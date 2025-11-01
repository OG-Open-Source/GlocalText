"""A reporter for generating concise execution summaries."""

import logging

from glocaltext.models import ExecutionContext

logger = logging.getLogger(__name__)


class SummaryReporter:
    """Generates a concise summary of a translation task execution and logs it."""

    def generate(self, context: ExecutionContext) -> None:
        """Log a summary of the execution to the console."""
        logger.info("--- Task Execution Summary for '%s' ---", context.task.name)

        total_processed = len(context.terminated_matches) + len(context.cached_matches) + len(context.matches_to_translate)
        logger.info("Total matches processed: %d", total_processed)

        rule_matches = [m for m in context.terminated_matches if m.provider == "rule"]
        skipped_matches = [m for m in context.terminated_matches if m.provider == "skipped"]

        logger.info("  - Replaced by rule: %d", len(rule_matches))
        logger.info("  - Skipped by rule: %d", len(skipped_matches))
        logger.info("  - From cache: %d", len(context.cached_matches))

        api_translated = [m for m in context.matches_to_translate if m.translated_text is not None and m.provider not in ("cached", "rule", "skipped")]
        logger.info("  - Newly translated via API: %d", len(api_translated))

        total_tokens = sum(m.tokens_used for m in api_translated if m.tokens_used is not None)
        if total_tokens > 0:
            logger.info("Total tokens used for API translation: %d", total_tokens)

        logger.info("-------------------------------------------------")
