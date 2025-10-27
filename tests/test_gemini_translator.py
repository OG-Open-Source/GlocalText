"""Unit tests for the GeminiTranslator."""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as google_exceptions

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult
from glocaltext.translators.gemini_translator import GeminiTranslator


class TestGeminiTranslatorInit(unittest.TestCase):
    """Test suite for GeminiTranslator initialization."""

    def test_init_raises_value_error_if_api_key_is_missing(self) -> None:
        """Raise ValueError if API key is not provided."""
        # Arrange
        faulty_settings = ProviderSettings()  # No API key

        # Act & Assert
        with pytest.raises(ValueError, match="API key for Gemini is missing"):
            GeminiTranslator(settings=faulty_settings)


class TestGeminiTranslator(unittest.TestCase):
    """Test suite for the GeminiTranslator."""

    def setUp(self) -> None:
        """Set up the test environment before each test."""
        self.mock_provider_settings = ProviderSettings(
            api_key="fake_api_key",
            retry_attempts=3,
            retry_delay=0.1,
            retry_backoff_factor=2.0,
        )
        self.original_texts = ["Hello", "World"]

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_success_on_first_attempt(self, mock_translate_attempt: MagicMock) -> None:
        """1. Success: API succeeds on the first call."""
        # Arrange
        translator = GeminiTranslator(settings=self.mock_provider_settings)
        mock_translate_attempt.return_value = [
            TranslationResult(translated_text="Bonjour"),
            TranslationResult(translated_text="Monde"),
        ]

        # Act
        results = translator.translate(texts=self.original_texts, target_language="fr")

        # Assert
        mock_translate_attempt.assert_called_once()
        assert len(results) == len(self.original_texts)
        assert results[0].translated_text == "Bonjour"
        assert results[1].translated_text == "Monde"

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_success_after_one_retry(self, mock_translate_attempt: MagicMock) -> None:
        """Succeed on retry after a single retriable error."""
        # Arrange
        translator = GeminiTranslator(settings=self.mock_provider_settings)
        error = google_exceptions.ResourceExhausted("Rate limit exceeded")
        success_result = [
            TranslationResult(translated_text="Hallo"),
            TranslationResult(translated_text="Welt"),
        ]
        mock_translate_attempt.side_effect = [error, success_result]

        # Act
        results = translator.translate(texts=self.original_texts, target_language="de")

        # Assert
        assert mock_translate_attempt.call_count == len(mock_translate_attempt.side_effect)
        assert len(results) == len(self.original_texts)
        assert results[0].translated_text == "Hallo"
        assert results[1].translated_text == "Welt"

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_fails_after_max_retries(self, mock_translate_attempt: MagicMock) -> None:
        """3. Max Retries: Fails after all retry attempts and returns original texts."""
        # Arrange
        translator = GeminiTranslator(settings=self.mock_provider_settings)
        error = google_exceptions.ResourceExhausted("Rate limit exceeded")
        mock_translate_attempt.side_effect = [
            error,
            error,
            error,
        ]  # Fails for all 3 attempts

        # Act
        results = translator.translate(texts=self.original_texts, target_language="ja")

        # Assert
        assert mock_translate_attempt.call_count == self.mock_provider_settings.retry_attempts
        assert len(results) == len(self.original_texts)
        # Should return original text on final failure
        assert results[0].translated_text == self.original_texts[0]
        assert results[1].translated_text == self.original_texts[1]

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_fails_with_non_retriable_error(self, mock_translate_attempt: MagicMock) -> None:
        """4. Non-Retriable Error: No retry on a generic exception."""
        # Arrange
        translator = GeminiTranslator(settings=self.mock_provider_settings)
        error = Exception("A generic, non-retriable error occurred.")
        mock_translate_attempt.side_effect = error

        # Act
        results = translator.translate(texts=self.original_texts, target_language="it")

        # Assert
        mock_translate_attempt.assert_called_once()
        assert len(results) == len(self.original_texts)
        assert results[0].translated_text == self.original_texts[0]
        assert results[1].translated_text == self.original_texts[1]


if __name__ == "__main__":
    unittest.main()
