import unittest

from glocaltext.config import ProviderSettings
from glocaltext.translators.mock_translator import MockTranslator


class TestMockTranslator(unittest.TestCase):
    def test_init_success(self):
        """1. Success: Initializes the translator with mock settings."""
        # Arrange
        settings = ProviderSettings()

        # Act
        translator = MockTranslator(settings=settings)

        # Assert
        self.assertIsInstance(translator, MockTranslator)
        self.assertEqual(translator.settings, settings)
