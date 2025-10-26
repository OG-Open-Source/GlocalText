# Implementation for the Gemini AI API using the latest google-genai SDK
import json
import logging
import time
from typing import Callable, Dict, List, Optional

from google import genai
from google.api_core import exceptions as google_exceptions
from google.genai import types
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import ProviderSettings
from ..models import TranslationResult
from .base import BaseTranslator

# --- Constants ---
PROMPT_TEMPLATE = """
You are a professional translation engine. Your task is to translate a list of texts from {source_lang} to {target_lang}.

You MUST adhere to the following rules:
1.  Respond with ONLY a single, valid JSON array of strings. Each string in the array is a translation of the corresponding text in the input.
2.  The JSON array MUST have the exact same number of elements as the input `texts_to_translate` array.
3.  If a translation is impossible, return the original text for that item.
4.  Pay close attention to the `manual_translations` provided. These are verified human translations and MUST be used as the single source of truth.

---
[MANUAL TRANSLATIONS START]
{manual_translations_json}
[MANUAL TRANSLATIONS END]
---

Translate the following JSON array of texts:

[TEXTS START]
{texts_json_array}
[TEXTS END]
"""


class GeminiTranslator(BaseTranslator):
    """
    A translator that uses the official Google Generative AI (Gemini) SDK.

    This class handles the entire translation workflow, including building
    prompts, sending requests to the Gemini API, parsing the JSON response,

    and handling errors and token counting.
    """

    def __init__(self, settings: ProviderSettings):
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
            ValueError: If the API key is missing from the settings.
            ConnectionError: If the Gemini client fails to initialize.
        """
        super().__init__(settings)
        if not self.settings:
            # This check satisfies the linter, as the base class defines settings as Optional.
            # Due to this constructor's signature, this path should not be reachable.
            raise ValueError("ProviderSettings are required for GeminiTranslator but were not provided.")

        if not self.settings.api_key:
            raise ValueError("API key for Gemini is missing in the provider settings.")

        try:
            # Configure the Gemini client with the API key from settings
            self.client = genai.Client(api_key=self.settings.api_key)
            self.model_name = self.settings.model or "gemini-1.0-pro"

            # Dynamically create a decorated method for translation attempts
            retry_decorator = self._create_retry_decorator(self.settings)
            self._decorated_translate = retry_decorator(self._translate_attempt)

        except Exception as e:
            raise ConnectionError(f"Failed to initialize Gemini client: {e}")

    def _create_retry_decorator(self, settings: ProviderSettings) -> Callable:
        """
        Creates and configures a tenacity retry decorator based on provider settings.

        This helper function centralizes the retry logic, making the __init__
        method cleaner and more focused on its primary responsibilities.

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
            before_sleep=lambda retry_state: logging.info(f"Gemini API resource exhausted. Retrying in {retry_state.next_action.sleep:.2f} seconds..." if retry_state.next_action else "Retrying Gemini API call..."),
        )

    def translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: str | None = None,
        debug: bool = False,
        prompts: Dict[str, str] | None = None,
    ) -> List[TranslationResult]:
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
        except RetryError as e:
            logging.error(f"Gemini API request failed after multiple retries: {e}. Returning original texts.")
            if prompt:
                logging.debug(f"Failed prompt for Gemini after all retries: \n{prompt}")
            return [TranslationResult(translated_text=text) for text in texts]
        except Exception as e:
            logging.error(f"Gemini API request failed with a non-retriable error: {e}. Returning original texts.")
            if prompt:
                logging.debug(f"Failed prompt for Gemini: \n{prompt}")
            return [TranslationResult(translated_text=text) for text in texts]

    def _translate_attempt(
        self,
        prompt: str,
        system_instruction: Optional[str],
        texts_count: int,
        debug: bool,
    ) -> List[TranslationResult]:
        """
        Executes a single translation attempt by calling the Gemini API.

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
            logging.info(f"[DEBUG] Gemini Request:\n- Model: {self.model_name}\n- Prompt Tokens: {prompt_tokens}\n- Prompt Body (first 200 chars): {prompt[:200]}...")

        start_time = time.time()
        config = types.GenerateContentConfig(response_mime_type="application/json", system_instruction=system_instruction)
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=[prompt],
            config=config,
        )
        duration = time.time() - start_time

        response_text = response.text or ""
        response_tokens = self._count_api_tokens(response.candidates[0].content) if response.candidates and response.candidates[0].content else 0
        total_tokens = prompt_tokens + response_tokens

        if debug:
            logging.info(f"[DEBUG] Gemini Response:\n- Duration: {duration:.2f}s\n- Completion Tokens: {response_tokens}\n- Total Tokens: {total_tokens}\n- Response Text (first 200 chars): {response_text[:200]}...")

        translated_texts = self._parse_and_validate_response(response_text, texts_count)
        return self._package_results(translated_texts, total_tokens)

    def _build_prompt(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str],
        prompts: Optional[Dict[str, str]],
    ) -> tuple[str, Optional[str]]:
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

    def count_tokens(self, texts: List[str], prompts: Optional[Dict[str, str]] = None) -> int:
        """
        Calculates the total number of tokens for a list of texts by building the
        full prompt and submitting it to the token counting API.
        """
        if not texts:
            return 0
        # We need to build the prompt to get an accurate token count, as it includes
        # templates, JSON formatting, and other overhead.
        # Target and source languages are placeholders as they have minimal impact on token count.
        prompt, _ = self._build_prompt(texts=texts, target_language="xx", source_language="xx", prompts=prompts)
        return self._count_api_tokens(prompt)

    def _count_api_tokens(self, content: str | types.ContentDict | types.Content) -> int:
        """Counts the tokens for the given content by calling the API."""
        if not content:
            return 0
        try:
            response = self.client.models.count_tokens(model=self.model_name, contents=[content])
            return response.total_tokens or 0
        except Exception as e:
            logging.warning(f"Token counting failed: {e}. Returning 0.")
            return 0

    def _package_results(self, translated_texts: List[str], total_tokens: int) -> List[TranslationResult]:
        """Packages the translated texts into TranslationResult objects."""
        num_texts = len(translated_texts)
        if not num_texts:
            return []

        tokens_per_text = total_tokens // num_texts
        results = [TranslationResult(translated_text=text, tokens_used=tokens_per_text or 0) for text in translated_texts]

        remainder = total_tokens % num_texts
        if results and results[-1].tokens_used is not None:
            results[-1].tokens_used += remainder

        return results

    def _parse_and_validate_response(self, response_text: str, expected_count: int) -> List[str]:
        """Parses the JSON response from Gemini and validates its structure."""
        try:
            cleaned_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()

            data = json.loads(cleaned_text)
            if not isinstance(data, list):
                raise ValueError("Response is not a JSON list.")

            if len(data) != expected_count:
                raise ValueError(f"Response list length ({len(data)}) does not match expected length ({expected_count}).")

            return [str(item) for item in data]

        except ValueError as e:
            if isinstance(e, json.JSONDecodeError):
                logging.warning("Failed to parse Gemini response as JSON. Assuming plain text response for the whole batch.")
                return [response_text.strip()] * expected_count

            logging.error(f"Failed to parse or validate Gemini response: {e}")
            logging.debug(f"Invalid Gemini response text: {response_text}")
            return [""] * expected_count
