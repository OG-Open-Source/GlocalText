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


def test_init_raises_connection_error_on_client_failure() -> None:
    """Raise ConnectionError if the genai.Client fails to initialize."""
    # Arrange
    settings = ProviderSettings(api_key="fake-api-key")
    with (
        patch(
            "glocaltext.translators.gemma_translator.genai.Client",
            side_effect=api_core_exceptions.GoogleAPICallError("Auth error"),
        ),
        pytest.raises(ConnectionError, match="Failed to initialize Gemma client"),
    ):
        # Act & Assert
        GemmaTranslator(settings=settings)


def test_translate_with_empty_list(mock_translator: tuple[GemmaTranslator, MagicMock]) -> None:
    """Test that translating an empty list returns an empty list immediately."""
    # Arrange
    translator, mock_genai_client = mock_translator
    # Act
    results = translator.translate(texts=[], target_language="fr")
    # Assert
    assert results == []
    mock_genai_client.models.generate_content.assert_not_called()


def test_translate_handles_empty_api_response(mock_translator: tuple[GemmaTranslator, MagicMock]) -> None:
    """Test that a ValueError is raised if the API returns an empty text response."""
    # Arrange
    translator, mock_genai_client = mock_translator
    mock_response = MagicMock()
    type(mock_response).text = PropertyMock(return_value="")
    mock_genai_client.models.generate_content.return_value = mock_response

    # Act & Assert
    with pytest.raises(ValueError, match="response text is empty"):
        translator.translate(texts=["Hello"], target_language="fr")


def test_translate_handles_mismatched_translation_count(
    mock_translator: tuple[GemmaTranslator, MagicMock],
) -> None:
    """Test ValueError is raised if the number of translations does not match the input."""
    # Arrange
    translator, mock_genai_client = mock_translator
    response_json = {"translations": ["Bonjour"]}  # Only one translation for two inputs
    mock_response = MagicMock()
    type(mock_response).text = PropertyMock(return_value=json.dumps(response_json))
    mock_response.usage_metadata.total_token_count = 5
    mock_genai_client.models.generate_content.return_value = mock_response

    # Act & Assert
    with pytest.raises(ValueError, match="Mismatched translation count"):
        translator.translate(texts=["Hello", "World"], target_language="fr")


def test_parse_response_from_markdown(mock_translator: tuple[GemmaTranslator, MagicMock]) -> None:
    """Test that the parser can extract a valid JSON object from a markdown block."""
    # Arrange
    translator, _ = mock_translator
    response_text = 'Some introductory text.\n```json\n{"translations": ["Bonjour", "Monde"]}\n```'
    original_texts = ["Hello", "World"]

    # Act
    translations = translator._parse_response(response_text, original_texts)  # noqa: SLF001

    # Assert
    assert translations == ["Bonjour", "Monde"]


def test_parse_response_raises_error_if_no_json_found(
    mock_translator: tuple[GemmaTranslator, MagicMock],
) -> None:
    """Test that a ValueError is raised if no JSON can be found in the response."""
    # Arrange
    translator, _ = mock_translator
    response_text = "This is a response with no JSON object."
    original_texts = ["Hello"]

    # Act & Assert
    with pytest.raises(ValueError, match="Could not find a valid JSON object"):
        translator._parse_response(response_text, original_texts)  # noqa: SLF001


def test_count_tokens_with_empty_list(mock_translator: tuple[GemmaTranslator, MagicMock]) -> None:
    """Test that counting tokens for an empty list returns 0."""
    # Arrange
    translator, mock_genai_client = mock_translator
    # Act
    token_count = translator.count_tokens([])
    # Assert
    assert token_count == 0
    mock_genai_client.models.count_tokens.assert_not_called()


def test_count_tokens_handles_api_error(mock_translator: tuple[GemmaTranslator, MagicMock]) -> None:
    """Test that token counting returns 0 if the API call fails."""
    # Arrange
    translator, mock_genai_client = mock_translator
    mock_genai_client.models.count_tokens.side_effect = api_core_exceptions.GoogleAPICallError("API error")
    # Act
    token_count = translator.count_tokens(["text"])
    # Assert
    assert token_count == 0
