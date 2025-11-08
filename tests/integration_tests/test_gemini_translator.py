"""
Integration tests for GeminiTranslator.

GeminiTranslator uses Google's Gemini API and requires the GEMINI_API_KEY
environment variable for integration tests.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as api_core_exceptions

from glocaltext.config import ProviderSettings
from glocaltext.translators.gemini_translator import GeminiTranslator


class TestGeminiTranslatorIntegration(unittest.TestCase):
    """Integration test suite for GeminiTranslator."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Note: Real API key is provided by fixture for integration tests
        self.api_key = "fake-test-key"
        self.translator = GeminiTranslator(settings=ProviderSettings(api_key=self.api_key))

    def test_initialization_with_api_key(self) -> None:
        """1. Initialization: Successfully creates translator with API key."""
        translator = GeminiTranslator(settings=ProviderSettings(api_key="test-key"))
        assert translator is not None
        assert translator.settings is not None
        assert translator.settings.api_key == "test-key"

    def test_initialization_without_api_key_raises_error(self) -> None:
        """2. Initialization: Raises ValueError if API key is missing."""
        with pytest.raises(ValueError, match="API key for GeminiTranslator is missing"):
            GeminiTranslator(settings=ProviderSettings(api_key=None))

    def test_default_model_name(self) -> None:
        """3. Configuration: Returns correct default model name."""
        model_name = self.translator._default_model_name()  # noqa: SLF001
        assert model_name == "gemini-flash-lite-latest"

    def test_generation_config(self) -> None:
        """4. Configuration: Returns correct generation config."""
        config = self.translator._get_generation_config()  # noqa: SLF001
        assert config is not None
        assert config.response_mime_type == "application/json"

    def test_parse_response_direct_json(self) -> None:
        """5. Parse: Handles direct, valid JSON responses."""
        response_text = '{"translations": ["Bonjour", "Monde"]}'
        original_texts = ["Hello", "World"]

        result = self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

        assert result == ["Bonjour", "Monde"]

    def test_parse_response_from_markdown(self) -> None:
        """6. Parse: Extracts and handles JSON from markdown code block."""
        response_text = '```json\n{"translations": ["Hallo", "Welt"]}\n```'
        original_texts = ["Hello", "World"]

        result = self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

        assert result == ["Hallo", "Welt"]

    def test_parse_response_mismatched_count_raises_error(self) -> None:
        """7. Parse Error: Raises ValueError if translation count mismatches."""
        response_text = '{"translations": ["Bonjour"]}'
        original_texts = ["Hello", "World"]

        with pytest.raises(ValueError, match="Mismatched translation count: expected 2, but got 1"):
            self.translator._parse_response(response_text, original_texts)  # noqa: SLF001

    def test_translation_with_api_error(self) -> None:
        """8. Error Handling: Handles GoogleAPICallError correctly."""
        # Patch the client's generate_content method directly
        with patch.object(self.translator.client.models, "generate_content", side_effect=api_core_exceptions.GoogleAPICallError("API error")), pytest.raises(ConnectionError, match="A Google API error occurred"):
            self.translator.translate(["test"], "en")

    def test_translation_with_empty_response(self) -> None:
        """9. Error Handling: Handles empty response text correctly."""
        # Patch the client's generate_content method to return empty response
        mock_response = MagicMock()
        mock_response.text = ""

        with patch.object(self.translator.client.models, "generate_content", return_value=mock_response), pytest.raises(ValueError, match="response text is empty"):
            self.translator.translate(["test"], "en")

    @pytest.mark.integration
    def test_real_translation_english_to_chinese(self) -> None:
        """10. Integration: Real translation from English to Chinese."""
        # Create translator with API key for integration test
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not available")

        translator = GeminiTranslator(settings=ProviderSettings(api_key=api_key))
        texts = ["Hello, world!"]
        target_language = "zh-TW"

        results = translator.translate(texts, target_language=target_language)

        assert len(results) == 1
        assert results[0].translated_text is not None
        assert len(results[0].translated_text) > 0
        # Should contain Chinese characters
        assert any("\u4e00" <= char <= "\u9fff" for char in results[0].translated_text)
        # Token usage should be recorded
        assert results[0].tokens_used is not None
        assert results[0].tokens_used > 0

    @pytest.mark.integration
    def test_real_batch_translation(self) -> None:
        """11. Integration: Real batch translation with multiple texts."""
        # Create translator with API key for integration test
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            pytest.skip("GEMINI_API_KEY not available")

        translator = GeminiTranslator(settings=ProviderSettings(api_key=api_key))
        texts = [
            "Good morning",
            "Thank you",
            "How are you?",
        ]
        target_language = "ja"

        results = translator.translate(texts, target_language=target_language)

        assert len(results) == 3
        # All results should have translations
        for result in results:
            assert result.translated_text is not None
            assert len(result.translated_text) > 0
            # Should contain Japanese characters
            assert any("\u3040" <= char <= "\u309f" or "\u30a0" <= char <= "\u30ff" for char in result.translated_text)


if __name__ == "__main__":
    unittest.main()
