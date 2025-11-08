"""
Integration tests for GoogleTranslator.

GoogleTranslator uses the deep-translator library which may not require explicit
API keys but can be rate-limited. Integration tests are marked appropriately.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.translators.google_translator import GoogleTranslator


class TestGoogleTranslatorIntegration(unittest.TestCase):
    """Integration test suite for GoogleTranslator."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.translator = GoogleTranslator(settings=ProviderSettings())

    def test_initialization_with_default_settings(self) -> None:
        """1. Initialization: Successfully creates translator with default settings."""
        translator = GoogleTranslator(settings=ProviderSettings())
        assert translator is not None
        assert translator.settings is not None

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_simple_translation_mocked(self, mock_deep_translator: MagicMock) -> None:
        """2. Translation (Mock): Translates a single text correctly."""
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Bonjour"]

        texts = ["Hello"]
        target_language = "fr"
        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 1
        assert results[0].translated_text == "Bonjour"
        assert results[0].tokens_used is not None

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_batch_translation_mocked(self, mock_deep_translator: MagicMock) -> None:
        """3. Batch Translation (Mock): Translates multiple texts correctly."""
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Bonjour", "Monde", "Test"]

        texts = ["Hello", "World", "Test"]
        target_language = "fr"
        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 3
        assert results[0].translated_text == "Bonjour"
        assert results[1].translated_text == "Monde"
        assert results[2].translated_text == "Test"

    def test_empty_input_handling(self) -> None:
        """4. Empty Input: Returns empty list for empty input."""
        results = self.translator.translate([], target_language="en")
        assert results == []
        assert len(results) == 0

    def test_batch_size_limit_exceeded(self) -> None:
        """5. Batch Limit: Raises NotImplementedError for oversized batches."""
        # GoogleTranslator has a batch size limit of 10
        too_many_texts = ["text"] * 11

        with pytest.raises(NotImplementedError, match="does not support large batches"):
            self.translator.translate(too_many_texts, target_language="fr")

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_api_exception_handling(self, mock_deep_translator: MagicMock) -> None:
        """6. Error Handling: Raises ConnectionError on API failure."""
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.side_effect = Exception("Service Unavailable")

        with pytest.raises(ConnectionError, match="deep-translator \\(Google\\) request failed"):
            self.translator.translate(["text"], target_language="fr")

    def test_count_tokens_returns_zero(self) -> None:
        """7. Token Counting: Always returns 0 as it's not supported."""
        texts = ["some text", "another text"]
        token_count = self.translator.count_tokens(texts)
        assert token_count == 0

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_translation_with_source_language(self, mock_deep_translator: MagicMock) -> None:
        """8. Source Language: Translation works with source language specified."""
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Hola"]

        texts = ["Hello"]
        results = self.translator.translate(
            texts,
            target_language="es",
            source_language="en",
        )

        assert len(results) == 1
        assert results[0].translated_text == "Hola"

    @pytest.mark.integration
    def test_real_translation_english_to_french(self) -> None:
        """9. Integration: Real translation from English to French."""
        # Integration tests use the translator from setUp
        # Note: These tests will actually use deep-translator without API key
        texts = ["Hello, world!"]
        target_language = "fr"

        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 1
        assert results[0].translated_text is not None
        assert len(results[0].translated_text) > 0
        # French translation should be different from English
        assert results[0].translated_text != texts[0]

    @pytest.mark.integration
    def test_real_batch_translation(self) -> None:
        """10. Integration: Real batch translation."""
        texts = ["Hello", "Goodbye", "Thank you"]
        target_language = "es"

        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 3
        # All results should have translations
        for result in results:
            assert result.translated_text is not None
            assert len(result.translated_text) > 0

    @pytest.mark.integration
    def test_real_translation_with_special_characters(self) -> None:
        """11. Integration: Real translation handles special characters."""
        texts = ["Hello! How are you?"]
        target_language = "de"

        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 1
        assert results[0].translated_text is not None
        # Translation should preserve punctuation
        assert "?" in results[0].translated_text or "！" in results[0].translated_text


if __name__ == "__main__":
    unittest.main()
