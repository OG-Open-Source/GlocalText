import csv
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .config import GlocalConfig
from .models import TextMatch


def _calculate_metrics(all_matches: List[TextMatch]) -> Dict:
    """
    Calculate various metrics from the list of all text matches.

    Args:
        all_matches: A list of TextMatch objects from all tasks.

    Returns:
        A dictionary containing key metrics about the translation process.
    """
    total_matches = len(all_matches)
    unique_texts = {m.original_text for m in all_matches}
    processed_files = {m.source_file for m in all_matches}
    translations_applied = sum(1 for m in all_matches if m.translated_text is not None and m.translated_text != m.original_text)

    provider_breakdown: Dict[str, Dict[str, int]] = {}
    extraction_rule_breakdown: Dict[str, int] = {}
    total_tokens = 0
    for match in all_matches:
        provider = match.provider or "unknown"
        provider_breakdown.setdefault(provider, {"count": 0, "tokens": 0})
        provider_breakdown[provider]["count"] += 1
        total_tokens += match.tokens_used or 0
        provider_breakdown[provider]["tokens"] += match.tokens_used or 0
        if hasattr(match, "extraction_rule") and match.extraction_rule:
            extraction_rule_breakdown[match.extraction_rule] = extraction_rule_breakdown.get(match.extraction_rule, 0) + 1

    return {
        "total_matches": total_matches,
        "unique_texts": len(unique_texts),
        "processed_files": len(processed_files),
        "translations_applied": translations_applied,
        "provider_breakdown": provider_breakdown,
        "extraction_rule_breakdown": extraction_rule_breakdown,
        "total_tokens": total_tokens,
    }


def _log_summary_to_console(metrics: Dict, total_run_time: float):
    """
    Log the summary report to the console.

    Args:
        metrics: A dictionary of calculated metrics.
        total_run_time: The total execution time of all tasks.
    """
    logging.info("\n" + "=" * 40)
    logging.info(" GlocalText - Translation Summary")
    logging.info("=" * 40)
    logging.info(f"- Total Run Time: {total_run_time:.2f} seconds")
    logging.info(f"- Total Files Processed: {metrics['processed_files']}")
    logging.info(f"- Total Matches Captured: {metrics['total_matches']}")
    logging.info(f"- Unique Texts Processed: {metrics['unique_texts']}")
    logging.info(f"- Translations Applied: {metrics['translations_applied']} ({metrics['total_matches'] - metrics['translations_applied']} skipped)")

    logging.info("\n--- Provider Breakdown ---")
    for provider, data in metrics["provider_breakdown"].items():
        token_str = f" (Tokens: {data['tokens']})" if data["tokens"] > 0 else ""
        logging.info(f"- {provider.title()} Translations: {data['count']}{token_str}")

    if metrics["total_tokens"] > 0:
        logging.info(f"- Total Tokens Consumed: {metrics['total_tokens']}")

    if metrics.get("extraction_rule_breakdown"):
        logging.info("\n--- Extraction Rule Breakdown ---")
        # Sort for consistent output
        sorted_rules = sorted(metrics["extraction_rule_breakdown"].items(), key=lambda item: item[1], reverse=True)
        for rule, count in sorted_rules:
            logging.info(f"- {count} matches from rule: '{rule}'")


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


def _export_summary_to_csv(all_matches: List[TextMatch], config: GlocalConfig, filepath: Path):
    """
    Export the detailed match data to a CSV file.

    Args:
        all_matches: A list of all TextMatch objects.
        config: The application's configuration object.
        filepath: The path to the output CSV file.
    """
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "source_file",
                    "source_language",
                    "target_language",
                    "original_text",
                    "translated_text",
                    "provider",
                    "tokens_used",
                    "extraction_rule",
                ]
            )
            task_lookup = {t.name: t for t in config.tasks}
            for match in all_matches:
                task = task_lookup.get(match.task_name)
                writer.writerow(
                    [
                        str(match.source_file),
                        task.source_lang if task else "N/A",
                        task.target_lang if task else "N/A",
                        match.original_text,
                        match.translated_text,
                        match.provider,
                        match.tokens_used or 0,
                        getattr(match, "extraction_rule", "N/A"),
                    ]
                )
        logging.info("\n--- Report ---")
        logging.info(f"- CSV report exported to: {filepath}")
    except OSError as e:
        logging.error(f"Failed to write CSV report: {e}")


def generate_summary_report(
    all_matches: List[TextMatch],
    start_time: float,
    config: GlocalConfig,
    export_dir_override: Path | None = None,
):
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

    logging.info("=" * 40)
