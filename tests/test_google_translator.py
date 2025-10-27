"""Unit tests for the GoogleTranslator."""

import unittest
from unittest.mock import MagicMock, patch

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.translators.google_translator import GoogleTranslator


class TestGoogleTranslatorInit(unittest.TestCase):
    """Test suite for the GoogleTranslator initialization and translation."""

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_init_success(self, mock_deep_translator: MagicMock) -> None:
        """1. Success: Initializes the translator and returns a valid translation."""
        # Arrange
        settings = ProviderSettings()
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Bonjour", "Monde"]
        original_texts = ["Hello", "World"]

        # Act
        translator = GoogleTranslator(settings=settings)
        results = translator.translate(texts=original_texts, target_language="fr")

        # Assert
        assert isinstance(translator, GoogleTranslator)
        mock_deep_translator.assert_called_once_with(source="auto", target="fr")
        mock_instance.translate_batch.assert_called_once_with(original_texts)
        assert len(results) == len(original_texts)
        assert results[0].translated_text == "Bonjour"
        assert results[1].translated_text == "Monde"

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_translate_failure(self, mock_deep_translator: MagicMock) -> None:
        """2. Failure: Raises ConnectionError on API failure."""
        # Arrange
        settings = ProviderSettings()
        error_message = "API is down"
        mock_deep_translator.side_effect = Exception(error_message)

        translator = GoogleTranslator(settings=settings)

        # Act & Assert
        with pytest.raises(ConnectionError, match=error_message):
            translator.translate(texts=["Hello"], target_language="es")
