"""A translator that uses Google's 'gemma-3-27b-it' model."""

import json
import logging
import re

from pydantic import ValidationError

from .base_genai import BaseGenAITranslator, TranslationList

logger = logging.getLogger(__name__)


GEMMA_PROMPT_TEMPLATE = """<start_of_turn>user
You are a professional translation engine. Your task is to translate a list of texts from {source_lang} to {target_lang}.

You MUST return a JSON object with a single key "translations" that contains a list of the translated strings.
The list of translated strings must have the same number of items as the input list.
If a translation is not possible, return the original text for that item. Do not add explanations.

Translate the following texts:
{texts_json_array}<end_of_turn>
<start_of_turn>model
"""


class GemmaTranslator(BaseGenAITranslator):
    """
    A translator for the Gemma family of models.

    This translator uses Google's 'gemma-3-27b-it' model by default and is designed
    to handle potentially unstructured text responses by extracting a JSON object
    for validation.
    """

    def _default_model_name(self) -> str:
        """Return the default model name to use if not specified in settings."""
        return "gemma-3-27b-it"

    def _get_prompt_template(self) -> str:
        """Return the Gemma-specific prompt template."""
        return GEMMA_PROMPT_TEMPLATE

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
