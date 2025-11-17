"""Processor for applying terminating rules."""

import logging

from glocaltext.models import ExecutionContext
from glocaltext.translate import apply_terminating_rules

from .base import Processor

__all__ = ["TerminatingRuleProcessor"]

logger = logging.getLogger(__name__)


class TerminatingRuleProcessor(Processor):
    """Phase 2: Apply terminating rules (e.g., skip, replace) to filter matches."""

    def process(self, context: ExecutionContext) -> None:
        """Apply terminating rules and update context with remaining and terminated matches."""
        # This processor now runs *after* the CacheProcessor, so it only
        # needs to process the remaining matches.
        remaining_matches, terminated_matches = apply_terminating_rules(context.matches_to_translate, context.task)
        context.terminated_matches.extend(terminated_matches)
        context.matches_to_translate = remaining_matches
        logger.debug(
            "Task '%s': %d matches handled by terminating rules.",
            context.task.name,
            len(context.terminated_matches),
        )
