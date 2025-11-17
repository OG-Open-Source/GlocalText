"""Translation processor for API-based translation."""

import logging

from glocaltext.match_state import SKIP_EMPTY, SKIP_SAME_LANGUAGE, MatchLifecycle
from glocaltext.models import ExecutionContext, TextMatch
from glocaltext.translate import process_matches

from .base import Processor

__all__ = ["TranslationProcessor"]

logger = logging.getLogger(__name__)


class TranslationProcessor(Processor):
    """Phase 4: Translate matches that were not handled by rules or cache."""

    def process(self, context: ExecutionContext) -> None:
        """
        Orchestrate the translation workflow with clear separation of concerns.

        Flow:
        1. Filter empty/whitespace matches
        2. Check for same-language optimization
        3. Perform translation (or dry-run simulation)
        """
        valid_matches = self._filter_empty_matches(context)

        if self._should_skip_same_language(context):
            self._mark_same_language_skipped(context.matches_to_translate)
            return

        if not valid_matches:
            return

        self._perform_translation(context, valid_matches)

    def _filter_empty_matches(self, context: ExecutionContext) -> list[TextMatch]:
        """
        Filter out empty or whitespace-only matches before translation.

        Empty matches are marked as SKIPPED and added to terminated_matches.

        Returns:
            List of valid (non-empty) matches

        """
        valid_matches = []
        empty_matches = []

        for match in context.matches_to_translate:
            if match.original_text and match.original_text.strip():
                valid_matches.append(match)
            else:
                empty_matches.append(match)

        if empty_matches:
            logger.info("Discarding %d empty or whitespace-only matches before translation.", len(empty_matches))
            for match in empty_matches:
                match.lifecycle = MatchLifecycle.SKIPPED
                match.skip_reason = SKIP_EMPTY
            context.terminated_matches.extend(empty_matches)

        # Update context with filtered matches
        context.matches_to_translate = valid_matches
        return valid_matches

    def _should_skip_same_language(self, context: ExecutionContext) -> bool:
        """Check if source and target languages are identical."""
        return context.task.source_lang == context.task.target_lang

    def _mark_same_language_skipped(self, matches: list[TextMatch]) -> None:
        """
        Mark all matches as skipped due to same-language optimization.

        When source and target languages are identical, no translation is needed.
        The original text is used as the "translation".
        """
        logger.info(
            "Source and target languages are the same. Skipping API translation for %d matches.",
            len(matches),
        )
        for match in matches:
            match.translated_text = match.original_text
            match.lifecycle = MatchLifecycle.SKIPPED
            match.skip_reason = SKIP_SAME_LANGUAGE

    def _perform_translation(self, context: ExecutionContext, valid_matches: list[TextMatch]) -> None:
        """
        Execute the actual translation (or dry-run simulation).

        In dry-run mode, applies pre-processing rules but skips API calls.
        """
        if context.is_dry_run:
            logger.debug("[DRY RUN] Processing matches with rules but skipping API translation.")
        else:
            logger.info("Processing %d matches for API translation.", len(valid_matches))

        process_matches(
            matches=valid_matches,
            task=context.task,
            config=context.config,
            debug=context.is_debug,
            dry_run=context.is_dry_run,
        )
