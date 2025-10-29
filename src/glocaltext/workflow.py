"""Manages the overall GlocalText translation workflow."""

import hashlib
import json
import logging
import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import regex
import yaml

from .config import GlocalConfig, TranslationTask
from .models import TextMatch
from .translate import apply_terminating_rules, process_matches

# Define constants
CACHE_FILE_NAME = ".glocaltext_cache.json"

# Configure logging
logger = logging.getLogger(__name__)


def calculate_checksum(text: str) -> str:
    """Calculate the SHA-256 checksum of a given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_task_cache_path(files: list[Path], task: TranslationTask) -> Path:
    """Determine the cache path with a new priority order."""
    if task.cache_path:
        p = Path(task.cache_path)
        return p / CACHE_FILE_NAME

    manual_cache_path_cwd = Path.cwd() / CACHE_FILE_NAME
    if manual_cache_path_cwd.exists():
        logger.info("Found manual cache file at: %s", manual_cache_path_cwd)
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


def load_cache(cache_path: Path, task_name: str) -> dict[str, str]:
    """Safely load the cache for a specific task from the cache file."""
    if not cache_path.exists():
        return {}
    try:
        with cache_path.open(encoding="utf-8") as f:
            full_cache = json.load(f)
        return full_cache.get(task_name, {})
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read or parse cache file at %s.", cache_path)
        return {}


def update_cache(cache_path: Path, task_name: str, matches_to_cache: list[TextMatch]) -> None:
    """Update the cache file by merging new translations into the existing task cache."""
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
                    logger.warning(
                        "Cache file %s is corrupted. A new one will be created.",
                        cache_path,
                    )

        task_cache = full_cache.get(task_name, {})
        new_entries = {calculate_checksum(match.original_text): match.translated_text for match in matches_to_cache if match.translated_text is not None}

        if new_entries:
            task_cache.update(new_entries)
            full_cache[task_name] = task_cache
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(full_cache, f, ensure_ascii=False, indent=4)
    except OSError:
        logger.exception("Could not write to cache file at %s", cache_path)


def _find_files(task: TranslationTask) -> Iterable[Path]:
    base_path = Path.cwd()
    included_files = {path for pattern in task.source.include for path in base_path.rglob(pattern)}
    excluded_files = {path for pattern in task.exclude for path in base_path.rglob(pattern)}
    return sorted(included_files - excluded_files)


def _apply_regex_rewrites(content: str, task: TranslationTask) -> str:
    if not task.regex_rewrites:
        return content
    for pattern, replacement in task.regex_rewrites.items():
        try:
            content = regex.sub(pattern, replacement, content)
        except regex.error as e:  # noqa: PERF203
            logger.warning(
                "Skipping invalid regex rewrite pattern '%s' in task '%s': %s",
                pattern,
                task.name,
                e,
            )
    return content


def _extract_matches_from_content(content: str, file_path: Path, task: TranslationTask) -> list[TextMatch]:
    matches: list[TextMatch] = []
    for rule_pattern in task.extraction_rules:
        try:
            for match in regex.finditer(rule_pattern, content, regex.MULTILINE, overlapped=True):
                if match.groups():
                    matches.append(  # noqa: PERF401
                        TextMatch(
                            original_text=match.group(1),
                            source_file=file_path,
                            span=match.span(1),
                            task_name=task.name,
                            extraction_rule=rule_pattern,
                        ),
                    )
        except regex.error as e:  # noqa: PERF203
            logger.warning(
                "Skipping invalid regex pattern '%s' in task '%s': %s",
                rule_pattern,
                task.name,
                e,
            )
    return matches


def _detect_newline(file_path: Path) -> str | None:
    try:
        with file_path.open(encoding="utf-8", newline="") as f:
            f.readline()
            if isinstance(f.newlines, tuple):
                return f.newlines[0]
            return f.newlines
    except (OSError, IndexError):
        return None


def capture_text_matches(task: TranslationTask, config: GlocalConfig, files_to_process: list[Path]) -> list[TextMatch]:
    """Capture all text matches from source files based on task rules."""
    all_matches: list[TextMatch] = []
    logger.info("Task '%s': Found %d files to process.", task.name, len(files_to_process))
    for file_path in files_to_process:
        try:
            content = file_path.read_text("utf-8")
            content = _apply_regex_rewrites(content, task)
            file_matches = _extract_matches_from_content(content, file_path, task)
            all_matches.extend(file_matches)
        except OSError:  # noqa: PERF203
            logger.exception("Could not read file %s", file_path)
        except Exception:
            logger.exception("An unexpected error occurred while processing %s", file_path)
    logger.info("Task '%s': Captured %d total text matches.", task.name, len(all_matches))
    if config.debug_options.enabled:
        debug_messages = [f"[DEBUG] Captured: '{match.original_text}' from file {match.source_file} at span {match.span}" for match in all_matches]
        if config.debug_options.log_path:
            log_dir = Path(config.debug_options.log_path)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "glocaltext_debug.log"
            with log_file.open("a", encoding="utf-8") as f:
                f.write("\n".join(debug_messages) + "\n")
            logger.info("Debug log saved to %s", log_file)
        else:
            for msg in debug_messages:
                logger.info(msg)
    return all_matches


def _get_output_path(file_path: Path, task: TranslationTask) -> Path | None:
    task_output = task.output
    if task_output.in_place:
        if task_output.filename_suffix:
            return file_path.with_name(f"{file_path.stem}{task_output.filename_suffix}{file_path.suffix}")
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
    if task_output.filename_suffix:
        new_name = f"{file_path.stem}{task_output.filename_suffix}{file_path.suffix}"
        return output_dir / new_name
    return output_dir / file_path.name


def _write_modified_content(output_path: Path, content: str, newline: str | None) -> None:
    if output_path.parent.is_file():
        logger.warning(
            "Output directory path %s exists as a file. Deleting it to create directory.",
            output_path.parent,
        )
        output_path.parent.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, "utf-8", newline=newline)
    logger.info("Successfully wrote modified content to %s", output_path)


def _is_overlapping(span1: tuple[int, int], span2: tuple[int, int]) -> bool:
    """Check if two spans overlap."""
    return span1[0] < span2[1] and span2[0] < span1[1]


def _deduplicate_matches(matches: list[TextMatch]) -> list[TextMatch]:
    """
    De-duplicate a list of matches, keeping only one for each unique (text, span) combination.

    This function prevents redundant processing of the exact same text captured
    at the exact same location, which can happen if multiple extraction rules overlap
    perfectly.
    """
    seen_signatures = set()
    deduplicated_matches: list[TextMatch] = []
    for match in matches:
        signature = (match.original_text, match.span)
        if signature not in seen_signatures:
            deduplicated_matches.append(match)
            seen_signatures.add(signature)
    return deduplicated_matches


def _group_matches_by_file(matches: list[TextMatch]) -> dict[Path, list[TextMatch]]:
    """
    Group and de-duplicate a list of TextMatch objects by their source file.

    This function filters for matches with translated text, groups them by file,
    and then de-duplicates any overlapping matches within each file.
    """
    # 1. Group all valid matches by file
    grouped_by_file: dict[Path, list[TextMatch]] = {}
    for match in matches:
        if match.translated_text is not None:
            grouped_by_file.setdefault(match.source_file, []).append(match)

    # 2. Return the groups directly without de-duplication.
    # Why: At the write-back stage, we need to apply translations to ALL occurrences,
    # including duplicates. De-duplicating here was the root cause of the bug
    # where only one of several identical texts was being translated.
    return grouped_by_file


def _apply_translations_to_content(content: str, matches: list[TextMatch]) -> str:
    """
    Apply a list of translations to a raw string content (default strategy).

    This helper isolates the core string manipulation logic. It sorts matches
    in reverse order of their position to avoid invalidating character indices
    of earlier matches.
    """
    # Sort matches by their starting position in reverse order.
    for match in sorted(matches, key=lambda m: m.span[0], reverse=True):
        start, end = match.span
        # Ensure that we have a translated text, otherwise, we'd be inserting None.
        translated_text = match.translated_text or match.original_text
        content = content[:start] + translated_text + content[end:]
    return content


def _apply_translations_to_structured_data(  # noqa: PLR0913
    content: str,
    matches: list[TextMatch],
    loader: Callable[[str], Any],
    dumper: Callable[[Any], str],
    error_type: type[Exception],
    error_message: str,
) -> str:
    """
    Apply translations to a structured string (JSON/YAML) by parsing it first.

    This function walks through the nested data structure and replaces string values
    that match the 'original_text' of a provided match. If parsing fails, it
    reverts to a simple string replacement strategy.
    """
    try:
        data = loader(content)
    except error_type:
        logger.warning("%s Falling back to string replacement.", error_message)
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
    return dumper(updated_data)


def _apply_translations_to_json_structured(content: str, matches: list[TextMatch]) -> str:
    """Apply translations by parsing the content as JSON."""
    return _apply_translations_to_structured_data(
        content,
        matches,
        loader=json.loads,
        dumper=lambda data: json.dumps(data, ensure_ascii=False, indent=4),
        error_type=json.JSONDecodeError,
        error_message="File is not valid JSON.",
    )


def _apply_translations_to_yaml_structured(content: str, matches: list[TextMatch]) -> str:
    """Apply translations by parsing the content as YAML."""
    return _apply_translations_to_structured_data(
        content,
        matches,
        loader=yaml.safe_load,
        dumper=lambda data: yaml.dump(data, allow_unicode=True, sort_keys=False),
        error_type=yaml.YAMLError,
        error_message="File is not valid YAML.",
    )


# Strategy mapping for different file types
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


def _read_file_for_writing(file_path: Path) -> tuple[str, str | None]:
    """Read a file's content and detect its newline character for consistent writing."""
    original_newline = _detect_newline(file_path)
    content = file_path.read_text("utf-8")
    return content, original_newline


def _orchestrate_file_write(file_path: Path, file_matches: list[TextMatch], task: TranslationTask) -> None:
    """
    Orchestrate reading, modifying, and writing for a single file.

    This function was created by refactoring the original _write_to_file to
    break it down into smaller, more manageable pieces.
    """
    try:
        logger.info("Processing %s: %d translations to apply.", file_path, len(file_matches))

        # 1. Read source file
        original_content, original_newline = _read_file_for_writing(file_path)

        # 2. Apply translations to content
        modified_content = _apply_translations_by_strategy(original_content, file_matches, file_path)

        # 3. Write modified content to the correct output path
        output_path = _get_output_path(file_path, task)
        if output_path:
            _write_modified_content(output_path, modified_content, newline=original_newline)
        else:
            logger.warning(
                "Output path is not defined for a non-in-place task. Skipping write-back for %s.",
                file_path,
            )

    except OSError:
        logger.exception("Could not read or write file %s", file_path)
    except Exception:
        logger.exception("An unexpected error occurred during write-back for %s", file_path)


def precise_write_back(matches: list[TextMatch], task: TranslationTask) -> None:
    """
    Group matches by file and write the translated content back.

    Why: This function was refactored to improve clarity and reduce complexity by
    delegating the file I/O orchestration to a new `_orchestrate_file_write` helper,
    which in turn uses more specialized functions for reading and writing. This
    adheres to the Single Responsibility Principle.
    """
    if not matches:
        logger.info("No matches with translated text to write back.")
        return

    matches_by_file = _group_matches_by_file(matches)
    logger.info("Writing back translations for %d files.", len(matches_by_file))

    for file_path, file_matches in matches_by_file.items():
        _orchestrate_file_write(file_path, file_matches, task)


def _phase_1_capture(task: TranslationTask, config: GlocalConfig) -> tuple[list[Path], list[TextMatch]]:
    """Phase 1: Find files and extract all text matches based on task rules."""
    files_to_process = list(_find_files(task))
    all_matches = capture_text_matches(task, config, files_to_process)
    return files_to_process, all_matches


def _phase_2_apply_terminating_rules(all_matches: list[TextMatch], task: TranslationTask) -> tuple[list[TextMatch], list[TextMatch]]:
    """Phase 2: Apply terminating rules (e.g., skip, replace) to filter matches."""
    remaining_matches, terminated_matches = apply_terminating_rules(all_matches, task)
    logger.info(
        "Task '%s': %d matches handled by terminating rules.",
        task.name,
        len(terminated_matches),
    )
    return remaining_matches, terminated_matches


def _partition_matches_by_cache(matches: list[TextMatch], cache: dict[str, str]) -> tuple[list[TextMatch], list[TextMatch]]:
    """
    Partitions matches into those found in the cache and those needing new translation.

    This function iterates through a list of matches once, sorting them into two groups:
    1.  `cached_matches`: Matches that already have a translation, either from a
        previous rule or from the cache.
    2.  `matches_to_translate`: All match instances corresponding to unique original
        texts that were not found in the cache.

    Returns:
        A tuple containing (`matches_to_translate`, `cached_matches`).

    """
    uncached_matches_by_text: dict[str, list[TextMatch]] = {}
    cached_matches: list[TextMatch] = []

    for match in matches:
        # If a translation already exists (e.g., from a rule), treat as cached.
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
            # Group all matches for a text that needs translation.
            uncached_matches_by_text.setdefault(match.original_text, []).append(match)

    # Flatten the dictionary values to get a single list of matches to translate.
    matches_to_translate = [match for matches_list in uncached_matches_by_text.values() for match in matches_list]
    return matches_to_translate, cached_matches


def _phase_3_check_cache(
    remaining_matches: list[TextMatch],
    files_to_process: list[Path],
    task: TranslationTask,
) -> tuple[list[TextMatch], list[TextMatch]]:
    """
    Phase 3: Check cache for remaining matches if in incremental mode.

    This refactored function delegates the complex partitioning logic to the
    `_partition_matches_by_cache` helper, significantly reducing its own complexity.
    Its sole responsibility is to orchestrate the cache check.
    """
    if not task.incremental:
        logger.info("Task '%s': Running in full translation mode (cache is ignored).", task.name)
        return remaining_matches, []

    logger.info("Task '%s': Running in incremental mode. Checking cache...", task.name)
    cache_path = _get_task_cache_path(files_to_process, task)
    cache = load_cache(cache_path, task.name)
    logger.info("Loaded %d items from cache for task '%s'.", len(cache), task.name)

    matches_to_translate, cached_matches = _partition_matches_by_cache(remaining_matches, cache)

    # To provide an accurate log, count the unique texts that need translation.
    unique_texts_count = len({m.original_text for m in matches_to_translate})

    logger.info("Found %d cached translations (including rule-based).", len(cached_matches))
    logger.info("%d unique texts require new translation.", unique_texts_count)
    return matches_to_translate, cached_matches


def _phase_4_translate(matches_to_translate: list[TextMatch], task: TranslationTask, config: GlocalConfig) -> None:
    """Phase 4: Translate matches that were not handled by rules or cache."""
    if matches_to_translate:
        logger.info("Processing %d matches for API translation.", len(matches_to_translate))
        process_matches(matches_to_translate, task, config)


def _phase_5_update_cache(
    matches_translated: list[TextMatch],
    files_to_process: list[Path],
    task: TranslationTask,
) -> None:
    """Phase 5: Update the cache with newly translated matches."""
    if not task.incremental:
        return

    # Why: We only want to cache matches that were successfully translated via an API.
    # We must exclude matches that were already from the cache, or handled by local rules,
    # to prevent incorrect or redundant cache entries.
    matches_to_cache = [m for m in matches_translated if m.translated_text is not None and m.provider not in ("cached", "rule", "skipped")]
    if matches_to_cache:
        cache_path = _get_task_cache_path(files_to_process, task)
        logger.info("Updating cache with %d new, API-translated items.", len(matches_to_cache))
        update_cache(cache_path, task.name, matches_to_cache)


def _phase_6_write_back(all_processed_matches: list[TextMatch], task: TranslationTask) -> None:
    """Phase 6: Write all modified content back to files."""
    if task.output:
        precise_write_back(all_processed_matches, task)


def run_task(task: TranslationTask, config: GlocalConfig) -> list[TextMatch]:
    """
    Run a single translation task by orchestrating a multi-phase workflow.

    Why: This function was refactored from a monolithic block into a clear,
    step-by-step orchestrator. Each "phase" is now a separate, testable
    function, dramatically reducing complexity and improving maintainability.
    The flow from capturing text to translating and writing it back is now
    explicit and easy to follow.
    """
    # Phase 1: Capture all potential matches from source files.
    files_to_process, all_matches = _phase_1_capture(task, config)

    # Phase 2: Apply local, fast "terminating" rules first.
    remaining_matches, terminated_matches = _phase_2_apply_terminating_rules(all_matches, task)

    # Phase 3: Use the cache to avoid re-translating known text.
    matches_to_translate, cached_matches = _phase_3_check_cache(remaining_matches, files_to_process, task)

    # Phase 4: Translate the remaining text via external APIs.
    _phase_4_translate(matches_to_translate, task, config)

    # Phase 5: Update the cache with the newly translated content.
    _phase_5_update_cache(matches_to_translate, files_to_process, task)

    # Phase 6: Combine all matches and write them back to the filesystem.
    # This includes matches from rules, cache, and new translations.
    final_matches = terminated_matches + cached_matches + matches_to_translate
    _phase_6_write_back(final_matches, task)

    return final_matches
