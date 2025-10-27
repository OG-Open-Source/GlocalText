"""A translator that uses the official Google Generative AI (Gemini) SDK."""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult

from .base import BaseTranslator

logger = logging.getLogger(__name__)


# --- Pydantic Schema for Structured Output ---
class TranslationList(BaseModel):
    """Defines the expected JSON structure for the list of translations."""

    translations: list[str] = Field(description="A list of translated strings.")


# --- Constants ---
PROMPT_TEMPLATE = """
You are a professional translation engine. Your task is to translate a list of texts from {source_lang} to {target_lang}.

- If a translation is impossible, return the original text for that item.
- Pay close attention to any `manual_translations` provided, as they are verified human translations.

[MANUAL TRANSLATIONS START]
{manual_translations_json}
[MANUAL TRANSLATIONS END]

Translate the following texts:
{texts_json_array}
"""


class GeminiTranslator(BaseTranslator):
    """
    A translator that uses the official Google Generative AI (Gemini) SDK.

    This class handles the entire translation workflow, including building
    prompts, sending requests to the Gemini API, parsing the JSON response,

    and handling errors and token counting.
    """

    def _initialize_safety_settings(self) -> list[types.SafetySetting] | None:
        """
        Initialize safety settings from the 'safety_settings' key in the provider's 'extra' config.

        This method centralizes the logic for parsing and validating safety
        settings, which are expected to be a list of dictionaries, each with
        a 'category' and 'threshold'.

        Returns:
            A list of SafetySetting objects ready for the API, or None.

        Raises:
            ValueError: If the settings format is invalid.

        """
        if not self.settings or not self.settings.extra:
            return None

        raw_settings = self.settings.extra.get("safety_settings")
        if not raw_settings:
            return None

        if not isinstance(raw_settings, list):
            msg = "'safety_settings' in provider config must be a list of dictionaries."
            raise TypeError(msg)

        safety_settings: list[types.SafetySetting] = []
        for setting_dict in raw_settings:
            if not isinstance(setting_dict, dict) or "category" not in setting_dict or "threshold" not in setting_dict:
                msg = "Each safety setting must be a dict with 'category' and 'threshold' keys."
                raise ValueError(msg)

            try:
                # The genai library expects enums, not strings.
                category = types.HarmCategory[setting_dict["category"]]
                threshold = types.HarmBlockThreshold[setting_dict["threshold"]]
                safety_settings.append(types.SafetySetting(category=category, threshold=threshold))
            except KeyError as e:
                msg = f"Invalid value for safety setting 'category' or 'threshold': {e}"
                raise ValueError(msg) from e

        return safety_settings

    def __init__(self, settings: ProviderSettings) -> None:
        """
        Initialize the Gemini Translator.

        This constructor is responsible for validating the provided settings,
        extracting the API key, and configuring the Gemini client. It will
        raise a `ValueError` if essential settings (like the API key)
        are missing.

        Args:
            settings: A Pydantic model containing provider-specific configurations
                      such as the API key, model name, and retry policies.

        Raises:
            ValueError: If the API key is missing from the settings or safety settings are malformed.
            ConnectionError: If the Gemini client fails to initialize.

        """
        super().__init__(settings)
        if not self.settings:
            msg = "ProviderSettings are required for GeminiTranslator but were not provided."
            raise ValueError(msg)

        if not self.settings.api_key:
            msg = "API key for Gemini is missing in the provider settings."
            raise ValueError(msg)

        self._initialize_client()
        self.safety_settings = self._initialize_safety_settings()

    def _initialize_client(self) -> None:
        """Initialize the Gemini client and retry decorator."""
        if not self.settings:
            msg = "Cannot initialize client without settings."
            raise ValueError(msg)
        try:
            self.client = genai.Client(api_key=self.settings.api_key)
            self.model_name = self.settings.model or "gemini-1.0-pro"
            retry_decorator = self._create_retry_decorator(self.settings)
            self._decorated_translate = retry_decorator(self._translate_attempt)
        except Exception as e:
            msg = f"Failed to initialize Gemini client: {e}"
            raise ConnectionError(msg) from e

    def _create_retry_decorator(self, settings: ProviderSettings) -> Callable[..., Any]:
        """
        Create and configure a tenacity retry decorator based on provider settings.

        This helper function centralizes the retry logic, making the __init__
        method cleaner.

        Args:
            settings: Provider-specific configurations containing retry parameters.

        Returns:
            A configured tenacity retry decorator.

        """
        retry_attempts = settings.retry_attempts or 3
        retry_delay = settings.retry_delay or 1.0
        retry_backoff_factor = settings.retry_backoff_factor or 2.0

        return retry(
            stop=stop_after_attempt(retry_attempts),
            wait=wait_exponential(
                multiplier=retry_delay,
                exp_base=retry_backoff_factor,
            ),
            retry=retry_if_exception_type(google_exceptions.ResourceExhausted),
            before_sleep=lambda retry_state: logger.info(
                "Gemini API resource exhausted. Retrying in %.2f seconds...",
                retry_state.next_action.sleep,
            )
            if retry_state.next_action
            else logger.info("Retrying Gemini API call..."),
        )

    def translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None = None,
        *,
        debug: bool = False,
        prompts: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """
        Translate a list of texts using the Gemini generative model with tenacity for retries.

        This method builds a detailed prompt, sends it to the Gemini API,
        and processes the response. Retry logic is handled by the `tenacity` library.

        Args:
            texts: A list of texts to be translated.
            target_language: The target language for the translation.
            source_language: The source language of the texts.
            debug: If True, enables detailed logging of the API request and response.
            prompts: An optional dictionary of custom prompts ('system' and 'user').

        Returns:
            A list of TranslationResult objects. If retries fail, returns original texts.

        """
        if not texts:
            return []

        prompt, system_instruction = self._build_prompt(texts, target_language, source_language, prompts)

        try:
            return self._decorated_translate(
                prompt=prompt,
                system_instruction=system_instruction,
                texts_count=len(texts),
                debug=debug,
            )
        except RetryError:
            logger.exception("Gemini API request failed after multiple retries. Returning original texts.")
            if prompt:
                logger.debug("Failed prompt for Gemini after all retries: \n%s", prompt)
            return [TranslationResult(translated_text=text) for text in texts]
        except Exception:
            logger.exception("Gemini API request failed with a non-retriable error. Returning original texts.")
            if prompt:
                logger.debug("Failed prompt for Gemini: \n%s", prompt)
            return [TranslationResult(translated_text=text) for text in texts]

    def _translate_attempt(
        self,
        prompt: str,
        system_instruction: str | None,
        texts_count: int,
        *,
        debug: bool,
    ) -> list[TranslationResult]:
        """
        Execute a single translation attempt by calling the Gemini API.

        This method is decorated with `tenacity.retry` in the `__init__` method.

        Args:
            prompt: The full prompt to send to the API.
            system_instruction: The system-level instructions for the model.
            texts_count: The number of texts to be translated.
            debug: If True, enables detailed logging.

        Returns:
            A list of TranslationResult objects.

        Raises:
            google_exceptions.ResourceExhausted: If the API returns a resource exhausted error.

        """
        prompt_tokens = self._count_api_tokens(prompt)
        if debug:
            logger.info(
                "[DEBUG] Gemini Request:\n- Model: %s\n- Prompt Tokens: %d\n- Prompt Body (first 200 chars): %s...",
                self.model_name,
                prompt_tokens,
                prompt[:200],
            )

        start_time = time.time()

        config = types.GenerateContentConfig(response_mime_type="application/json", system_instruction=system_instruction, safety_settings=self.safety_settings)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config,
        )
        duration = time.time() - start_time

        response_text = response.text or ""
        response_tokens = self._count_api_tokens(response.candidates[0].content) if response.candidates and response.candidates[0].content else 0
        total_tokens = prompt_tokens + response_tokens

        if debug:
            logger.info(
                "[DEBUG] Gemini Response:\n- Duration: %.2fs\n- Completion Tokens: %d\n- Total Tokens: %d\n- Response Text (first 200 chars): %s...",
                duration,
                response_tokens,
                total_tokens,
                response_text[:200],
            )

        translated_texts = self._parse_and_validate_response(response_text, texts_count)
        return self._package_results(translated_texts, total_tokens)

    def _build_prompt(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None,
        prompts: dict[str, str] | None,
    ) -> tuple[str, str | None]:
        """
        Build the full prompt for the Gemini API and extract the system instruction.

        It uses a template that is populated with the source and target languages,
        manual translations (if any), and the texts to be translated, formatted as
        a JSON array.

        Args:
            texts: The list of texts to translate.
            target_language: The target language.
            source_language: The source language.
            prompts: Optional custom prompts to override the default.

        Returns:
            A tuple containing the user-facing prompt and the system instruction.

        """
        # [TODO]: Implement manual translations lookup
        manual_translations_json = "{}"
        texts_json_array = json.dumps(texts, ensure_ascii=False)

        user_prompt_template = prompts.get("user", PROMPT_TEMPLATE) if prompts else PROMPT_TEMPLATE

        prompt = user_prompt_template.format(
            source_lang=source_language or "the original language",
            target_lang=target_language,
            manual_translations_json=manual_translations_json,
            texts_json_array=texts_json_array,
            text=texts_json_array,
        )
        system_instruction = prompts.get("system") if prompts else None
        return prompt, system_instruction

    def count_tokens(self, texts: list[str], prompts: dict[str, str] | None = None) -> int:
        """
        Calculate the total number of tokens for a list of texts.

        This is done by building the full prompt and submitting it to the token counting API.
        """
        if not texts:
            return 0
        # We need to build the prompt to get an accurate token count, as it includes
        # templates, JSON formatting, and other overhead.
        # Target and source languages are placeholders as they have minimal impact on token count.
        prompt, _ = self._build_prompt(texts=texts, target_language="xx", source_language="xx", prompts=prompts)
        return self._count_api_tokens(prompt)

    def _count_api_tokens(self, content: str | types.Content) -> int:
        """Count the tokens for the given content by calling the API."""
        if not content:
            return 0

        content_for_api: str
        if isinstance(content, types.Content):
            parts_text = "".join(part.text for part in content.parts if part.text is not None) if content.parts else ""
            content_for_api = parts_text
        else:
            content_for_api = content
        try:
            response = self.client.models.count_tokens(model=self.model_name, contents=content_for_api)
        except google_exceptions.GoogleAPICallError as e:
            # Catching a broad exception as a fallback, as the exact errors from the API
            # might vary. Logging the specific error provides visibility.
            logger.warning("Token counting failed due to an API error: %s. Returning 0.", e, exc_info=True)
            return 0
        else:
            return response.total_tokens or 0

    def _package_results(self, translated_texts: list[str], total_tokens: int) -> list[TranslationResult]:
        """Package the translated texts into TranslationResult objects."""
        num_texts = len(translated_texts)
        if not num_texts:
            return []

        tokens_per_text = total_tokens // num_texts
        results = [TranslationResult(translated_text=text, tokens_used=tokens_per_text or 0) for text in translated_texts]

        remainder = total_tokens % num_texts
        if results and results[-1].tokens_used is not None:
            results[-1].tokens_used += remainder

        return results

    def _parse_and_validate_response(self, response_text: str, expected_count: int) -> list[str]:
        """Parse the guaranteed JSON response from Gemini and validate its structure."""
        try:
            # The response is guaranteed to be valid JSON conforming to the schema.
            data = TranslationList.model_validate_json(response_text)
            translations = data.translations
        except Exception:
            logger.exception("Failed to parse or validate Gemini's structured response")
            logger.debug("Invalid Gemini response text: %s", response_text)
            return [""] * expected_count
        else:
            if len(translations) != expected_count:
                logger.warning(
                    "Response list length (%d) does not match expected length (%d). Padding with original texts.",
                    len(translations),
                    expected_count,
                )
                # This is a fallback, but with structured output, it's less likely to happen.
                return (translations + [""] * expected_count)[:expected_count]
            return translations
