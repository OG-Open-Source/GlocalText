"""File capture and text extraction processor."""

import logging
from collections.abc import Iterable
from pathlib import Path

import regex

from glocaltext import paths
from glocaltext.models import ExecutionContext, TextMatch
from glocaltext.text_coverage import TextCoverage
from glocaltext.types import TranslationTask

from .base import Processor

__all__ = [
    "CaptureProcessor",
    "_exclude_files",
    "_extract_matches_from_content",
    "_find_files",
    "_get_included_files",
]

logger = logging.getLogger(__name__)


def _get_included_files(task: TranslationTask, base_path: Path) -> set[Path]:
    """Resolve included files from glob patterns and literal paths."""
    included_files: set[Path] = set()
    for pattern in task.source.include:
        if any(char in pattern for char in "*?[]"):
            glob_method = base_path.rglob if "**" in pattern else base_path.glob
            included_files.update(glob_method(pattern))
        else:
            file_path = Path(pattern) if Path(pattern).is_absolute() else base_path / pattern
            if file_path.is_file():
                included_files.add(file_path.resolve())
    return included_files


def _exclude_files(
    included_files: set[Path],
    task: TranslationTask,
    base_path: Path,
) -> set[Path]:
    """Exclude files based on task's exclude patterns and output directory."""
    # Exclude files based on 'exclude' patterns
    try:
        explicitly_excluded = {path for pattern in task.source.exclude for path in base_path.rglob(pattern)}
    except Exception:
        logger.exception("Error during file exclusion pattern resolution. Proceeding with included files only.")
        explicitly_excluded = set()
    candidate_files = included_files - explicitly_excluded

    # Exclude files in the output directory
    if not task.output.in_place and task.output.path:
        try:
            output_dir_abs = Path(task.output.path).resolve()
            candidate_files = {f for f in candidate_files if not str(f.resolve()).startswith(str(output_dir_abs))}
        except Exception:
            logger.exception("Unexpected error during output path exclusion.")

    return candidate_files


def _find_files(task: TranslationTask, base_path: Path) -> Iterable[Path]:
    """Find all files to be processed by a task."""
    included_files = _get_included_files(task, base_path)
    final_files = _exclude_files(included_files, task, base_path)
    return sorted(final_files)


def _extract_matches_from_content(content: str, file_path: Path, task: TranslationTask) -> list[TextMatch]:
    """Extract text matches from a string using the task's extraction rules."""
    matches: list[TextMatch] = []
    # Ensure extraction_rules is treated as a list even if it's None
    extraction_rules = task.extraction_rules or []
    for rule_pattern in extraction_rules:
        try:
            found_matches = []
            for match in regex.finditer(rule_pattern, content, regex.MULTILINE, overlapped=True):
                if match.groups():
                    # Create coverage tracker initialized with the original text
                    coverage = TextCoverage(content)
                    # Add the range covered by this match
                    coverage.add_range(match.start(1), match.end(1))

                    # Create TextMatch with coverage
                    text_match = TextMatch(
                        original_text=match.group(1),
                        source_file=file_path,
                        span=match.span(1),
                        task_name=task.name,
                        extraction_rule=rule_pattern,
                        coverage=coverage,
                    )
                    found_matches.append(text_match)

            matches.extend(found_matches)
        except regex.error as e:
            logger.warning(
                "Skipping invalid regex pattern '%s' in task '%s': %s",
                rule_pattern,
                task.name,
                e,
            )
    return matches


class CaptureProcessor(Processor):
    """Phase 1: Find files and extract all text matches based on task rules."""

    def process(self, context: ExecutionContext) -> None:
        """Find files and capture all text matches within them."""
        try:
            base_path = paths.find_project_root()
            logger.debug("Using project root for file search: %s", base_path)

            context.files_to_process = list(_find_files(context.task, base_path))
            logger.info("Task '%s': Found %d files to process.", context.task.name, len(context.files_to_process))

            for file_path in context.files_to_process:
                try:
                    content = file_path.read_text("utf-8")
                    file_matches = _extract_matches_from_content(content, file_path, context.task)
                    context.all_matches.extend(file_matches)
                except OSError:
                    logger.exception("Could not read file %s", file_path)
                except Exception:
                    logger.exception("An unexpected error occurred while processing %s", file_path)

            logger.info("Task '%s': Captured %d total text matches.", context.task.name, len(context.all_matches))
        except FileNotFoundError:
            logger.exception(
                "Could not find project root based on '%s' anchor. Cannot capture files.",
                paths.OGOS_SUBDIR,
            )
