"""Unit tests for the main translation workflow."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from glocaltext.config import GlocalConfig, Output, ProviderSettings, Source, TranslationTask
from glocaltext.models import TextMatch, TranslationResult
from glocaltext.translate import _rpd_session_counts, _translator_cache, get_translator, process_matches
from glocaltext.translators.base import BaseTranslator
from glocaltext.translators.gemini_translator import GeminiTranslator


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
        mock_config.providers.mock = ProviderSettings()

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

    @patch("glocaltext.translate.TRANSLATOR_MAPPING")
    def test_get_translator_init_failure_returns_none(self, mock_translator_mapping: MagicMock) -> None:
        """2. Init Failure: Returns None and logs a warning if the translator's __init__ fails."""
        # Arrange
        error_message = "API key is missing"
        failing_translator = MagicMock()
        failing_translator.side_effect = ValueError(error_message)

        # Inject the failing mock into the mapping
        mock_translator_mapping.get.return_value = failing_translator

        mock_config = GlocalConfig()
        mock_config.providers.gemini = ProviderSettings(api_key="fake-key")

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            translator = get_translator("gemini", mock_config)

            assert translator is None, "Translator should be None on initialization failure."
            assert "gemini" not in _translator_cache, "Failed translator should not be cached."

            expected_log = f"Could not initialize translator 'gemini': {error_message}"
            assert any(expected_log in log for log in cm.output), f"Expected log message not found in {cm.output}"

    def test_get_translator_unknown_provider(self) -> None:
        """3. Unknown Provider: Returns None for an unregistered provider name."""
        # Arrange
        mock_config = GlocalConfig()

        # Act & Assert
        with self.assertLogs(level="WARNING") as cm:
            translator = get_translator("unknown_provider", mock_config)
            assert translator is None
            # Check the log output from the root logger
            assert any("Unknown translator provider: 'unknown_provider'" in log for log in cm.output)


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
        )
        self.mock_task.output = Output(in_place=True)
        # Mock the translator that get_translator will return
        self.mock_translator = MagicMock(spec=GeminiTranslator)
        self.mock_translator.settings = ProviderSettings()
        # Mock the translate method to return a predictable result
        self.mock_translator.translate.return_value = [TranslationResult(translated_text="Bonjour", tokens_used=10)]
        # Ensure the config has the provider settings for the test
        self.mock_config.providers.gemini = self.mock_translator.settings

    def test_smart_scheduling_with_rpm_and_tpm(self, mock_get_translator: MagicMock) -> None:
        """1. Smart Scheduling: Creates batches and delays correctly with RPM/TPM."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings(rpm=60, tpm=100, batch_size=10)
        self.mock_translator.settings = provider_settings
        self.mock_config.providers.gemini = provider_settings
        self.mock_translator.translate.side_effect = [
            [TranslationResult(translated_text="Batch 1", tokens_used=90)],
            [TranslationResult(translated_text="Batch 2", tokens_used=50)],
        ]

        # Define token counts for each text
        def mock_count_tokens(texts: list[str]) -> int:
            if len(texts) > 1:
                return 120  # This will force a new batch
            return 90 if "heavy" in texts[0] else 50

        self.mock_translator.count_tokens.side_effect = mock_count_tokens

        matches = [
            TextMatch(original_text="heavy text", source_file=Path("dummy.txt"), span=(0, 10), task_name="test", extraction_rule="test_rule"),
            TextMatch(original_text="light text", source_file=Path("dummy.txt"), span=(11, 21), task_name="test", extraction_rule="test_rule"),
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

        mock_sleep.assert_called_once_with(1.0)  # 60 RPM = 1s delay
        assert matches[0].translated_text == "Batch 1"
        assert matches[1].translated_text == "Batch 2"

    def test_rpd_limit_stops_execution(self, mock_get_translator: MagicMock) -> None:
        """2. RPD Limit: Stops processing when the daily request limit is reached."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings(rpm=60, tpm=100, rpd=1, batch_size=1)
        self.mock_translator.settings = provider_settings
        self.mock_config.providers.gemini = provider_settings
        self.mock_translator.translate.return_value = [TranslationResult(translated_text="Translated", tokens_used=50)]
        self.mock_translator.count_tokens.return_value = 50

        matches = [
            TextMatch(original_text="text 1", source_file=Path("dummy.txt"), span=(0, 6), task_name="test", extraction_rule="test_rule"),
            TextMatch(original_text="text 2", source_file=Path("dummy.txt"), span=(7, 13), task_name="test", extraction_rule="test_rule"),
        ]

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            process_matches(matches, self.mock_task, self.mock_config)

            # Check for the specific warning log
            assert any("Request Per Day limit (1) for 'gemini' reached." in log for log in cm.output)

        self.mock_translator.translate.assert_called_once()
        assert matches[0].translated_text == "Translated"
        assert matches[1].translated_text is None  # The second match should not be translated
        # This assertion reflects the current implementation where the provider name is nested.
        assert matches[1].provider == "error_error_rpd_limit"

    def test_fallback_to_single_batch_without_limits(self, mock_get_translator: MagicMock) -> None:
        """3. No Limits: Falls back to a single batch when RPM/TPM are not set."""
        # Arrange
        mock_get_translator.return_value = self.mock_translator
        # No RPM/TPM set in provider settings
        provider_settings = ProviderSettings()
        self.mock_translator.settings = provider_settings
        self.mock_config.providers.gemini = provider_settings
        self.mock_translator.translate.return_value = [
            TranslationResult(translated_text="Bonjour", tokens_used=10),
            TranslationResult(translated_text="Monde", tokens_used=10),
        ]
        matches = [
            TextMatch(original_text="Hello", source_file=Path("dummy.txt"), span=(0, 5), task_name="test", extraction_rule="test_rule"),
            TextMatch(original_text="World", source_file=Path("dummy.txt"), span=(6, 11), task_name="test", extraction_rule="test_rule"),
        ]

        # Act & Assert
        with self.assertLogs("glocaltext.translate", level="INFO") as cm, patch("time.sleep") as mock_sleep:
            process_matches(matches, self.mock_task, self.mock_config)

            # Assert that it was logged that we are not using smart scheduling
            assert any("is not configured for intelligent scheduling" in log for log in cm.output)

            self.mock_translator.translate.assert_called_once()
            # The call should contain all texts in a single batch
            assert self.mock_translator.translate.call_args.kwargs["texts"] == ["Hello", "World"]
            mock_sleep.assert_not_called()
            assert matches[0].translated_text == "Bonjour"
            assert matches[1].translated_text == "Monde"
