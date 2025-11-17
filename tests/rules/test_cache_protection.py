"""Tests for cache protection mechanisms to prevent overwriting manual edits."""

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from glocaltext.config import GlocalConfig
from glocaltext.match_state import MatchLifecycle
from glocaltext.models import ExecutionContext
from glocaltext.processing import CacheProcessor, CacheUpdateProcessor
from glocaltext.processing.cache_utils import _update_cache, calculate_checksum
from glocaltext.types import Source, TextMatch, TranslationTask


class TestCacheProtection(unittest.TestCase):
    """Test suite for cache protection against overwriting manual edits."""

    def setUp(self) -> None:
        """Set up a mock execution context for the tests."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="cache_protection_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            incremental=True,
            task_id="test-task-id-12345",
        )
        self.context = ExecutionContext(task=self.mock_task, config=self.mock_config)

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_cached_matches_not_overwritten_in_incremental_mode(
        self,
        mock_update_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that manually edited cache entries are not overwritten.

        Scenario:
        1. User manually edited a cache entry
        2. System runs in incremental mode
        3. Match hits cache (lifecycle=MatchLifecycle.CACHED)
        4. CacheUpdateProcessor should NOT write this match back to cache
        """
        mock_find_root.return_value = Path("/fake_project")

        # Setup: Original text with its checksum
        original_text = "Test text"
        checksum = calculate_checksum(original_text)

        # User manually edited the cache with custom translation
        manual_translation = "User's custom translation with    extra spaces"
        mock_load_cache.return_value = {checksum: manual_translation}

        # Create a match that will hit cache
        match = TextMatch(
            original_text=original_text,
            source_file=Path("f.txt"),
            span=(0, 9),
            task_name="test",
            extraction_rule="r",
        )
        self.context.all_matches = [match]
        self.context.is_incremental = True  # Enable incremental mode

        # Run CacheProcessor - this should set lifecycle=MatchLifecycle.CACHED
        cache_processor = CacheProcessor()
        cache_processor.process(self.context)

        # Verify match was cached
        assert len(self.context.cached_matches) == 1
        assert self.context.cached_matches[0].lifecycle == MatchLifecycle.CACHED
        assert self.context.cached_matches[0].translated_text == manual_translation

        # Run CacheUpdateProcessor
        update_processor = CacheUpdateProcessor()
        update_processor.process(self.context)

        # Verify: Cache update should NOT be called because the match came from cache
        # The match is in cached_matches, not in matches_to_translate
        mock_update_cache.assert_not_called()

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_cache_protection_filters_provider_cached(
        self,
        mock_update_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that matches with lifecycle=MatchLifecycle.CACHED are filtered out from cache updates.

        Even if a cached match somehow ends up in matches_to_translate,
        it should be filtered by the lifecycle check.
        """
        mock_find_root.return_value = Path("/fake_project")
        mock_load_cache.return_value = {}
        self.context.is_incremental = True  # Enable incremental mode

        # Simulate a match that has lifecycle=MatchLifecycle.CACHED but is in matches_to_translate
        # (This shouldn't normally happen, but we test the safety net)
        cached_match = TextMatch(
            original_text="Cached text",
            source_file=Path("f.txt"),
            span=(0, 11),
            task_name="test",
            extraction_rule="r",
            translated_text="Translated from cache",
        )
        cached_match.lifecycle = MatchLifecycle.CACHED

        # New API-translated match (should be cached)
        new_match = TextMatch(
            original_text="New text",
            source_file=Path("f.txt"),
            span=(12, 20),
            task_name="test",
            extraction_rule="r",
            translated_text="New translation",
        )
        new_match.lifecycle = MatchLifecycle.TRANSLATED

        self.context.matches_to_translate = [cached_match, new_match]

        # Run CacheUpdateProcessor
        update_processor = CacheUpdateProcessor()
        update_processor.process(self.context)

        # Verify: Only the new match should be passed to _update_cache
        mock_update_cache.assert_called_once()
        called_matches = mock_update_cache.call_args.args[2]
        assert len(called_matches) == 1
        assert called_matches[0].original_text == "New text"
        assert called_matches[0].lifecycle == MatchLifecycle.TRANSLATED

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_cache_protection_filters_existing_checksums(
        self,
        mock_update_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that matches whose checksums already exist in cache are filtered out.

        This is the extra protection layer: even if a match passes the lifecycle filter,
        if its checksum is already in the cache, it should not overwrite the existing entry.
        """
        mock_find_root.return_value = Path("/fake_project")
        self.context.is_incremental = True  # Enable incremental mode

        # Setup: Existing cache with a manual edit
        existing_text = "Existing text"
        existing_checksum = calculate_checksum(existing_text)
        manual_edit = "Manually edited translation"
        mock_load_cache.return_value = {existing_checksum: manual_edit}

        # Simulate a scenario where a match with existing checksum is somehow
        # marked with a non-cached lifecycle (edge case / bug scenario)
        suspicious_match = TextMatch(
            original_text=existing_text,
            source_file=Path("f.txt"),
            span=(0, 13),
            task_name="test",
            extraction_rule="r",
            translated_text="Different translation",
        )
        suspicious_match.lifecycle = MatchLifecycle.TRANSLATED  # Lifecycle is not CACHED

        # A genuinely new match
        new_match = TextMatch(
            original_text="Brand new text",
            source_file=Path("f.txt"),
            span=(14, 28),
            task_name="test",
            extraction_rule="r",
            translated_text="Brand new translation",
        )
        new_match.lifecycle = MatchLifecycle.TRANSLATED

        self.context.matches_to_translate = [suspicious_match, new_match]

        # Run CacheUpdateProcessor
        update_processor = CacheUpdateProcessor()
        update_processor.process(self.context)

        # Verify: Only the genuinely new match should be passed to _update_cache
        mock_update_cache.assert_called_once()
        called_matches = mock_update_cache.call_args.args[2]
        assert len(called_matches) == 1
        assert called_matches[0].original_text == "Brand new text"

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_cache_protection_filters_fully_covered_provider(
        self,
        mock_update_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that matches with lifecycle=MatchLifecycle.SKIPPED are filtered out.

        The SKIPPED lifecycle is used for matches that are completely
        covered by terminating rules and should not be written to cache.
        """
        mock_find_root.return_value = Path("/fake_project")
        mock_load_cache.return_value = {}
        self.context.is_incremental = True  # Enable incremental mode

        # Match marked as SKIPPED
        covered_match = TextMatch(
            original_text="Fully covered text",
            source_file=Path("f.txt"),
            span=(0, 18),
            task_name="test",
            extraction_rule="r",
            translated_text="Covered translation",
        )
        covered_match.lifecycle = MatchLifecycle.SKIPPED

        # Normal API-translated match
        api_match = TextMatch(
            original_text="API text",
            source_file=Path("f.txt"),
            span=(19, 27),
            task_name="test",
            extraction_rule="r",
            translated_text="API translation",
        )
        api_match.lifecycle = MatchLifecycle.TRANSLATED

        self.context.matches_to_translate = [covered_match, api_match]

        # Run CacheUpdateProcessor
        update_processor = CacheUpdateProcessor()
        update_processor.process(self.context)

        # Verify: Only the API match should be cached
        mock_update_cache.assert_called_once()
        called_matches = mock_update_cache.call_args.args[2]
        assert len(called_matches) == 1
        assert called_matches[0].original_text == "API text"

    @patch("glocaltext.paths.find_project_root")
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.open")
    @patch("pathlib.Path.mkdir")
    def test_cache_overwrite_warning_logged(
        self,
        mock_mkdir: MagicMock,
        mock_open: MagicMock,
        mock_exists: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that a warning is logged when a cache entry is about to be overwritten.

        This test verifies the diagnostic logging in _update_cache.
        """
        _ = mock_mkdir, mock_exists
        mock_find_root.return_value = Path("/fake_project")

        # Setup: Existing cache
        existing_checksum = calculate_checksum("Existing")
        existing_cache = {"test-task-id-12345": {existing_checksum: "Old translation"}}

        # Mock file operations
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(existing_cache).encode("utf-8")
        mock_open.return_value = mock_file

        # Match that will overwrite existing cache
        match = TextMatch(
            original_text="Existing",
            source_file=Path("f.txt"),
            span=(0, 8),
            task_name="test",
            extraction_rule="r",
            translated_text="New translation",
        )
        match.lifecycle = MatchLifecycle.TRANSLATED

        # Import to capture logs

        with self.assertLogs("glocaltext.processing.cache_utils", level="WARNING") as log_capture:
            cache_path = Path("/fake/cache.json")
            _update_cache(cache_path, "test-task-id-12345", [match])

            # Verify warning was logged
            warning_found = any("[CACHE OVERWRITE]" in message and existing_checksum[:16] in message for message in log_capture.output)
            assert warning_found, "Expected [CACHE OVERWRITE] warning was not logged"


if __name__ == "__main__":
    unittest.main()
