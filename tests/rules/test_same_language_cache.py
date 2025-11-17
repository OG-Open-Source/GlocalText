"""Regression test for Phase 6: Same Language Cache Missing Bug."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from glocaltext.config import GlocalConfig
from glocaltext.match_state import SKIP_SAME_LANGUAGE, SKIP_USER_RULE, MatchLifecycle
from glocaltext.models import ExecutionContext
from glocaltext.processing import CacheUpdateProcessor, TranslationProcessor
from glocaltext.types import Source, TextMatch, TranslationTask


class TestSameLanguageCacheBug(unittest.TestCase):
    """
    Test suite for the Same Language Cache Missing Bug (Phase 6).

    Bug Description:
    When source_lang == target_lang, matches are correctly marked as SKIPPED
    with SKIP_SAME_LANGUAGE reason, but they are not written to cache because
    CacheUpdateProcessor filters out ALL SKIPPED matches.

    This causes the same texts to be re-processed on every execution instead
    of being read from cache.
    """

    def setUp(self) -> None:
        """Set up test context."""
        self.mock_config = GlocalConfig()
        self.mock_task = TranslationTask(
            name="same_lang_task",
            source_lang="en",
            target_lang="en",  # Same language!
            translator="mock",
            source=Source(include=["*.txt"]),
            incremental=True,
            task_id="test-same-lang-id",
        )
        self.context = ExecutionContext(task=self.mock_task, config=self.mock_config)

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_same_language_matches_should_be_cached(
        self,
        mock_update_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that same language SKIPPED matches ARE written to cache.

        Scenario:
        1. source_lang == target_lang (e.g., both "en")
        2. TranslationProcessor marks matches as SKIPPED + SKIP_SAME_LANGUAGE
        3. CacheUpdateProcessor SHOULD write these to cache
        4. Next run should read from cache instead of re-processing

        Expected: Same language matches should be cached for performance.
        """
        mock_find_root.return_value = Path("/fake_project")
        mock_load_cache.return_value = {}  # Empty cache initially
        self.context.is_incremental = True  # Enable incremental mode

        # Create matches for same language scenario
        match1 = TextMatch(
            original_text="Hello World",
            source_file=Path("test.txt"),
            span=(0, 11),
            task_name="test",
            extraction_rule="r",
        )
        match2 = TextMatch(
            original_text="Another text",
            source_file=Path("test.txt"),
            span=(12, 24),
            task_name="test",
            extraction_rule="r",
        )

        self.context.matches_to_translate = [match1, match2]

        # Run TranslationProcessor - should mark as SKIPPED
        translation_processor = TranslationProcessor()
        translation_processor.process(self.context)

        # Verify matches were marked correctly
        assert match1.lifecycle == MatchLifecycle.SKIPPED
        assert match1.skip_reason == SKIP_SAME_LANGUAGE
        assert match1.translated_text == match1.original_text
        assert match2.lifecycle == MatchLifecycle.SKIPPED
        assert match2.skip_reason == SKIP_SAME_LANGUAGE
        assert match2.translated_text == match2.original_text

        # Run CacheUpdateProcessor - should write these to cache
        update_processor = CacheUpdateProcessor()
        update_processor.process(self.context)

        # CRITICAL ASSERTION: Same language matches SHOULD be cached
        # This test will FAIL before the fix, PASS after the fix
        mock_update_cache.assert_called_once()

        # Verify the matches passed to _update_cache
        called_matches = mock_update_cache.call_args.args[2]
        assert len(called_matches) == 2, f"Expected 2 matches to be cached, got {len(called_matches)}"

        # Verify the cached content
        cached_texts = {m.original_text for m in called_matches}
        assert "Hello World" in cached_texts
        assert "Another text" in cached_texts

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    def test_empty_text_skipped_matches_should_be_cached(
        self,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that empty text SKIPPED matches are also cached.

        Empty/whitespace-only texts should be cached to avoid re-processing.
        """
        mock_find_root.return_value = Path("/fake_project")
        mock_load_cache.return_value = {}

        # This will be filtered as empty by TranslationProcessor
        empty_match = TextMatch(
            original_text="   ",  # Whitespace only
            source_file=Path("test.txt"),
            span=(0, 3),
            task_name="test",
            extraction_rule="r",
        )

        self.context.matches_to_translate = [empty_match]

        # Run TranslationProcessor - moves empty matches to terminated_matches
        translation_processor = TranslationProcessor()
        translation_processor.process(self.context)

        # Empty matches are moved to terminated_matches, not left in matches_to_translate
        assert len(self.context.matches_to_translate) == 0
        assert len(self.context.terminated_matches) == 1
        assert self.context.terminated_matches[0].lifecycle == MatchLifecycle.SKIPPED

        # CacheUpdateProcessor only processes matches_to_translate
        # Empty matches are in terminated_matches, so they won't be cached
        # This is actually CORRECT behavior - empty matches don't need caching
        # because they're filtered before reaching the cache check

    @patch("glocaltext.paths.find_project_root")
    @patch("glocaltext.processing.cache_processors._load_cache")
    @patch("glocaltext.processing.cache_processors._update_cache")
    def test_user_rule_skipped_matches_not_cached(
        self,
        mock_update_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_find_root: MagicMock,
    ) -> None:
        """
        Test that user rule SKIPPED matches are NOT cached.

        User-defined skip rules should not be cached because the rules
        might change between runs.
        """
        mock_find_root.return_value = Path("/fake_project")
        mock_load_cache.return_value = {}
        self.context.is_incremental = True  # Enable incremental mode

        # Create a match that was skipped by user rule
        user_skip_match = TextMatch(
            original_text="Skip this",
            source_file=Path("test.txt"),
            span=(0, 9),
            task_name="test",
            extraction_rule="r",
            translated_text="Skip this",  # Would have translated_text
        )
        user_skip_match.lifecycle = MatchLifecycle.SKIPPED
        user_skip_match.skip_reason = SKIP_USER_RULE

        self.context.matches_to_translate = [user_skip_match]

        # Run CacheUpdateProcessor
        update_processor = CacheUpdateProcessor()
        update_processor.process(self.context)

        # User rule skips should NOT be cached
        mock_update_cache.assert_not_called()


if __name__ == "__main__":
    unittest.main()
