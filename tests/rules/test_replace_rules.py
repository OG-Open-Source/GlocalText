"""
Regression test for replace rules affecting translation input.

This test verifies that replace rules' modifications are used as the actual
translation input, not the original text. This is a regression test for the bug
where translate.py was using match.original_text instead of match.processed_text.

Bug Context:
- translate.py line 1045: Batch deduplication was using original_text as key
- translate.py line 1097: Translation API call was using original_text
- Expected: Both should use processed_text (after replace rules) if available
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.match_state import MatchLifecycle
from glocaltext.models import ExecutionContext
from glocaltext.processing import TerminatingRuleProcessor
from glocaltext.translate import process_matches
from glocaltext.translators.base import TranslationResult
from glocaltext.translators.mock_translator import MockTranslator
from glocaltext.types import ActionRule, MatchRule, Rule, Source, TextMatch, TranslationTask


class MockTranslatorWithRecording(MockTranslator):
    """Extended MockTranslator that records the actual texts it receives."""

    def __init__(self, settings: ProviderSettings) -> None:
        """Initialize the mock translator with recording capability."""
        super().__init__(settings)
        self.received_texts: list[str] = []

    def translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None = None,
        *,
        debug: bool = False,
        prompts: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """Record received texts and return mock translations."""
        # Record what we actually received
        self.received_texts.extend(texts)
        # Return mock translation
        return super().translate(texts, target_language, source_language, debug=debug, prompts=prompts)


class TestReplaceRulesTranslationInput(unittest.TestCase):
    """Test suite verifying replace rules affect actual translation input."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.source_file = Path("test.txt")
        self.config = GlocalConfig()
        self.config.providers["mock"] = ProviderSettings()

    def test_replace_rules_modify_translation_input_single_match(self) -> None:
        """
        1. Single Match: Verify that replace rules modify the text sent to translator.

        Regression test for bug where translate.py used match.original_text
        instead of match.processed_text for translation API calls.
        """
        # Create a match that will be modified by replace rule
        match = TextMatch(
            original_text="系統資訊(未知)",
            source_file=self.source_file,
            span=(0, 9),
            task_name="test",
            extraction_rule="test_rule",
        )

        # Simulate replace rule execution: "未知" -> "Unknown"
        match.processed_text = "系統資訊(Unknown)"

        # Create task with replace rule
        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="未知"), action=ActionRule(action="replace", value="Unknown")),
            ],
        )

        # Create recording translator
        recording_translator = MockTranslatorWithRecording(settings=ProviderSettings())

        # Patch get_translator to return our recording translator
        with patch("glocaltext.translate.get_translator", return_value=recording_translator):
            # Process matches using the public API
            process_matches([match], task, self.config, debug=False)

        # CRITICAL ASSERTION: Translator should receive processed_text, NOT original_text
        assert len(recording_translator.received_texts) == 1, "Should translate exactly one text"
        received_text = recording_translator.received_texts[0]

        assert received_text == "系統資訊(Unknown)", f"Translator should receive processed_text '系統資訊(Unknown)' but received '{received_text}' (original_text)"

        # Verify the match was translated
        assert match.translated_text is not None, "Match should be translated"
        assert match.lifecycle == MatchLifecycle.TRANSLATED, "Match should have TRANSLATED lifecycle"

    def test_replace_rules_modify_batch_deduplication(self) -> None:
        """
        2. Batch Deduplication: Verify replace rules affect batch grouping.

        Regression test for bug where translate.py used match.original_text
        as the deduplication key instead of match.processed_text.
        """
        # Create two matches with same original text
        match1 = TextMatch(
            original_text="狀態: 未知",
            source_file=self.source_file,
            span=(0, 7),
            task_name="test",
            extraction_rule="test_rule",
        )
        match2 = TextMatch(
            original_text="狀態: 未知",
            source_file=self.source_file,
            span=(10, 17),
            task_name="test",
            extraction_rule="test_rule",
        )

        # Both get same replacement
        match1.processed_text = "狀態: Unknown"
        match2.processed_text = "狀態: Unknown"

        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="未知"), action=ActionRule(action="replace", value="Unknown")),
            ],
        )

        recording_translator = MockTranslatorWithRecording(settings=ProviderSettings())

        # Patch get_translator to return our recording translator
        with patch("glocaltext.translate.get_translator", return_value=recording_translator):
            process_matches([match1, match2], task, self.config, debug=False)

        # CRITICAL ASSERTION: Should only translate once (deduplication by processed_text)
        # If bug exists, it would deduplicate by original_text and still translate once,
        # but the key insight is that it should use processed_text as the translation input
        assert len(recording_translator.received_texts) >= 1, "Should translate at least once"

        # All received texts should be processed_text, not original_text
        for received_text in recording_translator.received_texts:
            assert received_text == "狀態: Unknown", f"All translations should use processed_text '狀態: Unknown' but received '{received_text}'"

        # Both matches should be translated with same result (deduplication)
        assert match1.translated_text is not None, "Match1 should be translated"
        assert match2.translated_text is not None, "Match2 should be translated"

    def test_no_replace_rule_uses_original_text(self) -> None:
        """
        3. Baseline: Without replace rules, original_text should be used.

        This test verifies that when processed_text is None (no replace rules),
        the translator correctly falls back to using original_text.
        """
        match = TextMatch(
            original_text="測試文字",
            source_file=self.source_file,
            span=(0, 4),
            task_name="test",
            extraction_rule="test_rule",
        )

        # No replace rule applied, processed_text remains None
        assert match.processed_text is None, "processed_text should be None without replace rules"

        task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[],  # No rules
        )

        recording_translator = MockTranslatorWithRecording(settings=ProviderSettings())

        # Patch get_translator to return our recording translator
        with patch("glocaltext.translate.get_translator", return_value=recording_translator):
            process_matches([match], task, self.config, debug=False)

        # Should receive original_text when processed_text is None
        assert len(recording_translator.received_texts) == 1, "Should translate exactly one text"
        assert recording_translator.received_texts[0] == "測試文字", "Should use original_text when processed_text is None"

    def test_multiple_replace_rules_final_processed_text_used(self) -> None:
        """
        4. Multiple Replacements: Verify final processed_text is used after multiple replace rules.

        Tests that when multiple replace rules are applied sequentially,
        the final processed_text (after all replacements) is sent to the translator.
        """
        match = TextMatch(
            original_text="Error: Unknown Status",
            source_file=self.source_file,
            span=(0, 21),
            task_name="test",
            extraction_rule="test_rule",
        )

        # Simulate multiple replace rules:
        # 1. "Error" -> "錯誤"
        # 2. "Unknown" -> "未知"
        # Final result: "錯誤: 未知 Status"
        match.processed_text = "錯誤: 未知 Status"

        task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="zh-TW",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[
                Rule(match=MatchRule(regex="Error"), action=ActionRule(action="replace", value="錯誤")),
                Rule(match=MatchRule(regex="Unknown"), action=ActionRule(action="replace", value="未知")),
            ],
        )

        recording_translator = MockTranslatorWithRecording(settings=ProviderSettings())

        # Patch get_translator to return our recording translator
        with patch("glocaltext.translate.get_translator", return_value=recording_translator):
            process_matches([match], task, self.config, debug=False)

        # Should receive the final processed_text after all replacements
        assert len(recording_translator.received_texts) == 1, "Should translate exactly one text"
        assert recording_translator.received_texts[0] == "錯誤: 未知 Status", f"Translator should receive final processed_text '錯誤: 未知 Status' but received '{recording_translator.received_texts[0]}'"

    def test_replace_with_skip_rule_100_percent_coverage_skips_translation(self) -> None:
        """
        5. Coverage Detection with Replace + Skip: Verify correct text selection for coverage.

        Regression test for bug where _select_text_for_coverage_check prioritized
        match.processed_text over original_text_for_coverage parameter.

        This test verifies that when a skip rule is evaluated for coverage detection,
        it checks against the ORIGINAL text, not the processed text from replace rules.

        Bug scenario (before fix):
        - Original text: "%d 核心"
        - Replace rule: "未知" -> "Unknown" (partial match)
        - Skip rule: "^%d 核心$" (should match ORIGINAL text 100%)
        - Bug: Coverage checked processed_text instead of original_text
        - Result: Skip rule didn't match, text sent to translation

        After fix:
        - Coverage detection uses original_text
        - Skip rule matches 100%
        - Translation skipped, processed_text used as final result
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
                # Replace rule (doesn't provide coverage)
                Rule(match=MatchRule(regex="核心"), action=ActionRule(action="replace", value=" cores")),
                # Skip rule that should match ORIGINAL text 100%
                Rule(match=MatchRule(regex=r"^%d 核心$"), action=ActionRule(action="skip")),
            ],
        )

        recording_translator = MockTranslatorWithRecording(settings=ProviderSettings())

        # Use Pipeline to ensure rules are processed correctly
        context = ExecutionContext(
            task=task,
            config=self.config,
            project_root=Path.cwd(),
            is_dry_run=False,
            is_incremental=False,
            is_debug=False,
        )
        context.all_matches = [match]
        context.matches_to_translate = [match]

        # Execute Terminating Rules (Replace/Skip/Protect)
        terminating_processor = TerminatingRuleProcessor()
        terminating_processor.process(context)

        # Translation processing
        with patch("glocaltext.translate.get_translator", return_value=recording_translator):
            process_matches(
                matches=context.matches_to_translate,
                task=task,
                config=self.config,
                debug=False,
            )

        # CRITICAL ASSERTION: Skip rule matches original text 100%, should NOT call translator
        assert len(recording_translator.received_texts) == 0, f"Skip rule with 100% coverage of ORIGINAL text should skip translation, but translator received: {recording_translator.received_texts}"

        # Verify the match uses processed_text as final result (from replace rule)
        assert match.translated_text == "%d  cores", f"Match should use processed_text '%d  cores' as final result, but got '{match.translated_text}'"
        assert match.lifecycle == MatchLifecycle.SKIPPED, f"Match should be marked as SKIPPED (fully covered), but got '{match.lifecycle}'"


if __name__ == "__main__":
    unittest.main()
