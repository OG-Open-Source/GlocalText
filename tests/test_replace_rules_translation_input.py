"""
Test that Replace rules correctly modify text BEFORE it reaches the translator.

This test suite verifies the critical data flow:
    Replace Rules Process Text → processed_text → Translator Input

Key Validation Points:
1. When Replace rules modify text, translator receives the MODIFIED text
2. When no Replace rules match, translator receives the ORIGINAL text
3. Multiple Replace rules chain correctly
4. Replace + other terminating rules (Skip/Protect) work together
"""

import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.translate import process_matches
from glocaltext.translators.mock_translator import MockTranslator
from glocaltext.types import ActionRule, MatchRule, Output, Rule, Source, TextMatch, TranslationTask


class TestReplaceRulesTranslationInput(unittest.TestCase):
    """Test suite verifying Replace rules correctly modify translator input."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Create minimal config
        self.config = GlocalConfig()
        self.config.providers["mock"] = ProviderSettings()

        # Create test task
        self.task = TranslationTask(
            name="test_task",
            source_lang="zh-TW",
            target_lang="en",
            translator="mock",
            source=Source(include=["*.txt"]),
            output=Output(in_place=True),
            extraction_rules=[],
            rules=[],
        )

    def test_replace_rule_modifies_translator_input(self) -> None:
        """
        1. Replace Rule: Translator receives PROCESSED text, not original.

        Flow:
        - Original: "系統資訊(未知)"
        - Replace Rule: "未知" → "Unknown"
        - Expected translator input: "系統資訊(Unknown)"
        """
        # Setup: Create a match with original text
        match = TextMatch(
            original_text="系統資訊(未知)",
            source_file=self.temp_path / "test.txt",
            span=(0, 11),
            task_name="test_task",
            extraction_rule="test_pattern",
        )

        # Setup: Create Replace rule
        replace_rule = Rule(
            match=MatchRule(regex="未知"),
            action=ActionRule(action="replace", value="Unknown"),
        )
        self.task.rules = [replace_rule]

        # Capture what text the translator actually receives
        received_texts: list[str] = []

        def capture_translate(texts: list[str], **kwargs) -> list[Any]:  # noqa: ANN003, ARG001
            """Capture the texts sent to translator."""
            received_texts.extend(texts)
            # Return mock translation results
            return [type("TranslationResult", (), {"translated_text": f"[MOCK] {t}", "tokens_used": len(t)})() for t in texts]

        # Execute: Process matches with mocked translator
        with patch.object(MockTranslator, "translate", side_effect=capture_translate):
            process_matches(
                matches=[match],
                task=self.task,
                config=self.config,
                debug=False,
                dry_run=False,
            )

        # Verify: Translator received the PROCESSED text
        assert len(received_texts) == 1, "Should have sent exactly 1 text to translator"
        assert received_texts[0] == "系統資訊(Unknown)", "Translator should receive text AFTER Replace rule processing"
        assert received_texts[0] != "系統資訊(未知)", "Translator should NOT receive original unprocessed text"

    def test_no_replace_rule_sends_original_text(self) -> None:
        """
        2. No Replace Rule: Translator receives ORIGINAL text unchanged.

        Flow:
        - Original: "測試文本"
        - No Replace rules
        - Expected translator input: "測試文本" (unchanged)
        """
        match = TextMatch(
            original_text="測試文本",
            source_file=self.temp_path / "test.txt",
            span=(0, 4),
            task_name="test_task",
            extraction_rule="test_pattern",
        )

        # No replace rules
        self.task.rules = []

        received_texts: list[str] = []

        def capture_translate(texts: list[str], **kwargs) -> list[Any]:  # noqa: ANN003, ARG001
            received_texts.extend(texts)
            return [type("TranslationResult", (), {"translated_text": f"[MOCK] {t}", "tokens_used": len(t)})() for t in texts]

        with patch.object(MockTranslator, "translate", side_effect=capture_translate):
            process_matches(
                matches=[match],
                task=self.task,
                config=self.config,
                debug=False,
                dry_run=False,
            )

        assert len(received_texts) == 1
        assert received_texts[0] == "測試文本", "Without Replace rules, translator gets original text"

    def test_multiple_replace_rules_chain_correctly(self) -> None:
        """
        3. Multiple Replace Rules: Changes cascade correctly.

        Flow:
        - Original: "年/月/日"
        - Rule 1: "年" → "Year"
        - Rule 2: "月" → "Month"
        - Rule 3: "日" → "Day"
        - Expected translator input: "Year/Month/Day"
        """
        match = TextMatch(
            original_text="年/月/日",
            source_file=self.temp_path / "test.txt",
            span=(0, 5),
            task_name="test_task",
            extraction_rule="test_pattern",
        )

        # Multiple Replace rules that should chain
        self.task.rules = [
            Rule(
                match=MatchRule(regex="年"),
                action=ActionRule(action="replace", value="Year"),
            ),
            Rule(
                match=MatchRule(regex="月"),
                action=ActionRule(action="replace", value="Month"),
            ),
            Rule(
                match=MatchRule(regex="日"),
                action=ActionRule(action="replace", value="Day"),
            ),
        ]

        received_texts: list[str] = []

        def capture_translate(texts: list[str], **kwargs) -> list[Any]:  # noqa: ANN003, ARG001
            received_texts.extend(texts)
            return [type("TranslationResult", (), {"translated_text": f"[MOCK] {t}", "tokens_used": len(t)})() for t in texts]

        with patch.object(MockTranslator, "translate", side_effect=capture_translate):
            process_matches(
                matches=[match],
                task=self.task,
                config=self.config,
                debug=False,
                dry_run=False,
            )

        assert len(received_texts) == 1
        assert received_texts[0] == "Year/Month/Day", "Multiple Replace rules should chain to produce final processed text"

    def test_replace_with_partial_coverage_still_translates(self) -> None:
        """
        4. Partial Replace: Text is modified but still needs translation.

        Flow:
        - Original: "運行時間：2 年 3 月"
        - Replace Rule: "年" → "years", "月" → "months"
        - Processed: "運行時間：2 years 3 months"
        - Should still send to translator (not fully covered)
        """
        match = TextMatch(
            original_text="運行時間：2 年 3 月",
            source_file=self.temp_path / "test.txt",
            span=(0, 12),
            task_name="test_task",
            extraction_rule="test_pattern",
        )

        self.task.rules = [
            Rule(
                match=MatchRule(regex="年"),
                action=ActionRule(action="replace", value="years"),
            ),
            Rule(
                match=MatchRule(regex="月"),
                action=ActionRule(action="replace", value="months"),
            ),
        ]

        received_texts: list[str] = []

        def capture_translate(texts: list[str], **kwargs) -> list[Any]:  # noqa: ANN003, ARG001
            received_texts.extend(texts)
            return [type("TranslationResult", (), {"translated_text": f"[MOCK] {t}", "tokens_used": len(t)})() for t in texts]

        with patch.object(MockTranslator, "translate", side_effect=capture_translate):
            process_matches(
                matches=[match],
                task=self.task,
                config=self.config,
                debug=False,
                dry_run=False,
            )

        # Should still translate (partial coverage)
        assert len(received_texts) == 1
        assert received_texts[0] == "運行時間：2 years 3 months", "Partially replaced text should still be sent for translation"

    def test_batch_processing_uses_processed_text(self) -> None:
        """
        5. Batch Processing: Multiple matches all use processed_text.

        Flow:
        - Match 1: "系統(未知)" → "系統(Unknown)"
        - Match 2: "版本(未知)" → "版本(Unknown)"
        - Match 3: "狀態(未知)" → "狀態(Unknown)"
        All should be sent with processed text in a single batch.
        """
        matches = [
            TextMatch(
                original_text="系統(未知)",
                source_file=self.temp_path / "test.txt",
                span=(0, 6),
                task_name="test_task",
                extraction_rule="test_pattern",
            ),
            TextMatch(
                original_text="版本(未知)",
                source_file=self.temp_path / "test.txt",
                span=(7, 13),
                task_name="test_task",
                extraction_rule="test_pattern",
            ),
            TextMatch(
                original_text="狀態(未知)",
                source_file=self.temp_path / "test.txt",
                span=(14, 20),
                task_name="test_task",
                extraction_rule="test_pattern",
            ),
        ]

        self.task.rules = [
            Rule(
                match=MatchRule(regex="未知"),
                action=ActionRule(action="replace", value="Unknown"),
            ),
        ]

        received_texts: list[str] = []

        def capture_translate(texts: list[str], **kwargs) -> list[Any]:  # noqa: ANN003, ARG001
            received_texts.extend(texts)
            return [type("TranslationResult", (), {"translated_text": f"[MOCK] {t}", "tokens_used": len(t)})() for t in texts]

        with patch.object(MockTranslator, "translate", side_effect=capture_translate):
            process_matches(
                matches=matches,
                task=self.task,
                config=self.config,
                debug=False,
                dry_run=False,
            )

        # All 3 matches should be sent
        assert len(received_texts) == 3
        # All should have processed text
        assert "系統(Unknown)" in received_texts
        assert "版本(Unknown)" in received_texts
        assert "狀態(Unknown)" in received_texts
        # None should have original unprocessed text
        assert "系統(未知)" not in received_texts
        assert "版本(未知)" not in received_texts
        assert "狀態(未知)" not in received_texts


if __name__ == "__main__":
    unittest.main()
