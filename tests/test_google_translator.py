"""Unit tests for the GoogleTranslator."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult
from glocaltext.translators.google_translator import GoogleTranslator


class TestGoogleTranslator(unittest.TestCase):
    """Test suite for the GoogleTranslator."""

    def setUp(self) -> None:
        """Set up the test environment before each test."""
        self.settings = ProviderSettings()
        self.original_texts = ["Hello", "World"]

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_translate_success(self, mock_deep_translator: MagicMock) -> None:
        """1. Success: Initializes the translator and returns a valid translation."""
        # Arrange
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Bonjour", "Monde"]

        translator = GoogleTranslator(settings=self.settings)

        # Act
        results = translator.translate(texts=self.original_texts, target_language="fr")

        # Assert
        mock_deep_translator.assert_called_once_with(source="auto", target="fr")
        mock_instance.translate_batch.assert_called_once_with(self.original_texts)

        assert isinstance(results, list)
        assert len(results) == len(self.original_texts)

        # Verify first result
        assert isinstance(results[0], TranslationResult)
        assert results[0].translated_text == "Bonjour"

        # Verify second result
        assert isinstance(results[1], TranslationResult)
        assert results[1].translated_text == "Monde"

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_translate_failure(self, mock_deep_translator: MagicMock) -> None:
        """2. Failure: Raises ConnectionError on API failure."""
        # Arrange
        error_message = "API is down"
        # Configure the class to raise an error on instantiation
        mock_deep_translator.side_effect = Exception(error_message)

        translator = GoogleTranslator(settings=self.settings)

        # Act & Assert
        with pytest.raises(ConnectionError, match=error_message):
            translator.translate(texts=["Hello"], target_language="es")

    def test_count_tokens_returns_zero(self) -> None:
        """3. Token Count: Always returns 0 as it's not supported."""
        # Arrange
        translator = GoogleTranslator(settings=self.settings)

        # Act
        token_count = translator.count_tokens(texts=self.original_texts)

        # Assert
        assert token_count == 0


if __name__ == "__main__":
    unittest.main()
