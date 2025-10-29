"""Unit tests for the MockTranslator."""

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult
from glocaltext.translators.mock_translator import (
    MockTranslator,
    MockTranslatorError,
)

# Constants for magic values
EXPECTED_RESULTS_COUNT = 2
MOCK_TOKENS_USED = 5
TOTAL_MOCK_TOKENS = 11


@pytest.fixture
def mock_settings() -> ProviderSettings:
    """Return a reusable ProviderSettings instance."""
    return ProviderSettings()


def test_init_success(mock_settings: ProviderSettings) -> None:
    """Test that the translator initializes correctly."""
    # Act
    translator = MockTranslator(settings=mock_settings)
    # Assert
    assert isinstance(translator, MockTranslator)
    assert not translator.return_error


def test_init_with_return_error(mock_settings: ProviderSettings) -> None:
    """Test that the translator initializes with the return_error flag."""
    # Act
    translator = MockTranslator(settings=mock_settings, return_error=True)
    # Assert
    assert translator.return_error


def test_translate_success(mock_settings: ProviderSettings) -> None:
    """Test the successful translation case."""
    # Arrange
    translator = MockTranslator(settings=mock_settings)
    texts = ["Hello", "World"]
    # Act
    results = translator.translate(texts, "en")
    # Assert
    assert len(results) == EXPECTED_RESULTS_COUNT
    assert all(isinstance(r, TranslationResult) for r in results)
    assert results[0].translated_text == "[MOCK] Hello"
    assert results[0].tokens_used == MOCK_TOKENS_USED
    assert results[1].translated_text == "[MOCK] World"
    assert results[1].tokens_used == MOCK_TOKENS_USED


def test_translate_with_empty_list(mock_settings: ProviderSettings) -> None:
    """Test that translating an empty list returns an empty list."""
    # Arrange
    translator = MockTranslator(settings=mock_settings)
    # Act
    results = translator.translate([], "en")
    # Assert
    assert results == []


def test_translate_raises_exception_when_configured(
    mock_settings: ProviderSettings,
) -> None:
    """Test that an exception is raised if return_error is True."""
    # Arrange
    translator = MockTranslator(settings=mock_settings, return_error=True)
    # Act & Assert
    with pytest.raises(MockTranslatorError, match=r"Mock translator was configured to fail."):
        translator.translate(["text"], "en")


def test_count_tokens_success(mock_settings: ProviderSettings) -> None:
    """Test that token counting returns the correct sum of lengths."""
    # Arrange
    translator = MockTranslator(settings=mock_settings)
    texts = ["one", "two", "three"]
    # Act
    token_count = translator.count_tokens(texts)
    # Assert
    assert token_count == TOTAL_MOCK_TOKENS  # 3 + 3 + 5


def test_count_tokens_with_empty_list(mock_settings: ProviderSettings) -> None:
    """Test that counting tokens for an empty list returns 0."""
    # Arrange
    translator = MockTranslator(settings=mock_settings)
    # Act
    token_count = translator.count_tokens([])
    # Assert
    assert token_count == 0
