import logging
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

from google.api_core import exceptions as google_exceptions

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.models import TranslationResult
from glocaltext.translate import _initialize_gemini
from glocaltext.translators.gemini_translator import GeminiTranslator


@patch("google.genai.Client")
class TestGeminiTranslator(unittest.TestCase):
    def setUp(self):
        """Set up the test environment before each test."""
        self.mock_provider_settings = ProviderSettings(retry_attempts=3, retry_delay=0.1, retry_backoff_factor=2.0)

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_success_on_first_attempt(self, mock_translate_attempt: MagicMock, mock_genai_client: MagicMock):
        """1. Success: API succeeds on the first call."""
        # Arrange
        translator = GeminiTranslator(
            api_key="fake_api_key",
            provider_settings=self.mock_provider_settings,
        )
        mock_translate_attempt.return_value = [
            TranslationResult(translated_text="Bonjour"),
            TranslationResult(translated_text="Monde"),
        ]

        # Act
        results = translator.translate(texts=["Hello", "World"], target_language="fr")

        # Assert
        mock_translate_attempt.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].translated_text, "Bonjour")
        self.assertEqual(results[1].translated_text, "Monde")

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_success_after_one_retry(self, mock_translate_attempt: MagicMock, mock_genai_client: MagicMock):
        """2. Retry Success: API fails once with a retriable error, then succeeds."""
        # Arrange
        translator = GeminiTranslator(
            api_key="fake_api_key",
            provider_settings=self.mock_provider_settings,
        )
        error = google_exceptions.ResourceExhausted("Rate limit exceeded")
        success_result = [
            TranslationResult(translated_text="Hallo"),
            TranslationResult(translated_text="Welt"),
        ]
        mock_translate_attempt.side_effect = [error, success_result]

        # Act
        results = translator.translate(texts=["Hello", "World"], target_language="de")

        # Assert
        self.assertEqual(mock_translate_attempt.call_count, 2)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].translated_text, "Hallo")
        self.assertEqual(results[1].translated_text, "Welt")

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_fails_after_max_retries(self, mock_translate_attempt: MagicMock, mock_genai_client: MagicMock):
        """3. Max Retries: Fails after all retry attempts and returns original texts."""
        # Arrange
        translator = GeminiTranslator(
            api_key="fake_api_key",
            provider_settings=self.mock_provider_settings,
        )
        error = google_exceptions.ResourceExhausted("Rate limit exceeded")
        mock_translate_attempt.side_effect = [
            error,
            error,
            error,
        ]  # Fails for all 3 attempts
        original_texts = ["Hello", "World"]

        # Act
        results = translator.translate(texts=original_texts, target_language="ja")

        # Assert
        self.assertEqual(
            mock_translate_attempt.call_count,
            self.mock_provider_settings.retry_attempts,
        )
        self.assertEqual(len(results), 2)
        # Should return original text on final failure
        self.assertEqual(results[0].translated_text, original_texts[0])
        self.assertEqual(results[1].translated_text, original_texts[1])

    @patch("glocaltext.translators.gemini_translator.GeminiTranslator._translate_attempt")
    def test_translate_fails_with_non_retriable_error(self, mock_translate_attempt: MagicMock, mock_genai_client: MagicMock):
        """4. Non-Retriable Error: No retry on a generic exception."""
        # Arrange
        translator = GeminiTranslator(
            api_key="fake_api_key",
            provider_settings=self.mock_provider_settings,
        )
        error = Exception("A generic, non-retriable error occurred.")
        mock_translate_attempt.side_effect = error
        original_texts = ["Hello", "World"]

        # Act
        results = translator.translate(texts=original_texts, target_language="it")

        # Assert
        mock_translate_attempt.assert_called_once()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].translated_text, original_texts[0])
        self.assertEqual(results[1].translated_text, original_texts[1])

    @patch("glocaltext.translate.logging")
    @patch("glocaltext.translate._validate_gemini_settings")
    def test_initialize_gemini_handles_incomplete_settings(
        self, mock_validate: MagicMock, mock_logging: MagicMock, mock_genai_client: MagicMock
    ):
        """5. Init Failure: _initialize_gemini returns None when settings are incomplete."""
        # Arrange
        mock_validate.side_effect = ValueError("Incomplete settings")
        mock_config_dict = {
            "providers": {"gemini": {"api_key": "some-key"}},
            "tasks": [],
        }
        mock_config = GlocalConfig.from_dict(mock_config_dict)
        translators: Dict[str, Any] = {}

        # Act
        result = _initialize_gemini(mock_config, translators)

        # Assert
        self.assertIsNone(result, "Translator should be None on validation failure.")
        mock_validate.assert_called_once_with(mock_config.providers.gemini)
        mock_logging.warning.assert_called_once()
        self.assertIn(
            "Gemini translator could not be initialized due to incomplete settings",
            mock_logging.warning.call_args[0][0],
            "A warning should be logged about incomplete settings.",
        )


if __name__ == "__main__":
    unittest.main()
