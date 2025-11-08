"""
Integration tests for MockTranslator.

MockTranslator does not require API keys and should always be runnable.
These tests verify basic translator functionality without external dependencies.
"""

import unittest

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.translators.mock_translator import MockTranslator, MockTranslatorError


class TestMockTranslatorIntegration(unittest.TestCase):
    """Integration test suite for MockTranslator."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.translator = MockTranslator(settings=ProviderSettings())

    def test_initialization_with_default_settings(self) -> None:
        """1. Initialization: Successfully creates translator with default settings."""
        translator = MockTranslator(settings=ProviderSettings())
        assert translator is not None
        assert translator.settings is not None
        assert translator.return_error is False

    def test_initialization_with_error_mode(self) -> None:
        """2. Initialization: Successfully creates translator with error mode enabled."""
        translator = MockTranslator(settings=ProviderSettings(), return_error=True)
        assert translator is not None
        assert translator.return_error is True

    def test_simple_translation(self) -> None:
        """3. Translation: Translates a single text correctly."""
        texts = ["Hello, World!"]
        target_language = "zh-TW"
        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 1
        assert results[0].translated_text == "[MOCK] Hello, World!"
        assert results[0].tokens_used == len("Hello, World!")

    def test_batch_translation(self) -> None:
        """4. Batch Translation: Translates multiple texts correctly."""
        texts = ["Hello", "World", "Test"]
        target_language = "fr"
        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 3
        assert results[0].translated_text == "[MOCK] Hello"
        assert results[1].translated_text == "[MOCK] World"
        assert results[2].translated_text == "[MOCK] Test"
        # Verify token counting
        assert results[0].tokens_used == len("Hello")
        assert results[1].tokens_used == len("World")
        assert results[2].tokens_used == len("Test")

    def test_empty_input_handling(self) -> None:
        """5. Empty Input: Returns empty list for empty input."""
        results = self.translator.translate([], target_language="en")
        assert results == []
        assert len(results) == 0

    def test_translation_with_debug_mode(self) -> None:
        """6. Debug Mode: Translation works correctly with debug flag enabled."""
        texts = ["Debug test"]
        target_language = "de"
        # Should not raise any exceptions
        results = self.translator.translate(texts, target_language=target_language, debug=True)

        assert len(results) == 1
        assert results[0].translated_text == "[MOCK] Debug test"

    def test_translation_with_source_language(self) -> None:
        """7. Source Language: Translation works with source language specified."""
        texts = ["Source language test"]
        results = self.translator.translate(
            texts,
            target_language="es",
            source_language="en",
        )

        assert len(results) == 1
        assert results[0].translated_text == "[MOCK] Source language test"

    def test_count_tokens_with_single_text(self) -> None:
        """8. Token Counting: Correctly counts tokens for a single text."""
        texts = ["This is a test sentence."]
        token_count = self.translator.count_tokens(texts)

        expected_count = len("This is a test sentence.")
        assert token_count == expected_count

    def test_count_tokens_with_multiple_texts(self) -> None:
        """9. Token Counting: Correctly counts tokens for multiple texts."""
        texts = ["First text.", "Second text.", "Third."]
        token_count = self.translator.count_tokens(texts)

        expected_count = sum(len(text) for text in texts)
        assert token_count == expected_count

    def test_count_tokens_with_empty_input(self) -> None:
        """10. Token Counting: Returns zero for empty input."""
        token_count = self.translator.count_tokens([])
        assert token_count == 0

    def test_error_mode_raises_exception(self) -> None:
        """11. Error Handling: Raises exception when configured to fail."""
        translator = MockTranslator(settings=ProviderSettings(), return_error=True)

        with pytest.raises(MockTranslatorError, match="Mock translator was configured to fail"):
            translator.translate(["Test"], target_language="en")

    def test_translation_preserves_special_characters(self) -> None:
        """12. Special Characters: Correctly handles texts with special characters."""
        texts = [
            "Hello! @#$%",
            "Unicode: 你好世界",
            "Emoji: 😀🎉",
        ]
        target_language = "en"
        results = self.translator.translate(texts, target_language=target_language)

        assert len(results) == 3
        assert results[0].translated_text == "[MOCK] Hello! @#$%"
        assert results[1].translated_text == "[MOCK] Unicode: 你好世界"
        assert results[2].translated_text == "[MOCK] Emoji: 😀🎉"
        # Verify token counts are based on actual character length
        assert results[0].tokens_used is not None
        assert results[0].tokens_used > 0
        assert results[1].tokens_used is not None
        assert results[1].tokens_used > 0
        assert results[2].tokens_used is not None
        assert results[2].tokens_used > 0


if __name__ == "__main__":
    unittest.main()
