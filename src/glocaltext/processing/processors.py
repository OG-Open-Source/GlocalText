"""
Defines the processor pipeline for GlocalText workflows.

This module introduces a modular, extensible pipeline architecture where each stage
of the translation workflow is encapsulated within a dedicated `Processor` class.
This approach enhances clarity, maintainability, and testability compared to the
previous monolithic workflow function.

Core Components:
- Processor (ABC): An abstract base class defining the interface for all processors.
                   Each processor must implement a `process` method that modifies
                   the shared `ExecutionContext` in place.
- Concrete Processors: Each class handles a specific phase of the workflow:
    - CaptureProcessor: Finds source files and extracts text matches.
    - TerminatingRuleProcessor: Applies fast, local rules (e.g., skip, replace).
    - CacheProcessor: Checks for existing translations in the cache.
    - TranslationProcessor: Translates remaining texts using an external API.
    - CacheUpdateProcessor: Updates the cache with new translations.
    - WriteBackProcessor: Writes the modified content back to the filesystem.
"""

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import regex
import yaml

from glocaltext.models import ExecutionContext, TextMatch
from glocaltext.translate import apply_terminating_rules, process_matches
from glocaltext.types import TranslationTask

# Configure logging
logger = logging.getLogger(__name__)

# Define constants
CACHE_FILE_NAME = ".glocaltext_cache.json"


class Processor(ABC):
    """Abstract base class for a workflow processor."""

    @abstractmethod
    def process(self, context: ExecutionContext) -> None:
        """
        Process a phase of the workflow.

        This method should modify the context object in-place.
        """
        raise NotImplementedError


# Helper functions previously in workflow.py, now co-located with their processors.


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
    explicitly_excluded = {path for pattern in task.source.exclude for path in base_path.rglob(pattern)}
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
            found_matches = [
                TextMatch(
                    original_text=match.group(1),
                    source_file=file_path,
                    span=match.span(1),
                    task_name=task.name,
                    extraction_rule=rule_pattern,
                )
                for match in regex.finditer(rule_pattern, content, regex.MULTILINE, overlapped=True)
                if match.groups()
            ]
            matches.extend(found_matches)
        except regex.error as e:  # noqa: PERF203
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
        base_path = Path(context.config.project_root) if context.config.project_root else Path.cwd()
        logger.debug("Using base path for file search: %s", base_path)

        context.files_to_process = list(_find_files(context.task, base_path))
        logger.info("Task '%s': Found %d files to process.", context.task.name, len(context.files_to_process))

        for file_path in context.files_to_process:
            try:
                content = file_path.read_text("utf-8")
                file_matches = _extract_matches_from_content(content, file_path, context.task)
                context.all_matches.extend(file_matches)
            except OSError:  # noqa: PERF203
                logger.exception("Could not read file %s", file_path)
            except Exception:
                logger.exception("An unexpected error occurred while processing %s", file_path)

        logger.info("Task '%s': Captured %d total text matches.", context.task.name, len(context.all_matches))


class TerminatingRuleProcessor(Processor):
    """Phase 2: Apply terminating rules (e.g., skip, replace) to filter matches."""

    def process(self, context: ExecutionContext) -> None:
        """Apply terminating rules and update context with remaining and terminated matches."""
        remaining_matches, terminated_matches = apply_terminating_rules(context.all_matches, context.task)
        context.terminated_matches.extend(terminated_matches)
        # The remaining matches are stored temporarily and passed to the next processor
        # by the orchestrator, so we store them in a temporary field or handle in orchestrator
        context.matches_to_translate = remaining_matches  # Temporarily hold remaining
        logger.debug(
            "Task '%s': %d matches handled by terminating rules.",
            context.task.name,
            len(context.terminated_matches),
        )


def _get_task_cache_path(files: list[Path], task: TranslationTask) -> Path:
    """Determine the cache path with a new priority order."""
    if task.cache_path:
        p = Path(task.cache_path)
        return p / CACHE_FILE_NAME

    manual_cache_path_cwd = Path.cwd() / CACHE_FILE_NAME
    if manual_cache_path_cwd.exists():
        logger.debug("Found manual cache file at: %s", manual_cache_path_cwd)
        return manual_cache_path_cwd

    if not files:
        return manual_cache_path_cwd

    if len(files) == 1:
        return files[0].parent / CACHE_FILE_NAME

    common_path_str = os.path.commonpath([str(p) for p in files])
    common_path = Path(common_path_str)

    if common_path.is_file():
        common_path = common_path.parent

    return common_path / CACHE_FILE_NAME


def _load_cache(cache_path: Path, task_name: str) -> dict[str, str]:
    """Safely load the cache for a specific task from the cache file."""
    logger.debug("Loading cache for task '%s' from: %s", task_name, cache_path)
    if not cache_path.exists():
        logger.debug("Cache file not found.")
        return {}
    try:
        with cache_path.open(encoding="utf-8") as f:
            full_cache = json.load(f)
        task_cache = full_cache.get(task_name, {})
        logger.debug("Loaded %d items from cache for task '%s'.", len(task_cache), task_name)
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read or parse cache file at %s.", cache_path)
        return {}
    else:
        return task_cache


def calculate_checksum(text: str) -> str:
    """Calculate the SHA-256 checksum of a given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _partition_matches_by_cache(matches: list[TextMatch], cache: dict[str, str]) -> tuple[list[TextMatch], list[TextMatch]]:
    """Partitions matches into those found in the cache and those needing new translation."""
    logger.debug("Partitioning %d matches by cache.", len(matches))
    uncached_matches_by_text: dict[str, list[TextMatch]] = {}
    cached_matches: list[TextMatch] = []

    for match in matches:
        if match.translated_text:
            cached_matches.append(match)
            continue

        checksum = calculate_checksum(match.original_text)
        cached_translation = cache.get(checksum)

        if cached_translation:
            match.translated_text = cached_translation
            match.provider = "cached"
            cached_matches.append(match)
        else:
            uncached_matches_by_text.setdefault(match.original_text, []).append(match)

    matches_to_translate = [match for matches_list in uncached_matches_by_text.values() for match in matches_list]
    logger.debug(
        "Partitioning complete: %d matches to translate, %d matches found in cache.",
        len(matches_to_translate),
        len(cached_matches),
    )
    return matches_to_translate, cached_matches


class CacheProcessor(Processor):
    """Phase 3: Check cache for remaining matches if in incremental mode."""

    def process(self, context: ExecutionContext) -> None:
        """Check the cache for translations and partition the matches."""
        remaining_matches = context.matches_to_translate  # From previous processor
        if not context.task.incremental:
            context.matches_to_translate = remaining_matches
            return

        cache_path = _get_task_cache_path(context.files_to_process, context.task)
        cache = _load_cache(cache_path, context.task.name)

        matches_to_translate, cached_matches = _partition_matches_by_cache(remaining_matches, cache)
        context.matches_to_translate = matches_to_translate
        context.cached_matches = cached_matches

        unique_texts_count = len({m.original_text for m in context.matches_to_translate})
        logger.debug("Found %d cached translations (including rule-based).", len(context.cached_matches))
        logger.info("%d unique texts require new translation.", unique_texts_count)


class TranslationProcessor(Processor):
    """Phase 4: Translate matches that were not handled by rules or cache."""

    def process(self, context: ExecutionContext) -> None:
        """Translate texts using an external API, unless in dry-run mode."""
        if context.task.source_lang == context.task.target_lang:
            logger.info(
                "Source and target languages are the same ('%s'). Skipping API translation.",
                context.task.target_lang,
            )
            for match in context.matches_to_translate:
                match.translated_text = match.original_text
                match.provider = "skipped_same_lang"
            return

        if context.is_dry_run:
            logger.info("[DRY RUN] Skipping API translation for %d matches.", len(context.matches_to_translate))
            for match in context.matches_to_translate:
                match.provider = "dry_run_skipped"
            return

        if not context.matches_to_translate:
            return

        logger.info("Processing %d matches for API translation.", len(context.matches_to_translate))
        process_matches(
            matches=context.matches_to_translate,
            task=context.task,
            config=context.config,
            debug=context.is_debug,
        )


def _update_cache(cache_path: Path, task_name: str, matches_to_cache: list[TextMatch]) -> None:
    """Update the cache file by merging new translations."""
    logger.debug(
        "Updating cache for task '%s' at: %s with %d new items.",
        task_name,
        cache_path,
        len(matches_to_cache),
    )
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        full_cache: dict[str, dict[str, str]] = {}
        if cache_path.exists():
            with cache_path.open(encoding="utf-8") as f:
                try:
                    content = f.read()
                    if content.strip():
                        full_cache = json.loads(content)
                except json.JSONDecodeError:
                    logger.warning("Cache file %s is corrupted. A new one will be created.", cache_path)

        task_cache = full_cache.get(task_name, {})
        new_entries = {calculate_checksum(match.original_text): match.translated_text for match in matches_to_cache if match.translated_text is not None}

        if new_entries:
            task_cache.update(new_entries)
            full_cache[task_name] = task_cache
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(full_cache, f, ensure_ascii=False, indent=4)
    except OSError:
        logger.exception("Could not write to cache file at %s", cache_path)


class CacheUpdateProcessor(Processor):
    """Phase 5: Update the cache with newly translated matches."""

    def process(self, context: ExecutionContext) -> None:
        """Update the cache with new API-translated items."""
        if context.is_dry_run:
            logger.info("[DRY RUN] Skipping cache update.")
            return

        if not context.task.incremental:
            return

        matches_to_cache = [m for m in context.matches_to_translate if m.translated_text is not None and m.provider not in ("cached", "rule", "skipped")]
        if matches_to_cache:
            cache_path = _get_task_cache_path(context.files_to_process, context.task)
            logger.debug("Updating cache with %d new, API-translated items.", len(matches_to_cache))
            _update_cache(cache_path, context.task.name, matches_to_cache)


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
        if match.translated_text is not None:
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
            logger.info("[DRY RUN] Skipping file write-back.")
            return

        if context.task.output:
            all_processed_matches = context.terminated_matches + context.cached_matches + context.matches_to_translate
            matches_by_file = _group_matches_by_file(all_processed_matches)
            logger.info("Writing back translations for %d files.", len(matches_by_file))
            for file_path, file_matches in matches_by_file.items():
                _orchestrate_file_write(file_path, file_matches, context.task)
