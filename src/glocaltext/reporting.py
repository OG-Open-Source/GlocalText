"""Handles the generation of summary reports and CSV exports."""

import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

from .models import TextMatch

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_CSV_HEADER = [
    "source_file",
    "source_language",
    "target_language",
    "original_text",
    "translated_text",
    "provider",
    "tokens_used",
    "extraction_rule",
]


def _calculate_metrics(all_matches: list[TextMatch]) -> dict[str, Any]:
    """
    Calculate various metrics from the list of all text matches in a single pass.

    Args:
        all_matches: A list of TextMatch objects from all tasks.

    Returns:
        A dictionary containing key metrics about the translation process.

    """
    provider_breakdown: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "tokens": 0})
    extraction_rule_breakdown: defaultdict[str, int] = defaultdict(int)
    total_tokens = 0
    translations_applied = 0
    processed_files: set[Path] = set()
    unique_texts: set[str] = set()

    for match in all_matches:
        # Lifecycle state breakdown
        lifecycle_key = match.lifecycle.value if match.lifecycle else "unknown"
        provider_breakdown[lifecycle_key]["count"] += 1
        tokens_used = match.tokens_used or 0
        total_tokens += tokens_used
        provider_breakdown[lifecycle_key]["tokens"] += tokens_used

        # Extraction rule breakdown
        if hasattr(match, "extraction_rule") and match.extraction_rule:
            extraction_rule_breakdown[match.extraction_rule] += 1

        # Basic stats
        if match.translated_text is not None and match.translated_text != match.original_text:
            translations_applied += 1
        processed_files.add(match.source_file)
        unique_texts.add(match.original_text)

    return {
        "total_matches": len(all_matches),
        "unique_texts": len(unique_texts),
        "processed_files": len(processed_files),
        "translations_applied": translations_applied,
        "provider_breakdown": dict(provider_breakdown),
        "extraction_rule_breakdown": dict(extraction_rule_breakdown),
        "total_tokens": total_tokens,
    }


def _log_summary_to_console(metrics: dict, total_run_time: float) -> None:
    """
    Log the summary report to the console.

    Args:
        metrics: A dictionary of calculated metrics.
        total_run_time: The total execution time of all tasks.

    """
    logger.info("%s", "=" * 40)
    logger.info(" GlocalText - Translation Summary")
    logger.info("=" * 40)
    logger.info("- Total Run Time: %.2f seconds", total_run_time)
    logger.info("- Total Files Processed: %s", metrics["processed_files"])
    logger.info("- Total Matches Captured: %s", metrics["total_matches"])
    logger.info("- Unique Texts Processed: %s", metrics["unique_texts"])
    logger.info(
        "- Translations Applied: %s (%s skipped)",
        metrics["translations_applied"],
        metrics["total_matches"] - metrics["translations_applied"],
    )

    logger.info("--- Provider Breakdown ---")
    for provider, data in metrics["provider_breakdown"].items():
        token_str = f" (Tokens: {data['tokens']})" if data["tokens"] > 0 else ""
        logger.info("- %s Translations: %s%s", provider.title(), data["count"], token_str)

    if metrics["total_tokens"] > 0:
        logger.info("- Total Tokens Consumed: %s", metrics["total_tokens"])

    if metrics.get("extraction_rule_breakdown"):
        logger.info("--- Extraction Rule Breakdown ---")
        # Sort for consistent output
        sorted_rules = sorted(
            metrics["extraction_rule_breakdown"].items(),
            key=lambda item: item[1],
            reverse=True,
        )
        for rule, count in sorted_rules:
            logger.info("- %s matches from rule: '%s'", count, rule)
