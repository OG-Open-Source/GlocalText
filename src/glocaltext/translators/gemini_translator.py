"""A translator that uses Google's 'gemini-flash-lite-latest' model."""

import logging
import re

from google.genai import types

from .base_genai import BaseGenAITranslator, TranslationList

logger = logging.getLogger(__name__)


class GeminiTranslator(BaseGenAITranslator):
    """
    A translator for the Gemini family of models.

    This translator uses Google's 'gemini-flash-lite-latest' model by default
    and expects a structured JSON response from the model.
    """

    def _default_model_name(self) -> str:
        """Return the default model name to use if not specified in settings."""
        return "gemini-flash-lite-latest"

    def _get_generation_config(self) -> types.GenerateContentConfig:
        """
        Return the generation configuration for the API call.

        For Gemini, we specify the response MIME type as JSON.
        """
        return types.GenerateContentConfig(response_mime_type="application/json")

    def _parse_response(self, response_text: str, original_texts: list[str]) -> list[str]:
        """
        Parse and validate the JSON response from the API.

        Args:
            response_text: The raw text from the API response.
            original_texts: The original list of texts for validation.

        Returns:
            A list of translated strings.

        Raises:
            ValueError: If the response is invalid, or the translation count mismatches.

        """
        # Clean the response text from markdown code blocks.
        match = re.search(r"```json\n(.*?)\n```", response_text, re.DOTALL)
        if match:
            response_text = match.group(1)

        data = TranslationList.model_validate_json(response_text)
        translated_texts = data.translations
        if len(translated_texts) != len(original_texts):
            msg = f"Mismatched translation count: expected {len(original_texts)}, but got {len(translated_texts)}"
            raise ValueError(msg)
        return translated_texts
