"""Unit tests for the MockTranslator."""

import unittest

from glocaltext.config import ProviderSettings
from glocaltext.translators.mock_translator import MockTranslator


class TestMockTranslator(unittest.TestCase):
    """Test suite for the MockTranslator."""

    def test_init_success(self) -> None:
        """1. Success: Initializes the translator with mock settings."""
        # Arrange
        settings = ProviderSettings()

        # Act
        translator = MockTranslator(settings=settings)

        # Assert
        assert isinstance(translator, MockTranslator)
        assert translator.settings == settings
