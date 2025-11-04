"""Tests for the translator classes."""

import unittest
from unittest.mock import MagicMock, patch

import pytest
from google.api_core import exceptions as api_core_exceptions
from google.genai import types as google_genai_types
from pydantic import ValidationError

from glocaltext.config import ProviderSettings
from glocaltext.translators.base_genai import BaseGenAITranslator
from glocaltext.translators.gemini_translator import GeminiTranslator
from glocaltext.translators.gemma_translator import GemmaTranslator
from glocaltext.translators.google_translator import GoogleTranslator
from glocaltext.translators.mock_translator import MockTranslator


class TestMockTranslator(unittest.TestCase):
    """Test suite for the MockTranslator."""

    def test_translate_returns_mocked_string(self) -> None:
        """1. Translation: Returns a mocked string with the original text and target language."""
        translator = MockTranslator(settings=ProviderSettings())
        texts = ["Hello", "World"]
        target_language = "fr"
        results = translator.translate(texts, target_language=target_language)
        assert len(results) == 2  # noqa: PLR2004
        assert results[0].translated_text == "[MOCK] Hello"
        assert results[1].translated_text == "[MOCK] World"
        assert results[0].tokens_used == 5  # noqa: PLR2004

    def test_count_tokens_returns_actual_length(self) -> None:
        """2. Token Counting: Returns the actual token count based on len()."""
        translator = MockTranslator(settings=ProviderSettings())
        texts = ["This is a test.", "This is another test."]
        token_count = translator.count_tokens(texts)
        assert token_count == len("".join(texts))

    def test_translate_with_debug_does_not_fail(self) -> None:
        """3. Debug Mode: Ensures that passing the debug flag does not cause an error."""
        translator = MockTranslator(settings=ProviderSettings())
        texts = ["Test"]
        target_language = "de"
        try:
            results = translator.translate(texts, target_language=target_language, debug=True)
            assert len(results) == 1
            assert results[0].translated_text == "[MOCK] Test"
        except (AssertionError, AttributeError) as e:
            self.fail(f"MockTranslator failed in debug mode: {e}")


class ConcreteTestTranslator(BaseGenAITranslator):
    """A concrete implementation of BaseGenAITranslator for testing purposes."""

    def _default_model_name(self) -> str:
        return "test-model"

    def _parse_response(self, response_text: str, original_texts: list[str]) -> list[str]:
        return [f"parsed:{response_text}" for _ in original_texts]


class TestBaseGenAITranslator(unittest.TestCase):
    """Test suite for the BaseGenAITranslator."""

    def test_init_raises_error_on_missing_api_key(self) -> None:
        """1. Init: Raises ValueError if API key is missing."""
        with pytest.raises(ValueError, match="API key for ConcreteTestTranslator is missing"):
            ConcreteTestTranslator(settings=ProviderSettings(api_key=None))

    @patch("google.genai.Client")
    def test_translate_handles_api_error(self, mock_genai_client: MagicMock) -> None:
        """2. Translate: Handles GoogleAPICallError and raises ConnectionError."""
        mock_client_instance = mock_genai_client.return_value
        mock_client_instance.models.generate_content.side_effect = api_core_exceptions.GoogleAPICallError("API is down")
        translator = ConcreteTestTranslator(settings=ProviderSettings(api_key="fake-key"))
        with pytest.raises(ConnectionError, match="A Google API error occurred: None API is down"):
            translator.translate(["text"], "en")

    @patch("google.genai.Client")
    def test_translate_handles_empty_response(self, mock_genai_client: MagicMock) -> None:
        """3. Translate: Handles empty response text and raises ValueError."""
        mock_response = MagicMock()
        mock_response.text = ""
        mock_client_instance = mock_genai_client.return_value
        mock_client_instance.models.generate_content.return_value = mock_response
        translator = ConcreteTestTranslator(settings=ProviderSettings(api_key="fake-key"))
        with pytest.raises(ValueError, match=r"Failed to process API response: response text is empty."):
            translator.translate(["text"], "en")

    @patch("google.genai.Client")
    def test_successful_translation_and_token_distribution(self, mock_genai_client: MagicMock) -> None:
        """4. Success: Correctly processes a successful translation and distributes tokens."""
        mock_response = MagicMock()
        mock_response.text = "Success"
        mock_response.usage_metadata = MagicMock(total_token_count=10)
        mock_client_instance = mock_genai_client.return_value
        mock_client_instance.models.generate_content.return_value = mock_response
        translator = ConcreteTestTranslator(settings=ProviderSettings(api_key="fake-key"))
        results = translator.translate(["text1", "text2", "text3"], "en")
        assert len(results) == 3  # noqa: PLR2004
        assert results[0].translated_text == "parsed:Success"
        assert results[0].tokens_used == 3  # noqa: PLR2004
        assert results[1].tokens_used == 3  # noqa: PLR2004
        assert results[2].tokens_used == 4  # noqa: PLR2004

    @patch("google.genai.Client")
    def test_count_tokens_success_and_failure(self, mock_genai_client: MagicMock) -> None:
        """5. Token Count: Correctly counts tokens on success and handles API errors."""
        mock_client_instance = mock_genai_client.return_value
        mock_client_instance.models.count_tokens.return_value = MagicMock(total_tokens=42)
        translator = ConcreteTestTranslator(settings=ProviderSettings(api_key="fake-key"))
        token_count = translator.count_tokens(["some text"])
        assert token_count == 42  # noqa: PLR2004
        mock_client_instance.models.count_tokens.side_effect = api_core_exceptions.GoogleAPICallError("Count failed")
        token_count_fail = translator.count_tokens(["some text"])
        assert token_count_fail == 0


class TestGoogleTranslator(unittest.TestCase):
    """Test suite for the GoogleTranslator."""

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_successful_translation(self, mock_deep_translator: MagicMock) -> None:
        """1. Success: Translates texts and returns correct results."""
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.return_value = ["Bonjour", "Monde"]
        translator = GoogleTranslator(settings=ProviderSettings())
        results = translator.translate(["Hello", "World"], "fr")
        assert len(results) == 2  # noqa: PLR2004
        assert results[0].translated_text == "Bonjour"
        assert results[1].translated_text == "Monde"
        token_count = results[0].tokens_used
        assert token_count is not None
        assert token_count > 0

    @patch("glocaltext.translators.google_translator.DeepGoogleTranslator")
    def test_api_exception_raises_connection_error(self, mock_deep_translator: MagicMock) -> None:
        """2. API Error: Raises ConnectionError on API failure."""
        mock_instance = mock_deep_translator.return_value
        mock_instance.translate_batch.side_effect = Exception("Service Unavailable")
        translator = GoogleTranslator(settings=ProviderSettings())
        with pytest.raises(ConnectionError, match=r"deep-translator \(Google\) request failed: Service Unavailable"):
            translator.translate(["text"], "fr")

    def test_batch_size_limit_raises_not_implemented_error(self) -> None:
        """3. Batch Limit: Raises NotImplementedError for oversized batches."""
        translator = GoogleTranslator(settings=ProviderSettings())
        too_many_texts = ["text"] * 11
        with pytest.raises(NotImplementedError):
            translator.translate(too_many_texts, "fr")

    def test_empty_input_returns_empty_list(self) -> None:
        """4. Empty Input: Returns an empty list without calling the API."""
        translator = GoogleTranslator(settings=ProviderSettings())
        results = translator.translate([], "fr")
        assert results == []

    def test_count_tokens_returns_zero(self) -> None:
        """5. Token Counting: Always returns 0 as it's not supported."""
        translator = GoogleTranslator(settings=ProviderSettings())
        tokens = translator.count_tokens(["some text"])
        assert tokens == 0


class TestGemmaTranslator(unittest.TestCase):
    """Test suite for the GemmaTranslator."""

    def setUp(self) -> None:
        """Set up the test case."""
        self.translator = GemmaTranslator(settings=ProviderSettings(api_key="fake-key"))
        self.original_texts = ["Hello", "World"]

    def test_parse_response_direct_json(self) -> None:
        """1. Parse: Handles direct, valid JSON responses."""
        response_text = '{"translations": ["Bonjour", "Monde"]}'
        result = self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001
        assert result == ["Bonjour", "Monde"]

    def test_parse_response_from_markdown(self) -> None:
        """2. Parse: Extracts and handles JSON from a markdown code block."""
        response_text = 'Some introductory text.\n```json\n{"translations": ["Hallo", "Welt"]}\n```'
        result = self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001
        assert result == ["Hallo", "Welt"]

    def test_parse_response_from_unstructured_text(self) -> None:
        """3. Parse: Extracts the first valid JSON object from unstructured text."""
        response_text = 'Here is the translation: {"translations": ["Ciao", "Mondo"]}. Ignore this part.'
        result = self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001
        assert result == ["Ciao", "Mondo"]

    def test_parse_response_mismatched_count_raises_error(self) -> None:
        """4. Error: Raises ValueError if translation count mismatches."""
        response_text = '{"translations": ["Bonjour"]}'
        with pytest.raises(ValueError, match="Mismatched translation count: expected 2, but got 1"):
            self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001

    def test_parse_response_no_json_raises_error(self) -> None:
        """5. Error: Raises ValueError if no JSON is found."""
        response_text = "There is no JSON here."
        with pytest.raises(ValueError, match="Could not find a valid JSON object in the response"):
            self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001

    def test_parse_response_invalid_json_raises_error(self) -> None:
        """6. Error: Raises ValueError on invalid JSON."""
        response_text = '{"translations": ["Bonjour", "Monde"]'
        with pytest.raises(ValueError, match="Failed to validate extracted JSON"):
            self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001


class TestGeminiTranslator(unittest.TestCase):
    """Test suite for the GeminiTranslator."""

    def setUp(self) -> None:
        """Set up the test case."""
        self.translator = GeminiTranslator(settings=ProviderSettings(api_key="fake-key"))
        self.original_texts = ["Hello", "World"]

    def test_get_generation_config(self) -> None:
        """1. Config: Returns the correct generation config for JSON output."""
        config = self.translator._get_generation_config()  # noqa: SLF001
        assert isinstance(config, google_genai_types.GenerateContentConfig)
        assert config.response_mime_type == "application/json"

    def test_parse_response_direct_json(self) -> None:
        """2. Parse: Handles a direct, valid JSON response."""
        response_text = '{"translations": ["Bonjour", "Monde"]}'
        result = self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001
        assert result == ["Bonjour", "Monde"]

    def test_parse_response_from_markdown(self) -> None:
        """3. Parse: Extracts and handles JSON from a markdown code block."""
        response_text = '```json\n{"translations": ["Hallo", "Welt"]}\n```'
        result = self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001
        assert result == ["Hallo", "Welt"]

    def test_parse_response_mismatched_count_raises_error(self) -> None:
        """4. Error: Raises ValueError if translation count mismatches."""
        response_text = '{"translations": ["Bonjour"]}'
        with pytest.raises(ValueError, match="Mismatched translation count: expected 2, but got 1"):
            self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001

    def test_parse_response_invalid_json_raises_error(self) -> None:
        """5. Error: Raises ValidationError on malformed JSON."""
        response_text = '{"translations": ["Bonjour", "Monde"]'
        with pytest.raises(ValidationError):
            self.translator._parse_response(response_text, self.original_texts)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
