"""Unit tests for the main translation workflow."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glocaltext.config import (
    BatchOptions,
    GlocalConfig,
    Output,
    ProviderSettings,
    Source,
    TranslationTask,
)
from glocaltext.models import TextMatch, TranslationResult
from glocaltext.translate import (
    _create_batches,
    _create_simple_batches,
    _create_smart_batches,
    _log_oversized_batch_warning,
    _rpd_session_counts,
    _translator_cache,
    get_translator,
    process_matches,
)
from glocaltext.translators.base import BaseTranslator
from glocaltext.translators.gemini_translator import GeminiTranslator

# Constants for magic values to avoid PLR2004
RPM_LIMIT = 60
TPM_LIMIT = 100
RPD_LIMIT = 1
BATCH_SIZE = 10
SMALL_BATCH_SIZE = 2
EQUAL_BATCH_SIZE = 5
LARGE_BATCH_SIZE = 10
TOKENS_PER_TEXT_HEAVY = 90
TOKENS_PER_TEXT_LIGHT = 50
TOKENS_PER_TEXT_SIMPLE = 10
TOKENS_FOR_OVERSIZED = 150
DELAY_SECONDS = 1.0


class TestGetTranslator(unittest.TestCase):
    """Test suite for the get_translator function."""

    def setUp(self) -> None:
        """Clear the translator cache before each test."""
        _translator_cache.clear()

    def test_get_translator_success_and_cache(self) -> None:
        """1. Success: Initializes a translator and caches the instance."""
        # Arrange
        mock_config = GlocalConfig()
        # Mock a simple provider setting
        mock_config.providers["mock"] = ProviderSettings()

        # Act
        # First call should create and cache the translator
        translator1 = get_translator("mock", mock_config)

        # Second call should return the cached instance
        translator2 = get_translator("mock", mock_config)

        # Assert
        assert translator1 is not None
        assert isinstance(translator1, BaseTranslator)
        assert translator1 is translator2, "Translator instance should be cached and reused."
        assert "mock" in _translator_cache

    @unittest.skip("Skipping this test temporarily as it interferes with other tests.")
    def test_get_translator_init_failure_returns_none(self) -> None:
        """2. Init Failure: Returns None and logs a warning if the translator's __init__ fails."""
        # Arrange
        error_message = "API key is missing"

        mock_config = GlocalConfig()
        mock_config.providers["gemini"] = ProviderSettings(api_key="fake-key")

        # Act & Assert
        with (
            self.assertLogs("glocaltext.translate", level="WARNING") as cm,
            patch(
                "glocaltext.translate._get_translator",
                side_effect=ValueError(error_message),
            ),
        ):
            translator = get_translator("gemini", mock_config)

            assert translator is None, "Translator should be None on initialization failure."
            assert "gemini" not in _translator_cache, "Failed translator should not be cached."

            expected_log = f"Could not initialize translator 'gemini': {error_message}"
            assert any(expected_log in log for log in cm.output), f"Expected log message not found in {cm.output}"

    def test_get_translator_unknown_provider(self) -> None:
        """3. Unknown Provider: Raises ValueError for an unconfigured provider."""
        # Arrange
        mock_config = GlocalConfig()

        # Act & Assert
        with pytest.raises(ValueError, match=r"Provider 'unknown_provider' is not configured in your settings file."):
            get_translator("unknown_provider", mock_config)


@patch("glocaltext.translate.get_translator")
class TestProcessMatches(unittest.TestCase):
    """Test suite for the process_matches function."""

    def setUp(self) -> None:
        """Set up mock objects for testing process_matches."""
        # Reset the session counter before each test to ensure isolation
        _rpd_session_counts.clear()

        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            source=Source(include=["*.txt"]),
            extraction_rules=[],
            rules=[],
        )
        self.mock_task.output = Output(in_place=True)
        # Mock the translator that get_translator will return
        self.mock_translator = MagicMock(spec=GeminiTranslator)
        self.mock_translator.settings = ProviderSettings()
        # Mock the translate method to return a predictable result
        self.mock_translator.translate.return_value = [TranslationResult(translated_text="Bonjour", tokens_used=10)]
        # Ensure the config has the provider settings for the test
        self.mock_config.providers["gemini"] = self.mock_translator.settings

    def test_smart_scheduling_with_rpm_and_tpm(self, mock_get_translator: MagicMock) -> None:
        """1. Smart Scheduling: Creates batches and delays correctly with RPM/TPM."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings(rpm=RPM_LIMIT, tpm=TPM_LIMIT, batch_size=BATCH_SIZE)
        self.mock_translator.settings = provider_settings
        self.mock_config.providers["gemini"] = provider_settings
        self.mock_translator.translate.side_effect = [
            [TranslationResult(translated_text="Batch 1", tokens_used=TOKENS_PER_TEXT_HEAVY)],
            [TranslationResult(translated_text="Batch 2", tokens_used=TOKENS_PER_TEXT_LIGHT)],
        ]

        # Define token counts for each text
        def mock_count_tokens(texts: list[str], _prompts: dict | None = None) -> int:
            """Mock token counting for smart batching."""
            if len(texts) > 1:
                return TOKENS_PER_TEXT_HEAVY + TOKENS_PER_TEXT_LIGHT  # This will force a new batch
            return TOKENS_PER_TEXT_HEAVY if "heavy" in texts[0] else TOKENS_PER_TEXT_LIGHT

        self.mock_translator.count_tokens.side_effect = mock_count_tokens

        matches = [
            TextMatch(
                original_text="heavy text",
                source_file=Path("dummy.txt"),
                span=(0, 10),
                task_name="test",
                extraction_rule="test_rule",
            ),
            TextMatch(
                original_text="light text",
                source_file=Path("dummy.txt"),
                span=(11, 21),
                task_name="test",
                extraction_rule="test_rule",
            ),
        ]

        # Act
        with patch("time.sleep") as mock_sleep:
            process_matches(matches, self.mock_task, self.mock_config)

        # Assert
        assert self.mock_translator.translate.call_count == len(matches), "Should have been called twice, once for each batch"
        # First call for "heavy text"
        assert self.mock_translator.translate.call_args_list[0].kwargs["texts"] == ["heavy text"]
        # Second call for "light text"
        assert self.mock_translator.translate.call_args_list[1].kwargs["texts"] == ["light text"]

        mock_sleep.assert_called_once_with(DELAY_SECONDS)  # 60 RPM = 1s delay
        assert matches[0].translated_text == "Batch 1"
        assert matches[1].translated_text == "Batch 2"

    def test_rpd_limit_stops_execution(self, mock_get_translator: MagicMock) -> None:
        """2. RPD Limit: Stops processing when the daily request limit is reached."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings(rpm=RPM_LIMIT, tpm=TPM_LIMIT, rpd=RPD_LIMIT, batch_size=1)
        self.mock_translator.settings = provider_settings
        self.mock_config.providers["gemini"] = provider_settings
        self.mock_translator.translate.return_value = [TranslationResult(translated_text="Translated", tokens_used=TOKENS_PER_TEXT_LIGHT)]
        self.mock_translator.count_tokens.return_value = TOKENS_PER_TEXT_LIGHT

        matches = [
            TextMatch(
                original_text="text 1",
                source_file=Path("dummy.txt"),
                span=(0, 6),
                task_name="test",
                extraction_rule="test_rule",
            ),
            TextMatch(
                original_text="text 2",
                source_file=Path("dummy.txt"),
                span=(7, 13),
                task_name="test",
                extraction_rule="test_rule",
            ),
        ]

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            process_matches(matches, self.mock_task, self.mock_config)

            # Check for the specific warning log
            assert any(f"Request Per Day limit ({RPD_LIMIT}) for 'gemini' reached." in log for log in cm.output)

        self.mock_translator.translate.assert_called_once()
        assert matches[0].translated_text == "Translated"
        assert matches[1].translated_text is None  # The second match should not be translated
        assert matches[1].provider == "error_rpd_limit"

    def test_fallback_to_single_batch_without_limits(self, mock_get_translator: MagicMock) -> None:
        """3. No Limits: Falls back to a single batch when RPM/TPM are not set."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        # No RPM/TPM set in provider settings
        provider_settings = ProviderSettings()
        self.mock_translator.settings = provider_settings
        self.mock_config.providers["gemini"] = provider_settings
        self.mock_translator.translate.return_value = [
            TranslationResult(translated_text="Bonjour", tokens_used=10),
            TranslationResult(translated_text="Monde", tokens_used=10),
        ]
        matches = [
            TextMatch(
                original_text="Hello",
                source_file=Path("dummy.txt"),
                span=(0, 5),
                task_name="test",
                extraction_rule="test_rule",
            ),
            TextMatch(
                original_text="World",
                source_file=Path("dummy.txt"),
                span=(6, 11),
                task_name="test",
                extraction_rule="test_rule",
            ),
        ]

        # Act & Assert
        with (
            self.assertLogs("glocaltext.translate", level="INFO") as cm,
            patch("time.sleep") as mock_sleep,
        ):
            process_matches(matches, self.mock_task, self.mock_config)

            # Assert that it was logged that we are not using smart scheduling
            assert any("is not configured for intelligent scheduling" in log for log in cm.output)

            self.mock_translator.translate.assert_called_once()
            # The call should contain all texts in a single batch
            assert self.mock_translator.translate.call_args.kwargs["texts"] == [
                "Hello",
                "World",
            ]
            mock_sleep.assert_not_called()
            assert matches[0].translated_text == "Bonjour"
            assert matches[1].translated_text == "Monde"

    def test_provider_initialization_fallback(self, mock_get_translator: MagicMock) -> None:
        """4. Fallback: Uses fallback provider if primary fails to initialize."""
        # Arrange
        # Fail on first call (primary), succeed on second (fallback)
        mock_get_translator.side_effect = [None, self.mock_translator]

        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            process_matches(matches, self.mock_task, self.mock_config)

            # Check that a warning was logged about the primary failure
            assert any("Failed to initialize primary provider" in log for log in cm.output)

        # Assert that the fallback translator was used
        self.mock_translator.translate.assert_called_once_with(
            texts=["Hello"],
            target_language="fr",
            source_language="en",
            debug=False,
            prompts=None,
        )
        assert matches[0].translated_text == "Bonjour"
        # Ensure get_translator was called twice
        assert mock_get_translator.call_count == 2  # noqa: PLR2004

    def test_provider_initialization_critical_failure(self, mock_get_translator: MagicMock) -> None:
        """5. Critical Failure: Aborts if fallback provider also fails."""
        # Arrange
        # Fail on both calls
        mock_get_translator.side_effect = [None, None]

        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="ERROR") as cm:
            process_matches(matches, self.mock_task, self.mock_config)

            # Check that a critical error was logged
            assert any("CRITICAL: Fallback provider 'google' also failed" in log for log in cm.output)

        # Assert that translate was never called and the match is marked with an error
        self.mock_translator.translate.assert_not_called()
        assert matches[0].translated_text is None
        assert matches[0].provider == "error_initialization_error"
        assert mock_get_translator.call_count == 2  # noqa: PLR2004

    def test_translation_api_error_handling(self, mock_get_translator: MagicMock) -> None:
        """6. API Error: Handles exceptions during the API call gracefully."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        # The API call itself fails
        self.mock_translator.translate.side_effect = Exception("API is down")

        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="ERROR") as cm:
            process_matches(matches, self.mock_task, self.mock_config)

            assert any("Error translating batch" in log for log in cm.output)

        # Assert that the match is marked with an error
        self.mock_translator.translate.assert_called_once()
        assert matches[0].translated_text is None
        assert matches[0].provider == "error_gemini"


class TestBatchCreation(unittest.TestCase):
    """Test suite for batch creation functions."""

    def setUp(self) -> None:
        """Set up mock objects for testing batch creation."""
        self.mock_translator = MagicMock(spec=BaseTranslator)

    def test_create_simple_batches(self) -> None:
        """1. Simple Batches: Creates batches based on size only."""
        texts = ["a", "b", "c", "d", "e"]
        assert _create_simple_batches(texts, SMALL_BATCH_SIZE) == [["a", "b"], ["c", "d"], ["e"]]
        assert _create_simple_batches(texts, EQUAL_BATCH_SIZE) == [["a", "b", "c", "d", "e"]]
        assert _create_simple_batches(texts, LARGE_BATCH_SIZE) == [["a", "b", "c", "d", "e"]]
        assert _create_simple_batches(texts, 0) == [["a", "b", "c", "d", "e"]], "Batch size 0 should result in a single batch"
        assert _create_simple_batches([], SMALL_BATCH_SIZE) == []

    def test_create_smart_batches_tpm_limit(self) -> None:
        """2. Smart Batches: Creates batches respecting TPM limits."""
        texts = ["text1", "text2", "text3"]
        # Each text is 50 tokens, TPM is 100. So, batches should be [text1, text2], [text3]
        self.mock_translator.count_tokens.side_effect = lambda texts, _prompts: len(texts) * TOKENS_PER_TEXT_LIGHT

        batches = _create_smart_batches(self.mock_translator, texts, batch_size=EQUAL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)

        assert len(batches) == SMALL_BATCH_SIZE
        assert batches[0] == ["text1", "text2"]
        assert batches[1] == ["text3"]

    def test_create_smart_batches_batch_size_limit(self) -> None:
        """3. Smart Batches: Creates batches respecting batch_size limits."""
        texts = ["t1", "t2", "t3"]
        # Each text is 10 tokens, TPM is 100, batch_size is 2.
        self.mock_translator.count_tokens.side_effect = lambda texts, _prompts: len(texts) * TOKENS_PER_TEXT_SIMPLE

        batches = _create_smart_batches(self.mock_translator, texts, batch_size=SMALL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)

        assert len(batches) == SMALL_BATCH_SIZE
        assert batches[0] == ["t1", "t2"]
        assert batches[1] == ["t3"]

    @patch("glocaltext.translate.logger")
    def test_log_oversized_batch_warning(self, mock_logger: MagicMock) -> None:
        """4. Oversized Warning: Logs a warning for a single item exceeding TPM."""
        # A single text of 150 tokens, with a TPM of 100.
        self.mock_translator.count_tokens.return_value = TOKENS_FOR_OVERSIZED

        _log_oversized_batch_warning(self.mock_translator, ["oversized text"], tpm=TPM_LIMIT, prompts=None)

        mock_logger.warning.assert_called_once()
        assert "exceeds the TPM limit" in mock_logger.warning.call_args[0][0]

    def test_create_batches_delegation(self) -> None:
        """5. Batch Dispatch: Delegates to simple or smart batching correctly."""
        texts = ["a", "b", "c"]
        provider_settings = ProviderSettings(batch_options=BatchOptions(enabled=True), tpm=TPM_LIMIT)
        self.mock_translator.settings = provider_settings

        # With TPM, should use smart batching
        with patch("glocaltext.translate._create_smart_batches") as mock_smart:
            _create_batches(self.mock_translator, texts, batch_size=EQUAL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)
            mock_smart.assert_called_once()

        # Without TPM, should use simple batching
        with patch("glocaltext.translate._create_simple_batches") as mock_simple:
            _create_batches(self.mock_translator, texts, batch_size=EQUAL_BATCH_SIZE, tpm=None, prompts=None)
            mock_simple.assert_called_once()
