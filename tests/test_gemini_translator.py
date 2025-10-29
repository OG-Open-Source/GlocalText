"""Integration tests for the GeminiTranslator."""

import json
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult
from glocaltext.translators.gemini_translator import GeminiTranslator


@dataclass
class TranslationTestCase:
    """A container for translation test cases."""

    original_texts: list[str]
    translated_texts: list[str]
    target_language: str
    expected_tokens: int


def test_init_raises_value_error_if_api_key_is_missing() -> None:
    """Raise ValueError if API key for Gemini is not provided."""
    # Arrange
    faulty_settings = ProviderSettings()  # No API key

    # Act & Assert
    with pytest.raises(ValueError, match="API key for Gemini is missing"):
        GeminiTranslator(settings=faulty_settings)


@pytest.mark.integration
class TestGeminiTranslator:
    """Test suite for the GeminiTranslator."""

    @pytest.fixture
    def mock_provider_settings(self) -> ProviderSettings:
        """Return a mock provider settings object."""
        return ProviderSettings(api_key="fake_api_key", model="gemini-1.5-flash")

    @pytest.fixture
    def mock_genai_client(self) -> Generator[MagicMock, None, None]:
        """Fixture to mock the google.genai.Client."""
        with patch("glocaltext.translators.gemini_translator.genai.Client") as mock_client_constructor:
            mock_client_instance = MagicMock()
            mock_client_constructor.return_value = mock_client_instance
            yield mock_client_instance

    @pytest.fixture
    def mock_translator(self, mock_provider_settings: ProviderSettings, mock_genai_client: MagicMock) -> tuple[GeminiTranslator, MagicMock]:
        """Return a mock GeminiTranslator instance and its mock client."""
        translator = GeminiTranslator(settings=mock_provider_settings)
        translator.client = mock_genai_client
        return translator, mock_genai_client

    @pytest.mark.parametrize(
        "test_case",
        [
            TranslationTestCase(
                original_texts=["Hello", "World"],
                translated_texts=["Bonjour", "Monde"],
                target_language="fr",
                expected_tokens=10,
            ),
            TranslationTestCase(
                original_texts=["One"],
                translated_texts=["Uno"],
                target_language="es",
                expected_tokens=5,
            ),
            TranslationTestCase(
                original_texts=["Apple", "Banana", "Cherry"],
                translated_texts=["Apfel", "Banane", "Kirsche"],
                target_language="de",
                expected_tokens=21,
            ),
        ],
    )
    def test_translate_success(
        self,
        mock_translator: tuple[GeminiTranslator, MagicMock],
        test_case: TranslationTestCase,
    ) -> None:
        """Test successful translation with various inputs."""
        # Arrange
        translator, mock_genai_client = mock_translator

        # Mock the API response
        mock_response = MagicMock()
        response_json = {"translations": test_case.translated_texts}
        type(mock_response).text = PropertyMock(return_value=json.dumps(response_json))

        # Mock the usage_metadata directly to avoid SDK class issues
        mock_usage_metadata = MagicMock()
        mock_usage_metadata.total_token_count = test_case.expected_tokens
        mock_response.usage_metadata = mock_usage_metadata

        mock_genai_client.models.generate_content.return_value = mock_response

        # Act
        results = translator.translate(texts=test_case.original_texts, target_language=test_case.target_language)

        # Assert
        assert len(results) == len(test_case.original_texts)
        for i, result in enumerate(results):
            assert isinstance(result, TranslationResult)
            assert result.translated_text == test_case.translated_texts[i]

        # Verify token calculation
        total_tokens_in_results = sum(r.tokens_used or 0 for r in results)
        assert total_tokens_in_results == test_case.expected_tokens
        mock_genai_client.models.generate_content.assert_called_once()

    def test_translate_raises_error_on_invalid_json(self, mock_translator: tuple[GeminiTranslator, MagicMock]) -> None:
        """Test that a JSONDecodeError is handled and raises a ValueError."""
        # Arrange
        translator, mock_genai_client = mock_translator
        mock_response = MagicMock()
        type(mock_response).text = PropertyMock(return_value="this is not valid json")
        mock_genai_client.models.generate_content.return_value = mock_response

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to process Gemini API response"):
            translator.translate(texts=["Hello"], target_language="fr")

    def test_translate_raises_error_on_mismatched_pydantic_schema(self, mock_translator: tuple[GeminiTranslator, MagicMock]) -> None:
        """Test that a Pydantic ValidationError is handled and raises a ValueError."""
        # Arrange
        translator, mock_genai_client = mock_translator
        mock_response = MagicMock()
        # The key "wrong_key" does not match the Pydantic model's "translations" field
        response_json = {"wrong_key": ["Bonjour"]}
        type(mock_response).text = PropertyMock(return_value=json.dumps(response_json))
        mock_genai_client.models.generate_content.return_value = mock_response

        # Act & Assert
        with pytest.raises(ValueError, match="Failed to process Gemini API response"):
            translator.translate(texts=["Hello"], target_language="fr")

    def test_translate_raises_error_on_mismatched_translation_count(self, mock_translator: tuple[GeminiTranslator, MagicMock]) -> None:
        """Test error when the number of translations does not match the input."""
        # Arrange
        translator, mock_genai_client = mock_translator
        mock_response = MagicMock()
        # Input has 2 texts, but the response only has 1
        response_json = {"translations": ["Bonjour"]}
        type(mock_response).text = PropertyMock(return_value=json.dumps(response_json))

        # Mock the usage_metadata directly
        mock_usage_metadata = MagicMock()
        mock_usage_metadata.total_token_count = 5
        mock_response.usage_metadata = mock_usage_metadata

        mock_genai_client.models.generate_content.return_value = mock_response

        # Act & Assert
        with pytest.raises(ValueError, match="Mismatched translation count"):
            translator.translate(texts=["Hello", "World"], target_language="fr")
