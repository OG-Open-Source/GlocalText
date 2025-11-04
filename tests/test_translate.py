"""Tests for the main translation functions and logic."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.models import TextMatch
from glocaltext.translate import (
    _apply_protection,
    _check_rule_match,
    _create_batches,
    _create_simple_batches,
    _create_smart_batches,
    _handle_replace_action,
    _is_match_terminated,
    _log_oversized_batch_warning,
    _rpd_session_counts,
    _translator_cache,
    apply_terminating_rules,
    get_translator,
    process_matches,
)
from glocaltext.translators.base import BaseTranslator, TranslationResult
from glocaltext.translators.gemini_translator import GeminiTranslator
from glocaltext.types import ActionRule, MatchRule, Output, Rule, Source, TranslationTask

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
        mock_config = GlocalConfig()
        mock_config.providers["mock"] = ProviderSettings()
        translator1 = get_translator("mock", mock_config)
        translator2 = get_translator("mock", mock_config)
        assert translator1 is not None
        assert isinstance(translator1, BaseTranslator)
        assert translator1 is translator2
        assert "mock" in _translator_cache

    def test_get_translator_init_failure_returns_none(self) -> None:
        """2. Init Failure: Returns None and logs a warning if the translator's __init__ fails."""
        error_message = "API key is missing"
        mock_config = GlocalConfig()
        mock_config.providers["gemini"] = ProviderSettings()
        with (
            self.assertLogs("glocaltext.translate", level="WARNING") as cm,
            patch(
                "glocaltext.translators.gemini_translator.GeminiTranslator.__init__",
                side_effect=ValueError(error_message),
            ),
        ):
            translator = get_translator("gemini", mock_config)
            assert translator is None
            assert "gemini" not in _translator_cache
            expected_log = f"Could not initialize translator 'gemini': {error_message}"
            assert any(expected_log in log for log in cm.output)

    def test_get_translator_unknown_provider(self) -> None:
        """3. Unknown Provider: Raises ValueError for an unconfigured provider."""
        mock_config = GlocalConfig()
        with pytest.raises(ValueError, match=r"Provider 'unknown_provider' is not configured in your settings file."):
            get_translator("unknown_provider", mock_config)

    def test_get_translator_unmapped_provider(self) -> None:
        """4. Unmapped Provider: Returns None for a provider not in TRANSLATOR_MAPPING."""
        mock_config = GlocalConfig()
        mock_config.providers["unmapped"] = ProviderSettings()
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm, patch.dict("glocaltext.translate.TRANSLATOR_MAPPING", {"unmapped": None}):
            translator = get_translator("unmapped", mock_config)
            assert translator is None
            assert "unmapped" not in _translator_cache
            assert any("No translator class mapped for provider: 'unmapped'" in log for log in cm.output)


class TestRuleHandling(unittest.TestCase):
    """Test suite for rule handling and pre-processing functions."""

    def setUp(self) -> None:
        """Set up common test data."""
        self.match = TextMatch(original_text="Hello World", source_file=Path("f.txt"), span=(0, 11), task_name="t", extraction_rule="r")

    def test_check_rule_match_invalid_regex(self) -> None:
        """Rule Handling: _check_rule_match handles invalid regex."""
        rule = Rule(match=MatchRule(regex="[invalid"), action=ActionRule(action="skip"))
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            matched, value = _check_rule_match("text", rule)
            assert not matched
            assert value is None
            assert any("Invalid regex" in log for log in cm.output)

    def test_handle_replace_action_invalid_regex(self) -> None:
        """Rule Handling: _handle_replace_action handles invalid substitution."""
        rule = Rule(match=MatchRule(regex="World"), action=ActionRule(action="replace", value=r"\9"))  # Invalid backreference
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            result = _handle_replace_action("Hello World", "World", rule)
            assert result == "Hello World"  # Should return original text on error
            assert any("Invalid regex substitution" in log for log in cm.output)

    def test_apply_protection_invalid_regex(self) -> None:
        """Rule Handling: _apply_protection handles invalid regex."""
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            result = _apply_protection("text", "[invalid", {})
            assert result == "text"
            assert any("Error during regex protection" in log for log in cm.output)

    def test_apply_terminating_rules_no_rules(self) -> None:
        """Rule Handling: apply_terminating_rules returns all matches if no rules exist."""
        matches = [self.match]
        task = TranslationTask(name="t", source_lang="en", target_lang="fr", translator="m", source=Source(include=["*"]), rules=[])
        remaining, terminated = apply_terminating_rules(matches, task)
        assert remaining == matches
        assert terminated == []

    def test_is_match_terminated_non_terminating_action(self) -> None:
        """Rule Handling: _is_match_terminated ignores non-terminating actions."""
        rule = Rule(match=MatchRule(regex=".*"), action=ActionRule(action="protect"))
        assert not _is_match_terminated(self.match, [rule])


@patch("glocaltext.translate.get_translator")
class TestProcessMatches(unittest.TestCase):
    """Test suite for the process_matches function."""

    def setUp(self) -> None:
        """Set up mock objects for testing process_matches."""
        _rpd_session_counts.clear()
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="gemini",
            source=Source(include=["*.txt"]),
            extraction_rules=[],
            rules=[],
        )
        self.mock_task.output = Output(in_place=True)
        self.mock_translator = MagicMock(spec=GeminiTranslator)
        self.mock_translator.settings = ProviderSettings()
        self.mock_translator.translate.return_value = [TranslationResult(translated_text="Bonjour", tokens_used=10)]
        self.mock_config.providers["gemini"] = self.mock_translator.settings

    def test_smart_scheduling_with_rpm_and_tpm(self, mock_get_translator: MagicMock) -> None:
        """1. Smart Scheduling: Creates batches and delays correctly with RPM/TPM."""
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings(rpm=RPM_LIMIT, tpm=TPM_LIMIT, batch_size=BATCH_SIZE)
        self.mock_translator.settings = provider_settings
        self.mock_config.providers["gemini"] = provider_settings
        self.mock_translator.translate.side_effect = [
            [TranslationResult(translated_text="Batch 1", tokens_used=TOKENS_PER_TEXT_HEAVY)],
            [TranslationResult(translated_text="Batch 2", tokens_used=TOKENS_PER_TEXT_LIGHT)],
        ]

        def mock_count_tokens(texts: list[str], _prompts: dict | None = None) -> int:
            """Mock token counting for smart batching."""
            if len(texts) > 1:
                return TOKENS_PER_TEXT_HEAVY + TOKENS_PER_TEXT_LIGHT
            return TOKENS_PER_TEXT_HEAVY if "heavy" in texts[0] else TOKENS_PER_TEXT_LIGHT

        self.mock_translator.count_tokens.side_effect = mock_count_tokens
        matches = [
            TextMatch(original_text="heavy text", source_file=Path("dummy.txt"), span=(0, 10), task_name="test", extraction_rule="test_rule"),
            TextMatch(original_text="light text", source_file=Path("dummy.txt"), span=(11, 21), task_name="test", extraction_rule="test_rule"),
        ]
        with patch("time.sleep") as mock_sleep:
            process_matches(matches, self.mock_task, self.mock_config, debug=False)

        assert self.mock_translator.translate.call_count == 2  # noqa: PLR2004
        assert self.mock_translator.translate.call_args_list[0].kwargs["texts"] == ["heavy text"]
        assert self.mock_translator.translate.call_args_list[1].kwargs["texts"] == ["light text"]
        mock_sleep.assert_called_once_with(DELAY_SECONDS)
        assert matches[0].translated_text == "Batch 1"
        assert matches[1].translated_text == "Batch 2"

    def test_rpd_limit_stops_execution(self, mock_get_translator: MagicMock) -> None:
        """2. RPD Limit: Stops processing when the daily request limit is reached."""
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings(rpm=RPM_LIMIT, tpm=TPM_LIMIT, rpd=RPD_LIMIT, batch_size=1)
        self.mock_translator.settings = provider_settings
        self.mock_config.providers["gemini"] = provider_settings
        self.mock_translator.translate.return_value = [TranslationResult(translated_text="Translated", tokens_used=TOKENS_PER_TEXT_LIGHT)]
        self.mock_translator.count_tokens.return_value = TOKENS_PER_TEXT_LIGHT
        matches = [
            TextMatch(original_text="text 1", source_file=Path("dummy.txt"), span=(0, 6), task_name="test", extraction_rule="test_rule"),
            TextMatch(original_text="text 2", source_file=Path("dummy.txt"), span=(7, 13), task_name="test", extraction_rule="test_rule"),
        ]
        with self.assertLogs("glocaltext.translate", level="WARNING") as cm:
            process_matches(matches, self.mock_task, self.mock_config, debug=False)
            assert any(f"Request Per Day limit ({RPD_LIMIT}) for 'gemini' reached." in log for log in cm.output)

        self.mock_translator.translate.assert_called_once()
        assert matches[0].translated_text == "Translated"
        assert matches[1].translated_text is None
        assert matches[1].provider == "error_rpd_limit"

    def test_fallback_to_single_batch_without_limits(self, mock_get_translator: MagicMock) -> None:
        """3. No Limits: Falls back to a single batch when RPM/TPM are not set."""
        mock_get_translator.return_value = self.mock_translator
        provider_settings = ProviderSettings()
        self.mock_translator.settings = provider_settings
        self.mock_config.providers["gemini"] = provider_settings
        self.mock_translator.translate.return_value = [
            TranslationResult(translated_text="Bonjour", tokens_used=10),
            TranslationResult(translated_text="Monde", tokens_used=10),
        ]
        matches = [
            TextMatch(original_text="Hello", source_file=Path("dummy.txt"), span=(0, 5), task_name="test", extraction_rule="test_rule"),
            TextMatch(original_text="World", source_file=Path("dummy.txt"), span=(6, 11), task_name="test", extraction_rule="test_rule"),
        ]
        with self.assertLogs("glocaltext.translate", level="INFO") as cm, patch("time.sleep") as mock_sleep:
            process_matches(matches, self.mock_task, self.mock_config, debug=False)
            assert any("is not configured for intelligent scheduling" in log for log in cm.output)
            self.mock_translator.translate.assert_called_once()
            assert self.mock_translator.translate.call_args.kwargs["texts"] == ["Hello", "World"]
            mock_sleep.assert_not_called()
            assert matches[0].translated_text == "Bonjour"
            assert matches[1].translated_text == "Monde"

    @patch("glocaltext.translate._select_provider")
    def test_unconfigured_provider_raises_error(self, mock_select_provider: MagicMock, mock_get_translator: MagicMock) -> None:
        """4. Unconfigured Provider: Raises ValueError if the task's translator is not in settings."""
        self.mock_task.translator = "unconfigured_provider"
        error_msg = f"Task '{self.mock_task.name}' specified translator 'unconfigured_provider', but it is not configured in 'providers'."
        mock_select_provider.side_effect = ValueError(error_msg)
        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]
        with pytest.raises(ValueError, match=error_msg):
            process_matches(matches, self.mock_task, self.mock_config, debug=False)
        mock_select_provider.assert_called_once()
        mock_get_translator.assert_not_called()
        self.mock_translator.translate.assert_not_called()
        assert matches[0].translated_text is None
        assert matches[0].provider is None

    def test_translation_api_error_handling(self, mock_get_translator: MagicMock) -> None:
        """6. API Error: Handles exceptions during the API call gracefully."""
        mock_get_translator.return_value = self.mock_translator
        self.mock_translator.translate.side_effect = Exception("API is down")
        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]
        with self.assertLogs("glocaltext.translate", level="ERROR") as cm:
            process_matches(matches, self.mock_task, self.mock_config, debug=False)
            assert any("Error translating batch" in log for log in cm.output)
        self.mock_translator.translate.assert_called_once()
        assert matches[0].translated_text is None
        assert matches[0].provider == "error_gemini"

    def test_process_matches_translator_init_fails(self, mock_get_translator: MagicMock) -> None:
        """7. Init Failure: Handles failure to initialize a translator."""
        mock_get_translator.return_value = None
        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]
        with self.assertLogs("glocaltext.translate", level="ERROR") as cm:
            process_matches(matches, self.mock_task, self.mock_config, debug=False)
            assert "CRITICAL: Could not initialize any translator" in cm.output[0]

        assert matches[0].provider == "initialization_error"

    def test_process_matches_simple_provider(self, mock_get_translator: MagicMock) -> None:
        """8. Simple Provider: Correctly dispatches to the simple provider logic."""
        self.mock_task.translator = "mock"  # A simple provider
        mock_simple_translator = MagicMock(spec=BaseTranslator)
        mock_simple_translator.translate.return_value = [TranslationResult(translated_text="Bonjour", tokens_used=5)]
        mock_get_translator.return_value = mock_simple_translator

        matches = [TextMatch(original_text="Hello", source_file=Path("f.txt"), span=(0, 5), task_name="t", extraction_rule="r")]
        process_matches(matches, self.mock_task, self.mock_config, debug=False)

        mock_simple_translator.translate.assert_called_once_with(
            texts=["Hello"],
            target_language="fr",
            source_language="en",
            debug=False,
            prompts=None,
        )
        assert matches[0].translated_text == "Bonjour"
        assert matches[0].provider == "mock"


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
        assert _create_simple_batches(texts, 0) == [["a", "b", "c", "d", "e"]]
        assert _create_simple_batches([], SMALL_BATCH_SIZE) == []

    def test_create_smart_batches_tpm_limit(self) -> None:
        """2. Smart Batches: Creates batches respecting TPM limits."""
        texts = ["text1", "text2", "text3"]
        self.mock_translator.count_tokens.side_effect = lambda texts, _prompts: len(texts) * TOKENS_PER_TEXT_LIGHT
        batches = _create_smart_batches(self.mock_translator, texts, batch_size=EQUAL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)
        assert len(batches) == 2  # noqa: PLR2004
        assert batches[0] == ["text1", "text2"]
        assert batches[1] == ["text3"]

    def test_create_smart_batches_batch_size_limit(self) -> None:
        """3. Smart Batches: Creates batches respecting batch_size limits."""
        texts = ["t1", "t2", "t3"]
        self.mock_translator.count_tokens.side_effect = lambda texts, _prompts: len(texts) * TOKENS_PER_TEXT_SIMPLE
        batches = _create_smart_batches(self.mock_translator, texts, batch_size=SMALL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)
        assert len(batches) == 2  # noqa: PLR2004
        assert batches[0] == ["t1", "t2"]
        assert batches[1] == ["t3"]

    @patch("glocaltext.translate.logger")
    def test_log_oversized_batch_warning(self, mock_logger: MagicMock) -> None:
        """4. Oversized Warning: Logs a warning for a single item exceeding TPM."""
        self.mock_translator.count_tokens.return_value = TOKENS_FOR_OVERSIZED
        _log_oversized_batch_warning(self.mock_translator, ["oversized text"], tpm=TPM_LIMIT, prompts=None)
        mock_logger.warning.assert_called_once()
        assert "exceeds the TPM limit" in mock_logger.warning.call_args[0][0]

    def test_create_batches_delegation(self) -> None:
        """5. Batch Dispatch: Delegates to simple or smart batching correctly."""
        texts = ["a", "b", "c"]
        provider_settings = ProviderSettings(max_tokens_per_batch=TPM_LIMIT)
        self.mock_translator.settings = provider_settings
        with patch("glocaltext.translate._create_smart_batches") as mock_smart:
            _create_batches(self.mock_translator, texts, batch_size=EQUAL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)
            mock_smart.assert_called_once()
        with patch("glocaltext.translate._create_simple_batches") as mock_simple:
            _create_batches(self.mock_translator, texts, batch_size=EQUAL_BATCH_SIZE, tpm=None, prompts=None)
            mock_simple.assert_called_once()


if __name__ == "__main__":
    unittest.main()
