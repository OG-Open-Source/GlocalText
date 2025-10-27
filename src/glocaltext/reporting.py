"""Handles the generation of summary reports and CSV exports."""

import csv
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import GlocalConfig
from .models import TextMatch

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
        # Provider breakdown
        provider = match.provider or "unknown"
        provider_breakdown[provider]["count"] += 1
        tokens_used = match.tokens_used or 0
        total_tokens += tokens_used
        provider_breakdown[provider]["tokens"] += tokens_used

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
    logger.info("\n%s", "=" * 40)
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

    logger.info("\n--- Provider Breakdown ---")
    for provider, data in metrics["provider_breakdown"].items():
        token_str = f" (Tokens: {data['tokens']})" if data["tokens"] > 0 else ""
        logger.info("- %s Translations: %s%s", provider.title(), data["count"], token_str)

    if metrics["total_tokens"] > 0:
        logger.info("- Total Tokens Consumed: %s", metrics["total_tokens"])

    if metrics.get("extraction_rule_breakdown"):
        logger.info("\n--- Extraction Rule Breakdown ---")
        # Sort for consistent output
        sorted_rules = sorted(
            metrics["extraction_rule_breakdown"].items(),
            key=lambda item: item[1],
            reverse=True,
        )
        for rule, count in sorted_rules:
            logger.info("- %s matches from rule: '%s'", count, rule)


def _get_report_filepath(start_time: float, end_time: float, export_dir: Path) -> Path:
    """
    Generate a timestamped filepath for the CSV report.

    The filename is created using the UTC start and end times of the process
    to ensure uniqueness and chronological order.

    Args:
        start_time: The POSIX timestamp of the start time.
        end_time: The POSIX timestamp of the end time.
        export_dir: The directory where the report will be saved.

    Returns:
        A Path object representing the full filepath for the report.

    """
    start_ts = datetime.fromtimestamp(start_time, tz=timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    end_ts = datetime.fromtimestamp(end_time, tz=timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    return export_dir / f"{start_ts}---{end_ts}.csv"


def _export_summary_to_csv(all_matches: list[TextMatch], config: GlocalConfig, filepath: Path) -> None:
    """
    Export the detailed match data to a CSV file.

    This function opens a CSV file, writes the header, and then iterates through
    all matches to write the data row by row.

    Args:
        all_matches: A list of all TextMatch objects.
        config: The application's configuration object.
        filepath: The path to the output CSV file.

    """
    task_lookup = {t.name: t for t in config.tasks}
    try:
        with filepath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_CSV_HEADER)
            for match in all_matches:
                task = task_lookup.get(match.task_name)
                row = [
                    str(match.source_file),
                    task.source_lang if task else "N/A",
                    task.target_lang if task else "N/A",
                    match.original_text,
                    match.translated_text,
                    match.provider,
                    match.tokens_used or 0,
                    getattr(match, "extraction_rule", "N/A"),
                ]
                writer.writerow(row)
        logger.info("\n--- Report ---")
        logger.info("- CSV report exported to: %s", filepath)
    except OSError:
        logger.exception("Failed to write CSV report")


def generate_summary_report(
    all_matches: list[TextMatch],
    start_time: float,
    config: GlocalConfig,
    export_dir_override: Path | None = None,
) -> None:
    """
    Generate and output a summary report to the console and optionally to a CSV file.

    This is the main function for the reporting module. It orchestrates the
    calculation of metrics, console logging, and CSV export.

    Args:
        all_matches: A list of all TextMatch objects from the translation tasks.
        start_time: The POSIX timestamp when the process started.
        config: The application's configuration object.
        export_dir_override: An optional path to override the export directory
            defined in the configuration.

    """
    end_time = time.time()
    total_run_time = end_time - start_time
    metrics = _calculate_metrics(all_matches)
    _log_summary_to_console(metrics, total_run_time)

    export_dir = export_dir_override or (Path(config.report_options.export_dir) if config.report_options.export_dir else None)

    if config.report_options.export_csv and export_dir:
        export_dir.mkdir(parents=True, exist_ok=True)
        filepath = _get_report_filepath(start_time, end_time, export_dir)
        _export_summary_to_csv(all_matches, config, filepath)

    logger.info("=" * 40)
