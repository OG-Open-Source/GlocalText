"""Tests for the main translation functions and logic."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.models import TextMatch
from glocaltext.processing.processors import calculate_checksum
from glocaltext.translate import (
    _apply_protection,
    _check_full_coverage,
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
        with self.assertLogs("glocaltext.translate", level="DEBUG") as cm:
            matched, value = _check_rule_match("text", rule)
            assert not matched
            assert value is None
            assert any("Skipping pattern with regex error" in log for log in cm.output)

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

        assert self.mock_translator.translate.call_count == 2
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
        assert len(batches) == 2
        assert batches[0] == ["text1", "text2"]
        assert batches[1] == ["text3"]

    def test_create_smart_batches_batch_size_limit(self) -> None:
        """3. Smart Batches: Creates batches respecting batch_size limits."""
        texts = ["t1", "t2", "t3"]
        self.mock_translator.count_tokens.side_effect = lambda texts, _prompts: len(texts) * TOKENS_PER_TEXT_SIMPLE
        batches = _create_smart_batches(self.mock_translator, texts, batch_size=SMALL_BATCH_SIZE, tpm=TPM_LIMIT, prompts=None)
        assert len(batches) == 2
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


class TestFullCoverageDetection(unittest.TestCase):
    """Test suite for Phase 2.3: Full Coverage Detection in Terminating Rules."""

    def setUp(self) -> None:
        """Set up common test data."""
        self.source_file = Path("test.txt")

    def test_full_coverage_skip_rules(self) -> None:
        """1. Full Coverage: Multiple skip rules that fully cover the text."""
        # To achieve full coverage, rules must cover ALL characters including spaces
        match = TextMatch(original_text="who are you", source_file=self.source_file, span=(0, 11), task_name="test", extraction_rule="test_rule")
        rules = [
            Rule(match=MatchRule(regex="who"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=" "), action=ActionRule(action="skip")),  # Cover spaces
            Rule(match=MatchRule(regex="are"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex="you"), action=ActionRule(action="skip")),
        ]

        # Check full coverage detection
        is_covered = _check_full_coverage(match, rules)
        assert is_covered is True, "Text should be fully covered by skip rules"

    def test_partial_coverage_skip_rules(self) -> None:
        """2. Partial Coverage: Skip rules that don't fully cover the text."""
        # Example: "who are you and me" with only "who" and "are" skipped
        match = TextMatch(original_text="who are you and me", source_file=self.source_file, span=(0, 18), task_name="test", extraction_rule="test_rule")
        rules = [
            Rule(match=MatchRule(regex="who"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex="are"), action=ActionRule(action="skip")),
        ]

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is False, "Text should NOT be fully covered (missing 'you and me')"

    def test_full_coverage_overlapping_rules(self) -> None:
        """3. Overlapping Rules: Rules that overlap should merge coverage correctly."""
        # Example: "Hello World" with overlapping skip and protect
        match = TextMatch(original_text="Hello World", source_file=self.source_file, span=(0, 11), task_name="test", extraction_rule="test_rule")
        rules = [
            Rule(match=MatchRule(regex="Hello W"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex="World"), action=ActionRule(action="protect")),
        ]

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is True, "Overlapping rules should merge to full coverage"

    def test_full_coverage_mixed_rule_types(self) -> None:
        """
        4. Mixed Rules: Skip, replace, and protect rules combined.

        Coverage-aware behavior:
        - Replace rule executes first: "test content" -> "testcontent" (removes space)
        - Coverage checks processed_text "testcontent" against skip/protect rules
        - Skip rule "test" matches "test" in "testcontent" (4 chars)
        - Protect rule "content" matches "content" in "testcontent" (7 chars)
        - Total: 11 chars covered out of 11 chars -> 100% coverage
        """
        match = TextMatch(original_text="test content", source_file=self.source_file, span=(0, 12), task_name="test", extraction_rule="test_rule")

        # First, simulate replace rule execution
        match.processed_text = "testcontent"  # After replace rule removes space

        rules = [
            Rule(match=MatchRule(regex="test"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=" "), action=ActionRule(action="replace", value="")),
            Rule(match=MatchRule(regex="content"), action=ActionRule(action="protect")),
        ]

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is True, "Mixed rule types should achieve full coverage on processed_text"

    def test_empty_text_is_fully_covered(self) -> None:
        """5. Edge Case: Empty text should be considered fully covered."""
        match = TextMatch(original_text="", source_file=self.source_file, span=(0, 0), task_name="test", extraction_rule="test_rule")
        rules = [
            Rule(match=MatchRule(regex="test"), action=ActionRule(action="skip")),
        ]

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is True, "Empty text should be fully covered"

    def test_no_rules_not_covered(self) -> None:
        """6. Edge Case: No rules means text is NOT covered."""
        match = TextMatch(original_text="some text", source_file=self.source_file, span=(0, 9), task_name="test", extraction_rule="test_rule")
        rules: list[Rule] = []

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is False, "No rules means text is not covered"

    def test_apply_terminating_rules_with_full_coverage(self) -> None:
        """7. Integration: apply_terminating_rules() detects full coverage."""
        match = TextMatch(original_text="who are you", source_file=self.source_file, span=(0, 11), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="who"), action=ActionRule(action="skip")),
                Rule(match=MatchRule(regex=" "), action=ActionRule(action="skip")),  # Cover spaces
                Rule(match=MatchRule(regex="are"), action=ActionRule(action="skip")),
                Rule(match=MatchRule(regex="you"), action=ActionRule(action="skip")),
            ],
        )

        unhandled, terminated = apply_terminating_rules([match], task)

        # Match should be terminated due to full coverage
        assert len(terminated) == 1, "One match should be terminated"
        assert len(unhandled) == 0, "No unhandled matches"
        assert terminated[0].provider == "fully_covered", "Provider should be 'fully_covered'"
        assert terminated[0].translated_text == "who are you", "Translated text should be original"

    def test_apply_terminating_rules_partial_coverage(self) -> None:
        """8. Integration: Partial coverage should NOT terminate translation."""
        match = TextMatch(original_text="Hello World", source_file=self.source_file, span=(0, 11), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="Hello"), action=ActionRule(action="skip")),
                # "Hello" [0, 5) is covered, but " World" [5, 11) is NOT covered
                # Partial coverage - translation should proceed
            ],
        )

        unhandled, terminated = apply_terminating_rules([match], task)

        # Match should remain unhandled (needs translation)
        assert len(unhandled) == 1, "One match should be unhandled"
        assert len(terminated) == 0, "No terminated matches"

    def test_full_coverage_with_anchors(self) -> None:
        """9. Anchors: Full match with anchors should be detected."""
        match = TextMatch(original_text="who are", source_file=self.source_file, span=(0, 7), task_name="test", extraction_rule="test_rule")
        rules = [
            Rule(match=MatchRule(regex="^who are$"), action=ActionRule(action="skip")),
        ]

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is True, "Anchored full match should be detected as full coverage"

    def test_full_coverage_with_spaces(self) -> None:
        """10. Spaces: Coverage should include whitespace characters."""
        match = TextMatch(original_text="a b c", source_file=self.source_file, span=(0, 5), task_name="test", extraction_rule="test_rule")
        rules = [
            Rule(match=MatchRule(regex="a"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex=" "), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex="b"), action=ActionRule(action="skip")),
            Rule(match=MatchRule(regex="c"), action=ActionRule(action="skip")),
        ]

        is_covered = _check_full_coverage(match, rules)
        assert is_covered is True, "All characters including spaces should be covered"


class TestReplaceRuleExecution(unittest.TestCase):
    """
    Test suite for Phase 4: Replace Rule Execution Order (Solution A).

    These tests verify that replace rules are executed BEFORE coverage detection,
    ensuring partial-match replace rules work correctly even when text is fully covered.
    """

    def setUp(self) -> None:
        """Set up common test data."""
        self.source_file = Path("test.txt")

    def test_partial_match_replace_rule_executes(self) -> None:
        """1. Partial Match Replace: Replace rule executes on partial match before coverage check."""
        # Scenario: Text "who are you" has:
        # - "who" and "you" covered by skip rules (partial coverage)
        # - "are" should be replaced with "were" (partial match replace)
        match = TextMatch(original_text="who are you", source_file=self.source_file, span=(0, 11), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="are"), action=ActionRule(action="replace", value="were")),
                Rule(match=MatchRule(regex="who"), action=ActionRule(action="skip")),
                Rule(match=MatchRule(regex="you"), action=ActionRule(action="skip")),
            ],
        )

        unhandled, terminated = apply_terminating_rules([match], task)

        # The replace rule should execute first, storing modified text in processed_text
        # Coverage detection uses ORIGINAL text (not processed_text)
        # Since only "who" and "you" are skipped in original (not "are"), text is NOT fully covered
        assert len(unhandled) == 1, "Match should remain unhandled (needs translation)"
        assert len(terminated) == 0, "No matches should be terminated"
        assert match.original_text == "who are you", "original_text must remain unchanged for cache consistency"
        assert match.processed_text == "who were you", "processed_text should contain the replaced text"

    def test_replace_before_full_coverage_detection(self) -> None:
        """2. Replace + Full Coverage: Replace executes first, then full coverage is detected."""
        # Scenario: After replace, the modified text becomes fully covered
        match = TextMatch(original_text="who are you", source_file=self.source_file, span=(0, 11), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                # Step 1: Replace "are" with "is" -> "who is you"
                Rule(match=MatchRule(regex="are"), action=ActionRule(action="replace", value="is")),
                # Step 2: Check coverage on "who is you"
                Rule(match=MatchRule(regex="who"), action=ActionRule(action="skip")),
                Rule(match=MatchRule(regex=" "), action=ActionRule(action="skip")),
                Rule(match=MatchRule(regex="is"), action=ActionRule(action="skip")),
                Rule(match=MatchRule(regex="you"), action=ActionRule(action="skip")),
            ],
        )

        unhandled, terminated = apply_terminating_rules([match], task)

        # After replace: processed_text = "who is you", original_text = "who are you"
        # Coverage check uses ORIGINAL text: "who" + " " + "are" + " " + "you"
        # Skip rules check "who", " ", "are", " ", "you" -> DOES achieve 100% coverage!
        # Result: Match is terminated as fully_covered
        assert len(terminated) == 1, "Match should be terminated (100% coverage on original text)"
        assert len(unhandled) == 0, "No unhandled matches"
        assert terminated[0].original_text == "who are you", "original_text must remain unchanged"
        assert terminated[0].processed_text == "who is you", "processed_text should contain the replaced text"
        assert terminated[0].provider == "fully_covered", "Should be marked as fully_covered"
        assert terminated[0].translated_text == "who is you", "translated_text should use processed_text"

    def test_multiple_replace_rules_sequential_execution(self) -> None:
        """3. Multiple Replaces: Multiple replace rules execute sequentially."""
        match = TextMatch(original_text="Hello World Test", source_file=self.source_file, span=(0, 16), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="Hello"), action=ActionRule(action="replace", value="Hi")),
                Rule(match=MatchRule(regex="World"), action=ActionRule(action="replace", value="Earth")),
                Rule(match=MatchRule(regex="Test"), action=ActionRule(action="replace", value="Example")),
            ],
        )

        unhandled, _terminated = apply_terminating_rules([match], task)

        # All three replaces should execute sequentially in processed_text
        assert len(unhandled) == 1, "Match should need translation"
        assert match.original_text == "Hello World Test", "original_text must remain unchanged for cache consistency"
        assert match.processed_text == "Hi Earth Example", "All replace rules should execute in processed_text"

    def test_replace_then_skip_workflow(self) -> None:
        """
        4. Replace + Skip: Replace executes, then skip rule terminates translation.

        Coverage-aware design (NEW behavior):
        - Replace executes: "translate this" -> "skip this" (processed_text set)
        - Skip rules now check processed_text (if exists) instead of original_text
        - Skip rule "^skip this$" fully matches processed_text "skip this"
        - Result: Match is terminated by skip rule (provider = "skipped")

        This validates that skip rules correctly use processed_text after replace rules execute.
        """
        match = TextMatch(original_text="translate this", source_file=self.source_file, span=(0, 14), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                # Step 1: Replace "translate" with "skip" -> "skip this"
                Rule(match=MatchRule(regex="translate"), action=ActionRule(action="replace", value="skip")),
                # Step 2: Skip rule matches the processed text fully
                Rule(match=MatchRule(regex="^skip this$"), action=ActionRule(action="skip")),
            ],
        )

        unhandled, terminated = apply_terminating_rules([match], task)

        # After replace: processed_text = "skip this", original_text = "translate this"
        # Skip rule "^skip this$" fully matches processed_text -> triggers BOTH:
        # 1. Full coverage detection (100% coverage) -> provider = "fully_covered"
        # 2. Traditional skip termination (full match) -> but full coverage runs first
        # Result: Match is terminated via full coverage detection
        assert len(terminated) == 1, "Match should be terminated by skip rule matching processed_text"
        assert len(unhandled) == 0, "No matches should remain unhandled"
        assert terminated[0].provider == "fully_covered", "Provider should be 'fully_covered' (full match triggers coverage detection)"
        assert match.original_text == "translate this", "original_text must remain unchanged"
        assert match.processed_text == "skip this", "processed_text should contain the replaced text"

    def test_replace_with_overlapping_patterns(self) -> None:
        """5. Overlapping Patterns: Replace rules with overlapping patterns execute correctly."""
        match = TextMatch(original_text="test testing tester", source_file=self.source_file, span=(0, 19), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                # First rule replaces "test" -> "exam"
                Rule(match=MatchRule(regex="test"), action=ActionRule(action="replace", value="exam")),
                # This will affect all three words: "exam examing examer"
            ],
        )

        unhandled, _terminated = apply_terminating_rules([match], task)

        # The regex should replace all occurrences of "test" in processed_text
        assert len(unhandled) == 1, "Match should need translation"
        assert match.original_text == "test testing tester", "original_text must remain unchanged"
        # Note: regex.sub() replaces ALL occurrences by default
        assert match.processed_text == "exam examing examer", "All occurrences should be replaced in processed_text"
        assert "exam" in match.processed_text, "Replace should modify processed_text"

    def test_no_replace_rules_no_modification(self) -> None:
        """6. No Replace Rules: Text remains unchanged when no replace rules exist."""
        match = TextMatch(original_text="original text", source_file=self.source_file, span=(0, 13), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="text"), action=ActionRule(action="skip")),
            ],
        )

        unhandled, _terminated = apply_terminating_rules([match], task)

        # No replace rules, text should remain unchanged
        assert match.original_text == "original text", "Text should not be modified"
        assert len(unhandled) == 1, "Match should need translation"

    def test_replace_invalid_regex_logs_warning(self) -> None:
        """7. Invalid Regex: Replace rule with invalid regex logs debug message and skips replacement."""
        match = TextMatch(original_text="test content", source_file=self.source_file, span=(0, 12), task_name="test", extraction_rule="test_rule")
        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="[invalid"), action=ActionRule(action="replace", value="replacement")),
            ],
        )

        # Changed from WARNING to DEBUG level as backreference errors are expected
        with self.assertLogs("glocaltext.translate", level="DEBUG") as cm:
            unhandled, _terminated = apply_terminating_rules([match], task)
            assert any("Skipping pattern with regex error" in log for log in cm.output), "Should log regex error at DEBUG level"

        # Text should remain unchanged due to invalid regex
        assert match.original_text == "test content", "Text should not be modified on error"
        assert len(unhandled) == 1, "Match should still need translation"

    def test_replace_then_skip_different_text(self) -> None:
        """
        8. Replace + Skip with non-matching pattern should send for translation.

        This test verifies the coverage-aware replace rules behavior where:
        - Replace rules execute first and produce processed_text
        - Coverage detection checks skip/protect rules against processed_text
        - If skip/protect rules don't match processed_text, translation proceeds

        Scenario:
        - Original text: '%d 核心'
        - Replace rule: '^%d 核心$' -> '%d cores'
        - Skip rule: '^%d 核心$' (matches original, but NOT processed text)

        Expected behavior:
        - Replace executes: '%d 核心' -> '%d cores'
        - Coverage checks processed_text '%d cores' against skip rule '^%d 核心$' -> NO MATCH
        - Result: 0% coverage, sent for translation (but replace already executed)
        """
        match = TextMatch(
            original_text="%d 核心",
            source_file=self.source_file,
            span=(0, 5),
            task_name="test",
            extraction_rule="test_rule",
        )
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                # Replace rule: changes text to English
                Rule(match=MatchRule(regex=r"^%d 核心$"), action=ActionRule(action="replace", value="%d cores")),
                # Skip rule: matches the ORIGINAL Chinese text, but not the processed English text
                Rule(match=MatchRule(regex=r"^%d 核心$"), action=ActionRule(action="skip")),
            ],
        )

        unhandled, terminated = apply_terminating_rules([match], task)

        # Verify coverage-aware behavior:
        # - Replace executes: processed_text = "%d cores"
        # - Coverage checks processed_text "%d cores" against skip rule "^%d 核心$" -> NO MATCH
        # - Result: sent for translation (unhandled)
        assert len(unhandled) == 1, "Match should be unhandled (sent for translation)"
        assert len(terminated) == 0, "No terminated matches"
        assert unhandled[0].original_text == "%d 核心", "original_text must remain unchanged"
        assert unhandled[0].processed_text == "%d cores", "processed_text should contain the replaced text"


if __name__ == "__main__":
    unittest.main()


class TestCacheChecksumConsistency(unittest.TestCase):
    """Regression test for bug: Replace rule modifying original_text breaks cache checksum consistency."""

    def test_replace_rule_preserves_original_text_for_cache(self) -> None:
        """
        Regression test for critical bug: Replace rules must not modify match.original_text.

        BUG DESCRIPTION:
        When replace rules modified match.original_text, cache checksum calculation became inconsistent:
        - Cache write used checksum of MODIFIED text
        - Cache read used checksum of ORIGINAL text
        - Result: Cache永久失效 (permanent cache miss)

        FIX:
        - Replace rules now store modified text in match.processed_text
        - match.original_text remains unchanged for consistent checksum calculation
        - Translation uses processed_text when available

        This test verifies the fix by:
        1. Creating a match with text that triggers a replace rule
        2. Applying terminating rules (including replace)
        3. Verifying original_text is UNCHANGED
        4. Verifying processed_text contains the MODIFIED text
        """
        # Create a task with a replace rule
        task = TranslationTask(
            name="test_task",
            task_id="test-id",
            translator="mock",
            source_lang="zh-TW",
            target_lang="en",
            extraction_rules=[".*"],
            source=Source(include=["*.txt"]),
            output=Output(in_place=True),
            rules=[Rule(match=MatchRule(regex=r"\|"), action=ActionRule(action="replace", value=r"\\|"))],
        )

        # Create a match with text containing the pattern to be replaced
        original_text = "text | with pipe"
        match = TextMatch(
            original_text=original_text,
            source_file=Path("test.txt"),
            span=(0, len(original_text)),
            task_name="test_task",
            extraction_rule=".*",
        )

        # Apply terminating rules
        unhandled, terminated = apply_terminating_rules([match], task)

        # CRITICAL ASSERTIONS: Verify the fix
        # 1. original_text must remain UNCHANGED for cache consistency
        assert match.original_text == original_text, f"BUG DETECTED: original_text was modified! Expected '{original_text}', got '{match.original_text}'"

        # 2. processed_text must contain the MODIFIED text
        expected_processed = "text \\| with pipe"
        assert match.processed_text == expected_processed, f"processed_text not set correctly! Expected '{expected_processed}', got '{match.processed_text}'"

        # 3. Match should not be terminated (replace rules don't terminate translation)
        assert match in unhandled, "Match should remain unhandled after replace rule"
        assert match not in terminated, "Replace rule should not terminate the match"

    def test_cache_checksum_consistency_with_replace_rules(self) -> None:
        """
        Integration test: Verify cache checksum remains consistent across multiple runs with replace rules.

        Simulates the user's reported bug scenario:
        - Run 1: Extract text, apply replace rule, calculate checksum, write to cache
        - Run 2: Re-extract same text (original form), calculate checksum, read from cache
        - EXPECTED: Checksums match, cache hit occurs
        """
        original_text = "- 啟動時間：${CLR2}$(who -b)${CLR0}"

        # Simulate Run 1: First extraction
        match_run1 = TextMatch(
            original_text=original_text,
            source_file=Path("utilkit.sh"),
            span=(0, len(original_text)),
            task_name="test_task",
            extraction_rule=".*",
        )

        # Calculate checksum BEFORE any rules are applied (this is what gets cached)
        checksum_before_rules = calculate_checksum(match_run1.original_text)

        # Apply replace rule (simulating the bug scenario)
        task = TranslationTask(
            name="test_task",
            task_id="test-id",
            translator="mock",
            source_lang="zh-TW",
            target_lang="en",
            extraction_rules=[".*"],
            source=Source(include=["*.sh"]),
            output=Output(in_place=True),
            rules=[Rule(match=MatchRule(regex=r"\$"), action=ActionRule(action="replace", value=r"\\$"))],
        )

        apply_terminating_rules([match_run1], task)

        # Verify: original_text unchanged, so checksum for cache remains consistent
        checksum_after_rules = calculate_checksum(match_run1.original_text)
        assert checksum_before_rules == checksum_after_rules, "CACHE BUG: Checksum changed after applying rules! This breaks cache consistency."

        # Simulate Run 2: Re-extraction (fresh match with original text)
        match_run2 = TextMatch(
            original_text=original_text,  # Same original text
            source_file=Path("utilkit.sh"),
            span=(0, len(original_text)),
            task_name="test_task",
            extraction_rule=".*",
        )

        checksum_run2 = calculate_checksum(match_run2.original_text)

        # CRITICAL: Checksums must match for cache hit
        assert checksum_run2 == checksum_before_rules, f"CACHE MISS BUG: Run 2 checksum differs from Run 1!\nRun 1 checksum: {checksum_before_rules}\nRun 2 checksum: {checksum_run2}\nThis causes permanent cache miss in --incremental mode!"
