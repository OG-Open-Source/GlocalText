"""
Integration tests for GemmaTranslator.

GemmaTranslator uses Google's Gemma model and requires the GEMINI_API_KEY
environment variable for integration tests (same as Gemini).
"""

import os
import unittest

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.translators.gemma_translator import GemmaTranslator


class TestGemmaTranslatorIntegration(unittest.TestCase):
    """Integration test suite for GemmaTranslator."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Note: Real API key is provided by fixture for integration tests
        self.api_key = "fake-test-key"
        self.translator = GemmaTranslator(settings=ProviderSettings(api_key=self.api_key))

    def test_initialization_with_api_key(self) -> None:
        """1. Initialization: Successfully creates translator with API key."""
        translator = GemmaTranslator(settings=ProviderSettings(api_key="test-key"))
        assert translator is not None
        assert translator.settings is not None
        assert translator.settings.api_key == "test-key"

    def test_initialization_without_api_key_raises_error(self) -> None:
        """2. Initialization: Raises ValueError if API key is missing."""
        with pytest.raises(ValueError, match="API key for GemmaTranslator is missing"):
            GemmaTranslator(settings=ProviderSettings(api_key=None))

    def test_default_model_name(self) -> None:
        """3. Configuration: Returns correct default model name."""
        model_name = self.translator._default_model_name()  # noqa: SLF001
        assert model_name == "gemma-3-27b-it"

    def test_prompt_template(self) -> None:
        """4. Configuration: Returns Gemma-specific prompt template."""
        prompt_template = self.translator._get_prompt_template()  # noqa: SLF001
        assert prompt_template is not None
        assert "<start_of_turn>" in prompt_template
        assert "<end_of_turn>" in prompt_template
        assert "{source_lang}" in prompt_template
        assert "{target_lang}" in prompt_template

    def test_parse_response_direct_json(self) -> None:
        """5. Parse: Handles direct, valid JSON responses."""
        response_text = '{"translations": ["Bonjour", "Monde"]}'
        original_texts = ["Hello", "World"]

        result = self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

        assert result == ["Bonjour", "Monde"]

    def test_parse_response_from_markdown(self) -> None:
        """6. Parse: Extracts JSON from markdown code block."""
        response_text = 'Here is the translation:\n```json\n{"translations": ["Hallo", "Welt"]}\n```\nDone.'
        original_texts = ["Hello", "World"]

        result = self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

        assert result == ["Hallo", "Welt"]

    def test_parse_response_from_unstructured_text(self) -> None:
        """7. Parse: Extracts JSON from unstructured text."""
        response_text = 'The translations are: {"translations": ["Ciao", "Mondo"]}. Hope this helps!'
        original_texts = ["Hello", "World"]

        result = self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

        assert result == ["Ciao", "Mondo"]

    def test_parse_response_mismatched_count_raises_error(self) -> None:
        """8. Parse Error: Raises ValueError if translation count mismatches."""
        response_text = '{"translations": ["Bonjour"]}'
        original_texts = ["Hello", "World"]

        with pytest.raises(ValueError, match="Mismatched translation count: expected 2, but got 1"):
            self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

    def test_parse_response_no_json_raises_error(self) -> None:
        """9. Parse Error: Raises ValueError if no JSON is found."""
        response_text = "This response contains no valid JSON object at all."
        original_texts = ["Hello"]

        with pytest.raises(ValueError, match="Could not find a valid JSON object"):
            self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

    @pytest.mark.integration
    def test_real_translation_english_to_spanish(self) -> None:
        """10. Integration: Real translation from English to Spanish."""
        # Create translator with API key for integration test
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not available for Gemma")

        translator = GemmaTranslator(settings=ProviderSettings(api_key=api_key))
        texts = ["Hello, how are you?"]
        target_language = "Spanish"

        results = translator.translate(texts, target_language=target_language)

        assert len(results) == 1
        assert results[0].translated_text is not None
        assert len(results[0].translated_text) > 0
        # Spanish translation should be different from English
        assert results[0].translated_text != texts[0]
        # Token usage should be recorded
        assert results[0].tokens_used is not None
        assert results[0].tokens_used > 0

    @pytest.mark.integration
    def test_real_batch_translation_with_context(self) -> None:
        """11. Integration: Real batch translation maintains context."""
        # Create translator with API key for integration test
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not available for Gemma")

        translator = GemmaTranslator(settings=ProviderSettings(api_key=api_key))
        texts = [
            "Good morning",
            "How can I help you?",
            "Thank you very much",
        ]
        target_language = "French"

        results = translator.translate(texts, target_language=target_language)

        assert len(results) == 3
        # All results should have translations
        for i, result in enumerate(results):
            assert result.translated_text is not None
            assert len(result.translated_text) > 0
            # Translations should be different from originals
            assert result.translated_text != texts[i]
            # Should have token counts
            assert result.tokens_used is not None


if __name__ == "__main__":
    unittest.main()
