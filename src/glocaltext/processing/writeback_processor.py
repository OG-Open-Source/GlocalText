"""File writeback processor with strategy-based serialization."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from glocaltext.models import ExecutionContext, TextMatch
from glocaltext.types import TranslationTask

from .base import Processor

__all__ = [
    "WRITER_STRATEGIES",
    "StructuredDataStrategy",
    "WriteBackProcessor",
    "_apply_translations_by_strategy",
    "_apply_translations_to_content",
    "_apply_translations_to_json_structured",
    "_apply_translations_to_structured_data",
    "_apply_translations_to_yaml_structured",
    "_detect_newline",
    "_get_output_path",
    "_group_matches_by_file",
    "_orchestrate_file_write",
    "_read_file_for_writing",
    "_write_modified_content",
]

logger = logging.getLogger(__name__)


def _get_output_path(file_path: Path, task: TranslationTask) -> Path | None:
    """Calculate the output path for a given source file."""
    task_output = task.output
    if task_output.in_place:
        return file_path
    if not task_output.path:
        return None
    output_dir = Path(task_output.path)
    if task_output.filename:
        new_name = task_output.filename.format(
            stem=file_path.stem,
            source_lang=task.source_lang,
            target_lang=task.target_lang,
            extension=file_path.suffix.lstrip("."),
        )
        return output_dir / new_name
    return output_dir / file_path.name


def _write_modified_content(output_path: Path, content: str, newline: str | None) -> None:
    """Write content to the specified output path."""
    if output_path.parent.is_file():
        logger.warning(
            "Output directory path %s exists as a file. Deleting it to create directory.",
            output_path.parent,
        )
        output_path.parent.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, "utf-8", newline=newline)
    logger.info("Successfully wrote modified content to %s", output_path)


def _group_matches_by_file(matches: list[TextMatch]) -> dict[Path, list[TextMatch]]:
    """Group matches by their source file for write-back."""
    grouped_by_file: dict[Path, list[TextMatch]] = {}
    for match in matches:
        # A match should be written back if it has been processed (any lifecycle state except CAPTURED).
        # Group all matches for write-back
        grouped_by_file.setdefault(match.source_file, []).append(match)
    return grouped_by_file


def _apply_translations_to_content(content: str, matches: list[TextMatch]) -> str:
    """Apply a list of translations to a raw string content (default strategy)."""
    for match in sorted(matches, key=lambda m: m.span[0], reverse=True):
        start, end = match.span
        translated_text = match.translated_text or match.original_text
        content = content[:start] + translated_text + content[end:]
    return content


@dataclass
class StructuredDataStrategy:
    """Encapsulates the strategy for handling a structured data format."""

    loader: Callable[[str], Any]
    dumper: Callable[[Any], str]
    error_type: type[Exception]
    error_message: str


def _apply_translations_to_structured_data(
    content: str,
    matches: list[TextMatch],
    strategy: StructuredDataStrategy,
) -> str:
    """Apply translations to a structured string (JSON/YAML) by parsing it first."""
    try:
        data = strategy.loader(content)
    except strategy.error_type:
        logger.warning("%s Falling back to string replacement.", strategy.error_message)
        return _apply_translations_to_content(content, matches)

    match_map = {match.original_text: match.translated_text for match in matches if match.translated_text}

    def recursively_update(d: Any) -> Any:  # noqa: ANN401
        if isinstance(d, dict):
            return {key: recursively_update(value) for key, value in d.items()}
        if isinstance(d, list):
            return [recursively_update(item) for item in d]
        if isinstance(d, str) and d in match_map:
            return match_map[d]
        return d

    updated_data = recursively_update(data)
    return strategy.dumper(updated_data)


def _apply_translations_to_json_structured(content: str, matches: list[TextMatch]) -> str:
    """Apply translations by parsing the content as JSON."""
    strategy = StructuredDataStrategy(
        loader=json.loads,
        dumper=lambda data: json.dumps(data, ensure_ascii=False, indent=4),
        error_type=json.JSONDecodeError,
        error_message="File is not valid JSON.",
    )
    return _apply_translations_to_structured_data(content, matches, strategy)


def _apply_translations_to_yaml_structured(content: str, matches: list[TextMatch]) -> str:
    """Apply translations by parsing the content as YAML."""
    strategy = StructuredDataStrategy(
        loader=yaml.safe_load,
        dumper=lambda data: yaml.dump(data, allow_unicode=True, sort_keys=False),
        error_type=yaml.YAMLError,
        error_message="File is not valid YAML.",
    )
    return _apply_translations_to_structured_data(content, matches, strategy)


WRITER_STRATEGIES: dict[str, Callable[[str, list[TextMatch]], str]] = {
    ".json": _apply_translations_to_json_structured,
    ".yaml": _apply_translations_to_yaml_structured,
    ".yml": _apply_translations_to_yaml_structured,
}


def _apply_translations_by_strategy(content: str, matches: list[TextMatch], file_path: Path) -> str:
    """Select the appropriate writing strategy based on file extension."""
    file_extension = file_path.suffix.lower()
    strategy = WRITER_STRATEGIES.get(file_extension, _apply_translations_to_content)
    logger.info("Using '%s' strategy for %s", strategy.__name__, file_path.name)
    return strategy(content, matches)


def _detect_newline(file_path: Path) -> str | None:
    """Detect the newline character of a file."""
    try:
        with file_path.open(encoding="utf-8", newline="") as f:
            f.readline()
            if isinstance(f.newlines, tuple):
                return f.newlines[0]
            return f.newlines
    except (OSError, IndexError):
        return None


def _read_file_for_writing(file_path: Path) -> tuple[str, str | None]:
    """Read a file's content and detect its newline character."""
    original_newline = _detect_newline(file_path)
    content = file_path.read_text("utf-8")
    return content, original_newline


def _orchestrate_file_write(file_path: Path, file_matches: list[TextMatch], task: TranslationTask) -> None:
    """Orchestrate reading, modifying, and writing for a single file."""
    try:
        logger.info("Processing %s: %d translations to apply.", file_path, len(file_matches))
        original_content, original_newline = _read_file_for_writing(file_path)
        modified_content = _apply_translations_by_strategy(original_content, file_matches, file_path)
        output_path = _get_output_path(file_path, task)
        if output_path:
            _write_modified_content(output_path, modified_content, newline=original_newline)
        else:
            logger.warning("Output path not defined for non-in-place task. Skipping write-back for %s.", file_path)
    except OSError:
        logger.exception("Could not read or write file %s", file_path)
    except Exception:
        logger.exception("An unexpected error occurred during write-back for %s", file_path)


class WriteBackProcessor(Processor):
    """Phase 6: Write all modified content back to files."""

    def process(self, context: ExecutionContext) -> None:
        """Write all translated content back to the filesystem."""
        if context.is_dry_run:
            logger.debug("[DRY RUN] Skipping file write-back.")
            return

        if context.task.output:
            all_processed_matches = context.terminated_matches + context.cached_matches + context.matches_to_translate
            matches_by_file = _group_matches_by_file(all_processed_matches)
            logger.info("Writing back translations for %d files.", len(matches_by_file))
            for file_path, file_matches in matches_by_file.items():
                _orchestrate_file_write(file_path, file_matches, context.task)
