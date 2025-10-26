import unittest
from unittest.mock import MagicMock, patch

from glocaltext.config import ProviderSettings
from glocaltext.translators.google_translator import GoogleTranslator


class TestGoogleTranslatorInit(unittest.TestCase):
    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_init_success(self, mock_deep_translator: MagicMock):
        """1. Success: Initializes the translator."""
        # Arrange
        settings = ProviderSettings()
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Bonjour", "Monde"]

        # Act
        translator = GoogleTranslator(settings=settings)
        results = translator.translate(texts=["Hello", "World"], target_language="fr")

        # Assert
        self.assertIsInstance(translator, GoogleTranslator)
        mock_deep_translator.assert_called_once_with(source="auto", target="fr")
        mock_instance.translate_batch.assert_called_once_with(["Hello", "World"])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].translated_text, "Bonjour")

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_translate_failure(self, mock_deep_translator: MagicMock):
        """2. Failure: Raises ConnectionError on API failure."""
        # Arrange
        settings = ProviderSettings()
        error_message = "API is down"
        # When the mocked class is instantiated, it will raise an exception.
        mock_deep_translator.side_effect = Exception(error_message)

        translator = GoogleTranslator(settings=settings)

        # Act & Assert
        try:
            translator.translate(texts=["Hello"], target_language="es")
            self.fail("ConnectionError was not raised")
        except ConnectionError as e:
            self.assertIn(error_message, str(e))
