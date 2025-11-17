"""Tests for the reporting classes."""

import unittest
from pathlib import Path
from unittest.mock import ANY, MagicMock, call, mock_open, patch

from glocaltext.config import GlocalConfig
from glocaltext.match_state import SKIP_SAME_LANGUAGE, MatchLifecycle
from glocaltext.models import ExecutionContext
from glocaltext.reporters.dry_run_reporter import DryRunReporter
from glocaltext.reporters.summary_reporter import SummaryReporter
from glocaltext.types import Source, TextMatch, TranslationTask


class TestDryRunReporter(unittest.TestCase):
    """Test suite for the DryRunReporter."""

    def setUp(self) -> None:
        """Set up common test data."""
        self.task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            source=Source(include=["*.json"]),
            translator="mock",
        )
        self.config = GlocalConfig(tasks=[self.task])
        self.reporter = DryRunReporter()

    def _create_mock_context(self) -> ExecutionContext:
        """Create a default mock ExecutionContext."""
        context = ExecutionContext(task=self.task, config=self.config)
        context.files_to_process = [Path("file1.txt"), Path("file2.txt")]
        context.all_matches = [
            TextMatch(
                original_text="Hello",
                source_file=Path("file1.txt"),
                span=(0, 5),
                task_name="test_task",
                extraction_rule="rule1",
            ),
            TextMatch(
                original_text="World",
                source_file=Path("file2.txt"),
                span=(0, 5),
                task_name="test_task",
                extraction_rule="rule1",
            ),
        ]
        return context

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_generate_creates_report_file(self, mock_file: MagicMock) -> None:
        """1. Generate: Creates a report file with the correct name."""
        context = self._create_mock_context()
        self.reporter.generate(context)
        mock_file.assert_called_once_with("w", encoding="utf-8")
        assert mock_file().write.call_count == 1
        assert f"# Dry Run Report for Task: `{self.task.name}`" in mock_file().write.call_args[0][0]

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_build_report_with_no_files(self, mock_file: MagicMock) -> None:
        """2. Content: Handles cases with no files to process."""
        context = self._create_mock_context()
        context.files_to_process = []
        self.reporter.generate(context)
        report_content = mock_file().write.call_args[0][0]
        assert "## 📂 File Details\n\nNo files found to process.\n" in report_content

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_build_report_with_all_match_types(self, mock_file: MagicMock) -> None:
        """3. Content: Correctly renders all text lifecycle categories."""
        context = self._create_mock_context()
        # Create a match with processed_text to simulate replace rule behavior
        replaced_match = TextMatch("Replaced", Path("f1.txt"), (0, 8), "test", "test")
        replaced_match.lifecycle = MatchLifecycle.REPLACED
        replaced_match.processed_text = "Modified"  # Simulate replace rule modification

        skipped_match = TextMatch("Skipped", Path("f1.txt"), (0, 7), "test", "test")
        skipped_match.lifecycle = MatchLifecycle.SKIPPED

        context.terminated_matches = [replaced_match, skipped_match]

        cached_match = TextMatch("Cached", Path("f2.txt"), (0, 6), "test", "test")
        cached_match.lifecycle = MatchLifecycle.CACHED
        context.cached_matches = [cached_match]

        translate_match = TextMatch("To Translate", Path("f3.txt"), (0, 12), "test", "test")
        translate_match.lifecycle = MatchLifecycle.PENDING_TRANSLATION
        context.matches_to_translate = [translate_match]

        # Update all_matches to include all matches for the new logic to work
        context.all_matches = context.terminated_matches + context.cached_matches + context.matches_to_translate
        self.reporter.generate(context)
        report_content = mock_file().write.call_args[0][0]
        assert "### Replaced by Rule (1 items)" in report_content
        assert "### Skipped by Rule (1 items)" in report_content
        assert "### Found in Cache (1 items)" in report_content
        assert "### Would be Translated (1 items)" in report_content

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_build_report_with_no_matches_to_translate(self, mock_file: MagicMock) -> None:
        """4. Content: Correctly handles no new translations."""
        context = self._create_mock_context()
        context.matches_to_translate = []
        self.reporter.generate(context)
        report_content = mock_file().write.call_args[0][0]
        assert "## 🚀 Batch Processing Plan (Simulated)\n\nNo new translations required.\n" in report_content

    @patch("logging.Logger.exception")
    @patch("pathlib.Path.open", side_effect=OSError("Disk full"))
    def test_generate_handles_os_error(self, mock_path_open: MagicMock, mock_log_exception: MagicMock) -> None:
        """5. Error Handling: Logs an exception on file write failure."""
        _ = mock_path_open
        context = self._create_mock_context()
        self.reporter.generate(context)
        mock_log_exception.assert_called_once_with("Failed to write dry-run report to %s", ANY)

    def test_escape_markdown(self) -> None:
        """6. Utility: _escape_markdown correctly escapes special characters."""
        text_with_pipe = "Hello | World"
        text_with_newline = "Hello\nWorld"
        escaped_pipe = self.reporter._escape_markdown(text_with_pipe)  # noqa: SLF001
        escaped_newline = self.reporter._escape_markdown(text_with_newline)  # noqa: SLF001
        assert escaped_pipe == "Hello \\| World"
        assert escaped_newline == "Hello World"

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_same_language_skipped_not_in_translation_list(self, mock_file: MagicMock) -> None:
        """7. Bug Regression: Same language matches should not appear in 'Would be Translated' section."""
        context = self._create_mock_context()

        # Create a same-language match: SKIPPED lifecycle but in matches_to_translate
        same_lang_match = TextMatch(
            original_text="Same Language Text",
            source_file=Path("file1.txt"),
            span=(0, 18),
            task_name="test_task",
            extraction_rule="rule1",
        )
        same_lang_match.lifecycle = MatchLifecycle.SKIPPED
        same_lang_match.skip_reason = SKIP_SAME_LANGUAGE
        same_lang_match.translated_text = "Same Language Text"  # Same as original

        # Simulate the state after TranslationProcessor processes same language
        context.matches_to_translate = [same_lang_match]
        context.all_matches = [same_lang_match]

        self.reporter.generate(context)
        report_content = mock_file().write.call_args[0][0]

        # The match should appear in "Skipped by Rule", not "Would be Translated"
        assert "### Skipped by Rule (1 items)" in report_content
        assert "### Would be Translated (0 items)" in report_content or "No matches in this category" in report_content
        assert "Same Language Text" in report_content

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_same_language_batch_plan_shows_zero(self, mock_file: MagicMock) -> None:
        """8. Bug Regression: Batch plan should show zero translations needed for same language."""
        context = self._create_mock_context()

        # Create same-language matches
        same_lang_match = TextMatch(
            original_text="Test",
            source_file=Path("file1.txt"),
            span=(0, 4),
            task_name="test_task",
            extraction_rule="rule1",
        )
        same_lang_match.lifecycle = MatchLifecycle.SKIPPED
        same_lang_match.skip_reason = SKIP_SAME_LANGUAGE
        same_lang_match.translated_text = "Test"

        context.matches_to_translate = [same_lang_match]
        context.all_matches = [same_lang_match]

        self.reporter.generate(context)
        report_content = mock_file().write.call_args[0][0]

        # Batch plan should show "No new translations required"
        assert "## 🚀 Batch Processing Plan (Simulated)\n\nNo new translations required.\n" in report_content


class TestSummaryReporter(unittest.TestCase):
    """Test suite for the SummaryReporter."""

    def setUp(self) -> None:
        """Set up test data."""
        self.task = TranslationTask(
            name="summary_task",
            source_lang="en",
            target_lang="de",
            translator="mock",
            source=Source(include=["*.txt"]),
        )
        self.config = GlocalConfig(tasks=[self.task])
        self.reporter = SummaryReporter()

    @patch("logging.Logger.info")
    def test_generate_summary_logs_output(self, mock_log_info: MagicMock) -> None:
        """1. Logging: Generates a summary and logs it via the logger."""
        context = ExecutionContext(task=self.task, config=self.config)
        # Phase 4: Updated test data to use lifecycle states
        # A rule match must have processed_text != original_text to be counted as replaced
        rule_match = TextMatch("A", Path("f.txt"), (0, 1), "test", "test")
        rule_match.lifecycle = MatchLifecycle.REPLACED
        rule_match.processed_text = "A_replaced"  # Simulate rule replacement

        skipped_match = TextMatch("B", Path("f.txt"), (0, 1), "test", "test")
        skipped_match.lifecycle = MatchLifecycle.SKIPPED

        context.terminated_matches = [rule_match, skipped_match]

        cached_match = TextMatch("C", Path("f.txt"), (0, 1), "test", "test")
        cached_match.lifecycle = MatchLifecycle.CACHED
        context.cached_matches = [cached_match]

        translated_match = TextMatch("D", Path("f.txt"), (0, 1), "test", "test")
        translated_match.lifecycle = MatchLifecycle.TRANSLATED
        translated_match.translated_text = "d"
        translated_match.tokens_used = 10
        context.matches_to_translate = [translated_match]

        self.reporter.generate(context)
        calls = [
            call("--- Task Execution Summary for '%s' ---", "summary_task"),
            call("Total matches processed: %d", 4),
            call("  - Replaced by rule: %d", 1),
            call("  - Skipped by rule: %d", 1),
            call("  - From cache: %d", 1),
            call("  - Newly translated via API: %d", 1),
            call("Total tokens used for API translation: %d", 10),
            call("-------------------------------------------------"),
        ]
        mock_log_info.assert_has_calls(calls)

    @patch("logging.Logger.info")
    def test_generate_summary_no_tokens(self, mock_log_info: MagicMock) -> None:
        """2. Logging: Does not log token usage if zero tokens were used."""
        context = ExecutionContext(task=self.task, config=self.config)
        translated_match = TextMatch("D", Path("f.txt"), (0, 1), "test", "test")
        translated_match.lifecycle = MatchLifecycle.TRANSLATED
        translated_match.translated_text = "d"
        translated_match.tokens_used = 0
        context.matches_to_translate = [translated_match]
        self.reporter.generate(context)
        token_log_call = call("Total tokens used for API translation: %d", 0)
        assert token_log_call not in mock_log_info.call_args_list


if __name__ == "__main__":
    unittest.main()
