"""Unit tests for the GemmaTranslator."""

import json
from collections.abc import Generator
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from google.api_core import exceptions as api_core_exceptions

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult
from glocaltext.translators.gemma_translator import GemmaTranslator


def test_gemma_translator_initialization() -> None:
    """Verify that the GemmaTranslator initializes with the correct default model."""
    # Arrange
    settings = ProviderSettings(api_key="fake-api-key")

    # Act
    translator = GemmaTranslator(settings=settings)

    # Assert
    assert translator.model_name == "gemma-3-27b-it"


def test_init_raises_value_error_if_api_key_is_missing() -> None:
    """Raise ValueError if API key for Gemma is not provided."""
    # Arrange
    faulty_settings = ProviderSettings()  # No API key

    # Act & Assert
    with pytest.raises(ValueError, match=r"API key for Gemma is missing in the provider settings."):
        GemmaTranslator(settings=faulty_settings)


@pytest.fixture
def mock_genai_client() -> Generator[MagicMock, None, None]:
    """Fixture to mock the google.genai.Client."""
    with patch("glocaltext.translators.gemma_translator.genai.Client") as mock_client_constructor:
        mock_client_instance = MagicMock()
        mock_client_constructor.return_value = mock_client_instance
        yield mock_client_instance


@pytest.fixture
def mock_translator(mock_genai_client: MagicMock) -> tuple[GemmaTranslator, MagicMock]:
    """Return a mock GemmaTranslator instance and its mock client."""
    settings = ProviderSettings(api_key="fake-api-key")
    translator = GemmaTranslator(settings=settings)
    translator.client = mock_genai_client
    return translator, mock_genai_client


def test_translate_success(mock_translator: tuple[GemmaTranslator, MagicMock]) -> None:
    """Test successful translation with a non-structured response."""
    # Arrange
    translator, mock_genai_client = mock_translator
    original_texts = ["Hello", "World"]
    target_language = "fr"
    expected_translations = ["Bonjour", "Monde"]
    response_json = {"translations": expected_translations}
    expected_total_tokens = 10
    # Mock the API response
    mock_response = MagicMock()
    type(mock_response).text = PropertyMock(return_value=json.dumps(response_json))
    mock_usage_metadata = MagicMock()
    mock_usage_metadata.total_token_count = expected_total_tokens
    mock_response.usage_metadata = mock_usage_metadata
    mock_genai_client.models.generate_content.return_value = mock_response

    # Act
    results = translator.translate(texts=original_texts, target_language=target_language)

    # Assert
    assert len(results) == len(expected_translations)
    for i, result in enumerate(results):
        assert isinstance(result, TranslationResult)
        assert result.translated_text == expected_translations[i]

    total_tokens_in_results = sum(r.tokens_used or 0 for r in results)
    assert total_tokens_in_results == expected_total_tokens


def test_translate_failure_on_api_error(
    mock_translator: tuple[GemmaTranslator, MagicMock],
) -> None:
    """Test that a ConnectionError is raised when the API call fails."""
    # Arrange
    translator, mock_genai_client = mock_translator
    mock_genai_client.models.generate_content.side_effect = api_core_exceptions.GoogleAPICallError("API error")

    # Act & Assert
    with pytest.raises(ConnectionError, match="A Google API error occurred"):
        translator.translate(texts=["Hello"], target_language="fr")
