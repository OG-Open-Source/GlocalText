"""A translator that uses Google's 'gemma-3-27b-it' model."""

import json
import logging
import re

from google import genai
from google.api_core import exceptions as api_core_exceptions
from pydantic import BaseModel, Field, ValidationError

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

You MUST return a JSON object with a single key "translations" that contains a list of the translated strings.
The list of translated strings must have the same number of items as the input list.
Do not add any explanatory text, markdown, or any other text outside of the JSON object.

Translate the following texts:
{texts_json_array}
"""


class GemmaTranslator(BaseTranslator):
    """
    A translator for the Gemma family of models.

    This translator uses Google's 'gemma-3-27b-it' model by default and is designed
    to handle potentially unstructured text responses by extracting a JSON object
    for validation.
    """

    def __init__(self, settings: ProviderSettings) -> None:
        """
        Initialize the Gemma Translator.

        Args:
            settings: A Pydantic model containing provider-specific configurations
                      such as the API key and model name.

        Raises:
            ValueError: If the API key is missing from the settings.
            ConnectionError: If the Gemma client fails to initialize.

        """
        super().__init__(settings)
        if not self.settings:
            msg = "ProviderSettings are required for GemmaTranslator but were not provided."
            raise ValueError(msg)

        if not self.settings.api_key:
            msg = "API key for Gemma is missing in the provider settings."
            raise ValueError(msg)

        try:
            self.client = genai.Client(api_key=self.settings.api_key)
            self.model_name = self.settings.model or "gemma-3-27b-it"
        except (ValueError, api_core_exceptions.GoogleAPICallError) as e:
            msg = f"Failed to initialize Gemma client: {e}"
            raise ConnectionError(msg) from e

    def _parse_response(self, response_text: str, original_texts: list[str]) -> list[str]:
        """
        Parse and validate the JSON response from the API, handling unstructured text.

        Args:
            response_text: The raw text from the API response.
            original_texts: The original list of texts for validation.

        Returns:
            A list of translated strings.

        Raises:
            ValueError: If a valid JSON object cannot be parsed or the translation count mismatches.

        """
        json_str = ""
        # Attempt 1: Try to parse the whole string directly
        try:
            data = TranslationList.model_validate_json(response_text)
        except (ValidationError, json.JSONDecodeError):
            logger.debug("Direct JSON parsing failed. Attempting to extract from text.")
        else:
            if len(data.translations) != len(original_texts):
                msg = f"Mismatched translation count: expected {len(original_texts)}, but got {len(data.translations)}"
                raise ValueError(msg)
            return data.translations

        # Attempt 2: Find JSON within markdown code blocks (e.g., ```json ... ```)
        # The non-greedy search is safe from ReDoS because the delimiters are distinct
        # and the ambiguous `\s*` has been removed. Whitespace is handled by `strip()`.
        match = re.search(r"```json(.*?)```", response_text, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
        else:
            # Attempt 3: Find the first and most inclusive JSON object or array
            match = re.search(r"\{[^\}]*\}|\[[^\]]*\]", response_text, re.DOTALL)
            if match:
                json_str = match.group(0)

        if not json_str:
            msg = f"Could not find a valid JSON object in the response: {response_text}"
            raise ValueError(msg)

        try:
            data = TranslationList.model_validate_json(json_str)
            translated_texts = data.translations
            if len(translated_texts) != len(original_texts):
                msg = f"Mismatched translation count: expected {len(original_texts)}, but got {len(translated_texts)}"
                raise ValueError(msg)
        except (ValidationError, json.JSONDecodeError) as e:
            msg = f"Failed to validate extracted JSON. Details: {e}. Extracted JSON: '{json_str}'"
            raise ValueError(msg) from e
        else:
            return translated_texts

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
        Translate a list of texts using the Gemma model.

        Returns:
            A list of TranslationResult objects.

        Raises:
            ValueError: If the API response is invalid or cannot be processed.
            ConnectionError: If there's an issue communicating with the API.

        """
        if not texts:
            return []

        template = (prompts or {}).get("user", PROMPT_TEMPLATE)

        prompt = template.format(
            source_lang=source_language or "the original language",
            target_lang=target_language,
            texts_json_array=json.dumps(texts, ensure_ascii=False),
        )

        if debug:
            logger.debug(
                "Gemma Request:\n- Model: %s\n- Prompt Body (first 300 chars): %s...",
                self.model_name,
                prompt[:300],
            )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        except api_core_exceptions.GoogleAPICallError as e:
            logger.exception("A Google API error occurred during Gemma translation.")
            msg = f"A Google API error occurred: {e}"
            raise ConnectionError(msg) from e

        response_text = response.text
        if not response_text:
            msg = "Failed to process Gemma API response: response text is empty."
            raise ValueError(msg)

        try:
            translated_texts = self._parse_response(response_text, texts)

            total_tokens = 0
            if response.usage_metadata:
                total_tokens = response.usage_metadata.total_token_count or 0

            tokens_per_text = total_tokens // len(texts) if texts else 0
            results = [TranslationResult(translated_text=text, tokens_used=tokens_per_text) for text in translated_texts]

            if texts and results and total_tokens > 0:
                remainder = total_tokens % len(texts)
                if results[-1].tokens_used is not None:
                    results[-1].tokens_used += remainder
        except ValueError as e:
            raw_response_text = getattr(response, "text", "[NO TEXT IN RESPONSE]")
            logger.exception(
                "Failed to parse, validate, or read Gemma response: %s",
                raw_response_text,
            )
            msg = f"Failed to process Gemma API response. Details: {e}"
            raise ValueError(msg) from e
        else:
            return results

    def count_tokens(self, texts: list[str], prompts: dict[str, str] | None = None) -> int:
        """Calculate the token count by calling the API."""
        if not texts:
            return 0

        template = (prompts or {}).get("user", PROMPT_TEMPLATE)
        prompt = template.format(
            source_lang="en",  # lang doesn't matter for token count
            target_lang="fr",
            texts_json_array=json.dumps(texts, ensure_ascii=False),
        )
        try:
            response = self.client.models.count_tokens(model=self.model_name, contents=prompt)
        except api_core_exceptions.GoogleAPICallError:
            logger.exception("Token counting via API failed for Gemma. Returning 0.")
            return 0
        else:
            return response.total_tokens or 0
