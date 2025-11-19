"""Tests for the processing pipeline and its components."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.match_state import MatchLifecycle
from glocaltext.models import ExecutionContext, TextMatch
from glocaltext.processing import (
    CacheProcessor,
    CacheUpdateProcessor,
    CaptureProcessor,
    TerminatingRuleProcessor,
    TranslationProcessor,
    WriteBackProcessor,
)
from glocaltext.processing.cache_utils import _get_task_cache_path
from glocaltext.processing.capture_processor import _exclude_files
from glocaltext.processing.writeback_processor import (
    _apply_translations_by_strategy,
    _get_output_path,
    _orchestrate_file_write,
    _write_modified_content,
)
from glocaltext.types import ActionRule, MatchRule, Output, Rule, Source, TranslationTask


class TestCaptureProcessor(unittest.TestCase):
    """Test suite for the CaptureProcessor."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["**/*.txt"], exclude=["**/ignore.txt"]),
            extraction_rules=[r'msgid "([^"]+)"'],
        )
        self.context = ExecutionContext(
            task=self.mock_task,
            config=self.mock_config,
            project_root=Path.cwd(),
        )

    @patch("glocaltext.paths.find_project_root")
    @patch("pathlib.Path.rglob")
    def test_find_files_with_include_and_exclude(self, mock_rglob: MagicMock, mock_find_root: MagicMock) -> None:
        """1. File Discovery: Correctly finds files based on include/exclude patterns."""
        base_path = Path("/project")
        mock_find_root.return_value = base_path
        mock_rglob.side_effect = [
            [
                base_path / "file1.txt",
                base_path / "subdir" / "file2.txt",
                base_path / "subdir" / "ignore.txt",
            ],
            [base_path / "subdir" / "ignore.txt"],
        ]
        processor = CaptureProcessor()
        processor.process(self.context)
        expected_files = {
            base_path / "file1.txt",
            base_path / "subdir" / "file2.txt",
        }
        assert set(self.context.files_to_process) == expected_files

    @patch("glocaltext.paths.find_project_root")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.read_text")
    def test_extract_matches_from_content(self, mock_read_text: MagicMock, mock_rglob: MagicMock, mock_find_root: MagicMock) -> None:
        """2. Text Extraction: Correctly extracts text based on extraction rules."""
        base_path = Path("/project")
        mock_find_root.return_value = base_path
        file_path = base_path / "file1.txt"
        mock_rglob.side_effect = [[file_path], []]
        mock_read_text.return_value = 'msgid "Hello"\nmsgid "World"'
        processor = CaptureProcessor()
        processor.process(self.context)
        expected_match_count = 2
        assert len(self.context.all_matches) == expected_match_count
        extracted_texts = {match.original_text for match in self.context.all_matches}
        assert extracted_texts == {"Hello", "World"}
        assert all(match.source_file == file_path for match in self.context.all_matches)

    @patch("glocaltext.paths.find_project_root")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.read_text", side_effect=OSError("Permission denied"))
    def test_process_handles_os_error(self, mock_read_text: MagicMock, mock_rglob: MagicMock, mock_find_root: MagicMock) -> None:
        """3. Error Handling: Handles OSError during file read."""
        base_path = Path("/project")
        mock_find_root.return_value = base_path
        file_path = base_path / "file1.txt"
        mock_rglob.side_effect = [[file_path], []]
        processor = CaptureProcessor()
        processor.process(self.context)
        assert len(self.context.all_matches) == 0
        mock_read_text.assert_called_with("utf-8")

    @patch("glocaltext.paths.find_project_root")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.read_text")
    def test_process_handles_invalid_regex(self, mock_read_text: MagicMock, mock_rglob: MagicMock, mock_find_root: MagicMock) -> None:
        """4. Error Handling: Handles invalid regex patterns gracefully."""
        self.mock_task.extraction_rules = ["[invalid-regex"]
        base_path = Path("/project")
        mock_find_root.return_value = base_path
        file_path = base_path / "file1.txt"
        mock_rglob.side_effect = [[file_path], []]
        mock_read_text.return_value = "some content"
        processor = CaptureProcessor()
        processor.process(self.context)
        assert len(self.context.all_matches) == 0


class TestTerminatingRuleProcessor(unittest.TestCase):
    """Test suite for the TerminatingRuleProcessor."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="test_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            rules=[],
        )
        self.base_context = ExecutionContext(
            task=self.mock_task,
            config=self.mock_config,
            project_root=Path.cwd(),
        )

    def test_skip_rule_terminates_match(self) -> None:
        """1. Skip Rule: A match is terminated if a 'skip' rule fully covers the text (Phase 2.3 behavior)."""
        # Pattern that fully matches the text - will be detected by full coverage detection
        self.mock_task.rules = [Rule(match=MatchRule(regex=r"^Skip this$"), action=ActionRule(action="skip"))]
        self.base_context.matches_to_translate = [
            TextMatch(original_text="Skip this", source_file=Path("f.txt"), span=(0, 9), task_name="test", extraction_rule="r"),
            TextMatch(original_text="Translate this", source_file=Path("f.txt"), span=(10, 24), task_name="test", extraction_rule="r"),
        ]
        processor = TerminatingRuleProcessor()
        processor.process(self.base_context)
        assert len(self.base_context.terminated_matches) == 1
        assert self.base_context.terminated_matches[0].original_text == "Skip this"
        # Phase 2.3: Full coverage detection takes priority and marks this as SKIPPED
        assert self.base_context.terminated_matches[0].lifecycle == MatchLifecycle.SKIPPED
        assert len(self.base_context.matches_to_translate) == 1
        assert self.base_context.matches_to_translate[0].original_text == "Translate this"

    def test_replace_to_empty_terminates_match(self) -> None:
        """
        2. Replace-to-Empty Rule: A match is terminated if a 'replace' rule fully covers the text.

        Phase 4.8 Architecture:
        - Replace rules execute FIRST, storing result in match.processed_text
        - match.original_text remains unchanged (for cache consistency)
        - Full coverage detection marks match as fully covered
        - match.translated_text is set to processed_text when fully covered
        """
        # Pattern that fully matches the text - will be detected by full coverage detection
        self.mock_task.rules = [Rule(match=MatchRule(regex=r"^Replace.*"), action=ActionRule(action="replace", value=""))]
        self.base_context.matches_to_translate = [
            TextMatch(original_text="Replace this to empty", source_file=Path("f.txt"), span=(0, 21), task_name="test", extraction_rule="r"),
            TextMatch(original_text="Keep this", source_file=Path("f.txt"), span=(22, 31), task_name="test", extraction_rule="r"),
        ]
        processor = TerminatingRuleProcessor()
        processor.process(self.base_context)
        assert len(self.base_context.terminated_matches) == 1

        # Phase 4.8: Verify the architecture behavior
        terminated = self.base_context.terminated_matches[0]
        assert terminated.original_text == "Replace this to empty"  # Unchanged for cache
        assert terminated.processed_text == ""  # Replace rule result
        assert terminated.lifecycle == MatchLifecycle.SKIPPED  # Fully covered by terminating rules

        assert len(self.base_context.matches_to_translate) == 1
        assert self.base_context.matches_to_translate[0].original_text == "Keep this"


class TestCacheProcessor(unittest.TestCase):
    """Test suite for the CacheProcessor."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="cache_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            incremental=True,
        )
        self.context = ExecutionContext(task=self.mock_task, config=self.mock_config, project_root=Path.cwd())
        self.processor = CacheProcessor()

    def test_non_incremental_skips_processing(self) -> None:
        """1. Cache Skip: Skips cache logic if incremental mode is off."""
        self.mock_task.incremental = False
        self.context.all_matches = [TextMatch("Hello", Path("f.txt"), (0, 5), "t", "r")]
        self.processor.process(self.context)
        assert self.context.matches_to_translate == self.context.all_matches
        assert len(self.context.cached_matches) == 0

    @patch("glocaltext.processing.cache_processors._get_task_cache_path")
    @patch("glocaltext.processing.cache_processors._load_cache")
    def test_partitioning_with_cache_hits_and_misses(self, mock_load_cache: MagicMock, mock_get_path: MagicMock) -> None:
        """2. Partitioning: Correctly separates matches based on cache hits."""
        self.context.is_incremental = True  # Enable incremental mode
        mock_get_path.return_value = Path("/fake_project/.ogos/glocaltext/caches/test_task.json")
        # sha256 hash of "" is e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        mock_load_cache.return_value = {"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": "Bonjour"}
        match_in_cache = TextMatch("", Path("f1.txt"), (0, 0), "t", "r")
        match_not_in_cache = TextMatch("World", Path("f2.txt"), (0, 5), "t", "r")
        self.context.all_matches = [match_in_cache, match_not_in_cache]
        self.processor.process(self.context)
        assert len(self.context.cached_matches) == 1
        assert self.context.cached_matches[0].translated_text == "Bonjour"
        assert len(self.context.matches_to_translate) == 1
        assert self.context.matches_to_translate[0].original_text == "World"

    @patch("glocaltext.paths.find_project_root", return_value=Path("/fake_project"))
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.open", new_callable=mock_open, read_data="corrupted json")
    def test_load_cache_handles_corrupted_file(self, mock_open_file: MagicMock, mock_exists: MagicMock, mock_find_root: MagicMock) -> None:
        """3. Error Handling: Handles corrupted or unreadable cache files."""
        _ = mock_open_file, mock_exists, mock_find_root
        self.context.all_matches = [TextMatch("Hello", Path("f.txt"), (0, 5), "t", "r")]
        processor = CacheProcessor()
        processor.process(self.context)
        assert len(self.context.cached_matches) == 0
        assert len(self.context.matches_to_translate) == 1
        assert self.context.matches_to_translate[0].original_text == "Hello"


class TestTranslationProcessor(unittest.TestCase):
    """Test suite for the TranslationProcessor."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        self.mock_task = TranslationTask(name="translate_task", source_lang="en", target_lang="fr", translator="mock", source=Source(include=["*.txt"]))
        self.context = ExecutionContext(task=self.mock_task, config=self.mock_config, project_root=Path.cwd())
        self.processor = TranslationProcessor()

    def test_skips_if_languages_are_the_same(self) -> None:
        """1. Skip: Skips API call if source and target languages are identical."""
        self.mock_task.target_lang = "en"
        self.context.matches_to_translate = [TextMatch("Hello", Path("f.txt"), (0, 5), "t", "r")]
        self.processor.process(self.context)
        assert len(self.context.matches_to_translate) == 1
        assert self.context.matches_to_translate[0].translated_text == "Hello"
        assert self.context.matches_to_translate[0].lifecycle == MatchLifecycle.SKIPPED

    def test_skips_in_dry_run_mode(self) -> None:
        """2. Skip: Skips API call in dry-run mode but applies pre-processing rules."""
        self.context.is_dry_run = True
        self.context.matches_to_translate = [TextMatch("Hello", Path("f.txt"), (0, 5), "t", "r")]
        self.processor.process(self.context)
        assert len(self.context.matches_to_translate) == 1
        # In dry-run mode, pre-processing rules are applied, so translated_text contains the processed text
        assert self.context.matches_to_translate[0].translated_text is not None
        assert self.context.matches_to_translate[0].lifecycle == MatchLifecycle.DRY_RUN_SIMULATED

    def test_discards_empty_matches(self) -> None:
        """3. Filtering: Discards empty or whitespace-only matches before translation."""
        self.context.matches_to_translate = [
            TextMatch("  ", Path("f.txt"), (0, 2), "t", "r"),
            TextMatch("Valid", Path("f.txt"), (3, 8), "t", "r"),
        ]
        self.processor.process(self.context)
        assert len(self.context.matches_to_translate) == 1
        assert self.context.matches_to_translate[0].original_text == "Valid"
        assert len(self.context.terminated_matches) == 1
        assert self.context.terminated_matches[0].lifecycle == MatchLifecycle.SKIPPED


class TestCacheUpdateProcessor(unittest.TestCase):
    """Test suite for the CacheUpdateProcessor."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="cache_update_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            incremental=True,
        )
        self.context = ExecutionContext(task=self.mock_task, config=self.mock_config, project_root=Path.cwd())
        self.processor = CacheUpdateProcessor()

    @patch("glocaltext.paths.find_project_root")
    def test_skips_in_dry_run_mode(self, mock_find_root: MagicMock) -> None:
        """1. Skip: Skips cache update in dry-run mode."""
        mock_find_root.return_value = Path("/fake_project")
        self.context.is_dry_run = True
        match = TextMatch("Hello", Path("f.txt"), (0, 5), "t", "r", translated_text="Bonjour")
        match.lifecycle = MatchLifecycle.TRANSLATED
        self.context.matches_to_translate = [match]
        with patch("glocaltext.processing.cache_utils._update_cache") as mock_update_cache:
            self.processor.process(self.context)
            mock_update_cache.assert_not_called()

    @patch("glocaltext.processing.cache_processors._get_task_cache_path")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_updates_cache_with_new_translations(self, mock_update_cache: MagicMock, mock_get_path: MagicMock) -> None:
        """2. Update: Updates the cache with new, API-translated items."""
        self.context.is_incremental = True  # Enable incremental mode
        mock_get_path.return_value = Path("/fake_project/.ogos/glocaltext/caches/test_task.json")
        match1 = TextMatch("Hello", Path("f.txt"), (0, 5), "t", "r", translated_text="Bonjour")
        match1.lifecycle = MatchLifecycle.TRANSLATED
        match2 = TextMatch("World", Path("f.txt"), (6, 11), "t", "r", translated_text="Monde")
        match2.lifecycle = MatchLifecycle.CACHED  # This one should be filtered out
        self.context.matches_to_translate = [match1, match2]
        self.processor.process(self.context)
        mock_update_cache.assert_called_once()

        called_args = mock_update_cache.call_args.args
        expected_arg_count = 3  # path, task_name, matches_to_cache
        assert len(called_args) == expected_arg_count
        matches_to_cache = called_args[2]

        expected_match_count = 1
        assert len(matches_to_cache) == expected_match_count
        assert matches_to_cache[0].original_text == "Hello"


class TestWriteBackProcessor(unittest.TestCase):
    """Test suite for the WriteBackProcessor."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="write_back_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            output=Output(in_place=True),
        )
        self.context = ExecutionContext(task=self.mock_task, config=self.mock_config, project_root=Path.cwd())
        self.processor = WriteBackProcessor()

    @patch("glocaltext.processing.writeback_processor._orchestrate_file_write")
    def test_skips_in_dry_run_mode(self, mock_orchestrate: MagicMock) -> None:
        """1. Skip: Skips file writing in dry-run mode."""
        self.context.is_dry_run = True
        match = TextMatch("H", Path("f.txt"), (0, 1), "t", "r")
        match.lifecycle = MatchLifecycle.TRANSLATED
        self.context.matches_to_translate = [match]
        self.processor.process(self.context)
        mock_orchestrate.assert_not_called()

    @patch("glocaltext.processing.writeback_processor._orchestrate_file_write")
    def test_groups_matches_and_writes_files(self, mock_orchestrate: MagicMock) -> None:
        """2. Write-back: Correctly groups matches by file and calls the writer."""
        file1 = Path("file1.txt")
        file2 = Path("file2.txt")
        match1 = TextMatch("A", file1, (0, 1), "t", "r")
        match1.lifecycle = MatchLifecycle.SKIPPED
        match2 = TextMatch("B", file2, (0, 1), "t", "r")
        match2.lifecycle = MatchLifecycle.CACHED
        match3 = TextMatch("C", file1, (2, 3), "t", "r")
        match3.lifecycle = MatchLifecycle.TRANSLATED
        self.context.terminated_matches = [match1]
        self.context.cached_matches = [match2]
        self.context.matches_to_translate = [match3]
        self.processor.process(self.context)

        expected_call_count = 2
        assert mock_orchestrate.call_count == expected_call_count

        # Check call for file1
        call1_args = next((c.args for c in mock_orchestrate.call_args_list if c.args[0] == file1), None)
        assert call1_args is not None, "Orchestrator was not called for file1.txt"
        matches_for_file1 = call1_args[1]
        expected_matches_for_file1 = 2
        assert len(matches_for_file1) == expected_matches_for_file1

        # Check call for file2
        call2_args = next((c.args for c in mock_orchestrate.call_args_list if c.args[0] == file2), None)
        assert call2_args is not None, "Orchestrator was not called for file2.txt"
        matches_for_file2 = call2_args[1]
        expected_matches_for_file2 = 1
        assert len(matches_for_file2) == expected_matches_for_file2


class TestProcessorHelpers(unittest.TestCase):
    """Test suite for helper functions in the processors module."""

    def setUp(self) -> None:
        """Set up common test data."""
        self.mock_task = TranslationTask(
            name="helper_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
        )

    @patch("glocaltext.processing.cache_utils.paths.get_cache_dir")
    @patch("glocaltext.processing.cache_utils.paths.find_project_root")
    def test_get_task_cache_path(self, mock_find_root: MagicMock, mock_get_cache_dir: MagicMock) -> None:
        """Helper: _get_task_cache_path correctly builds a cache path from a task's UUID."""
        mock_cache_dir = Path("/fake/cache/dir")
        mock_get_cache_dir.return_value = mock_cache_dir
        mock_find_root.return_value = Path("/fake/project")

        # Create a task with a known task_id
        task = TranslationTask(name="My Test Task", source_lang="en", target_lang="fr", translator="mock", source=Source(include=["*.txt"]), task_id="test-uuid-12345")

        result_path = _get_task_cache_path(task, Path.cwd())
        mock_get_cache_dir.assert_called_once()
        expected_filename = "test-uuid-12345.json"
        expected_path = mock_cache_dir / expected_filename
        assert result_path == expected_path

    def test_get_output_path(self) -> None:
        """Helper: _get_output_path correctly determines output file path."""
        file_path = Path("/project/src/file.md")
        self.mock_task.source_lang = "en"
        self.mock_task.target_lang = "fr"

        # 1. In-place
        self.mock_task.output = Output(in_place=True)
        path = _get_output_path(file_path, self.mock_task)
        assert path == file_path

        # 2. Output directory (implementation only uses file name)
        self.mock_task.output = Output(in_place=False, path="/out")
        path = _get_output_path(file_path, self.mock_task)
        assert path == Path("/out/file.md")

        # 3. Output with filename format
        self.mock_task.output = Output(in_place=False, path="/out", filename="{stem}.{target_lang}.{extension}")
        path = _get_output_path(file_path, self.mock_task)
        assert path == Path("/out/file.fr.md")

    def test_exclude_files_handles_exception(self) -> None:
        """Helper: _exclude_files handles exceptions during path resolution."""
        included = {Path("file1.txt")}
        self.mock_task.source.exclude = ["**/*"]  # Add exclude pattern
        with patch("pathlib.Path.rglob", side_effect=Exception("Resolution failed")):
            result = _exclude_files(included, self.mock_task, Path())
            assert result == included


class TestWriteBackStrategies(unittest.TestCase):
    """Test suite for the write-back strategies and helpers."""

    def setUp(self) -> None:
        """Set up common test data."""
        self.matches = [
            TextMatch("greeting", Path("f.json"), (0, 8), "t", "r", translated_text="Hello"),
            TextMatch("farewell", Path("f.json"), (9, 17), "t", "r", translated_text="Goodbye"),
        ]
        self.task = TranslationTask(name="wb_task", source_lang="en", target_lang="fr", translator="mock", source=Source(include=["*"]))

    def test_strategy_fallback_on_invalid_json(self) -> None:
        """Write Strategy: Falls back to text replacement for invalid JSON."""
        invalid_json = '{\n  "greeting": "Hello",\n  "farewell": "Goodbye"\n'
        result = _apply_translations_by_strategy(invalid_json, self.matches, Path("f.json"))
        assert "Hello" in result
        assert "Goodbye" in result

    def test_strategy_fallback_on_invalid_yaml(self) -> None:
        """Write Strategy: Falls back to text replacement for invalid YAML."""
        invalid_yaml = "greeting: Hello\n  farewell: Goodbye"
        result = _apply_translations_by_strategy(invalid_yaml, self.matches, Path("f.yml"))
        assert "Hello" in result
        assert "Goodbye" in result

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.unlink")
    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.is_file", return_value=True)
    def test_write_content_deletes_parent_if_file(self, mock_is_file: MagicMock, mock_mkdir: MagicMock, mock_unlink: MagicMock, mock_write: MagicMock) -> None:
        """Write Helper: _write_modified_content deletes parent if it's a file."""
        _ = mock_is_file
        output_path = Path("/a/b/c.txt")
        _write_modified_content(output_path, "content", None)
        mock_unlink.assert_called_once()
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_write.assert_called_once_with("content", "utf-8", newline=None)

    @patch("glocaltext.processing.writeback_processor._read_file_for_writing", side_effect=OSError("Cannot read"))
    @patch("logging.Logger.exception")
    def test_orchestrate_write_handles_os_error(self, mock_log: MagicMock, mock_read: MagicMock) -> None:
        """Write Helper: _orchestrate_file_write handles OSError during read."""
        _ = mock_read
        _orchestrate_file_write(Path("file.txt"), [], self.task)
        mock_log.assert_called_once_with("Could not read or write file %s", Path("file.txt"))


if __name__ == "__main__":
    unittest.main()
