import hashlib
import json
import logging
import os
from glob import glob
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Tuple

import regex
import yaml

from .config import GlocalConfig, TranslationTask
from .models import TextMatch
from .translate import apply_terminating_rules, process_matches

# Define constants
CACHE_FILE_NAME = ".glocaltext_cache.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def calculate_checksum(text: str) -> str:
    """Calculates the SHA-256 checksum of a given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_task_cache_path(files: List[Path], task: TranslationTask) -> Path:
    """Determines the cache path with a new priority order."""
    if task.cache_path:
        p = Path(task.cache_path)
        return p / CACHE_FILE_NAME

    manual_cache_path_cwd = Path.cwd() / CACHE_FILE_NAME
    if manual_cache_path_cwd.exists():
        logging.info(f"Found manual cache file at: {manual_cache_path_cwd}")
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


def load_cache(cache_path: Path, task_name: str) -> Dict[str, str]:
    """Safely loads the cache for a specific task from the cache file."""
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, encoding="utf-8") as f:
            full_cache = json.load(f)
        return full_cache.get(task_name, {})
    except (OSError, json.JSONDecodeError):
        logging.warning(f"Could not read or parse cache file at {cache_path}.")
        return {}


def update_cache(cache_path: Path, task_name: str, matches_to_cache: List[TextMatch]):
    """Updates the cache file by merging new translations into the existing task cache."""
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        full_cache: Dict[str, Dict[str, str]] = {}
        if cache_path.exists():
            with open(cache_path, encoding="utf-8") as f:
                try:
                    content = f.read()
                    if content.strip():
                        full_cache = json.loads(content)
                except json.JSONDecodeError:
                    logging.warning(f"Cache file {cache_path} is corrupted. A new one will be created.")

        task_cache = full_cache.get(task_name, {})
        new_entries = {calculate_checksum(match.original_text): match.translated_text for match in matches_to_cache if match.translated_text is not None}

        if new_entries:
            task_cache.update(new_entries)
            full_cache[task_name] = task_cache
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(full_cache, f, ensure_ascii=False, indent=4)
    except OSError as e:
        logging.error(f"Could not write to cache file at {cache_path}: {e}")


def _find_files(task: TranslationTask) -> Iterable[Path]:
    base_path = Path.cwd()
    included_files = set()
    for pattern in task.source.include:
        for file_path in glob(str(base_path / pattern), recursive=True):
            included_files.add(Path(file_path))
    excluded_files = set()
    for pattern in task.exclude:
        for file_path in glob(str(base_path / pattern), recursive=True):
            excluded_files.add(Path(file_path))
    return sorted(included_files - excluded_files)


def _apply_regex_rewrites(content: str, task: TranslationTask) -> str:
    if not task.regex_rewrites:
        return content
    for pattern, replacement in task.regex_rewrites.items():
        try:
            content = regex.sub(pattern, replacement, content)
        except regex.error as e:
            logging.warning(f"Skipping invalid regex rewrite pattern '{pattern}' in task '{task.name}': {e}")
    return content


def _extract_matches_from_content(content: str, file_path: Path, task: TranslationTask) -> List[TextMatch]:
    matches = []
    for rule_pattern in task.extraction_rules:
        try:
            for match in regex.finditer(rule_pattern, content, regex.MULTILINE, overlapped=True):
                if match.groups():
                    matches.append(
                        TextMatch(
                            original_text=match.group(1),
                            source_file=file_path,
                            span=match.span(1),
                            task_name=task.name,
                            extraction_rule=rule_pattern,
                        )
                    )
        except regex.error as e:
            logging.warning(f"Skipping invalid regex pattern '{rule_pattern}' in task '{task.name}': {e}")
    return matches


def _detect_newline(file_path: Path) -> str | None:
    try:
        with open(file_path, encoding="utf-8", newline="") as f:
            f.readline()
            if isinstance(f.newlines, tuple):
                return f.newlines[0]
            return f.newlines
    except (OSError, IndexError):
        return None


def capture_text_matches(task: TranslationTask, config: GlocalConfig, files_to_process: List[Path]) -> List[TextMatch]:
    all_matches = []
    logging.info(f"Task '{task.name}': Found {len(files_to_process)} files to process.")
    for file_path in files_to_process:
        try:
            content = file_path.read_text("utf-8")
            content = _apply_regex_rewrites(content, task)
            file_matches = _extract_matches_from_content(content, file_path, task)
            all_matches.extend(file_matches)
        except OSError as e:
            logging.error(f"Could not read file {file_path}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred while processing {file_path}: {e}")
    logging.info(f"Task '{task.name}': Captured {len(all_matches)} total text matches.")
    if config.debug_options.enabled:
        debug_messages = [f"[DEBUG] Captured: '{match.original_text}' from file {match.source_file} at span {match.span}" for match in all_matches]
        if config.debug_options.log_path:
            log_dir = Path(config.debug_options.log_path)
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "glocaltext_debug.log"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write("\n".join(debug_messages) + "\n")
            logging.info(f"Debug log saved to {log_file}")
        else:
            for msg in debug_messages:
                logging.info(msg)
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


def _write_modified_content(output_path: Path, content: str, newline: str | None):
    if output_path.parent.is_file():
        logging.warning(f"Output directory path {output_path.parent} exists as a file. Deleting it to create directory.")
        output_path.parent.unlink()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, "utf-8", newline=newline)
    logging.info(f"Successfully wrote modified content to {output_path}")


def _is_overlapping(span1: Tuple[int, int], span2: Tuple[int, int]) -> bool:
    """Checks if two spans overlap."""
    return span1[0] < span2[1] and span2[0] < span1[1]


def _deduplicate_matches(matches: List[TextMatch]) -> List[TextMatch]:
    """
    De-duplicates a list of matches, keeping only one match for each unique (text, span) combination.

    Why: This function prevents redundant processing of the exact same text captured
    at the exact same location, which can happen if multiple extraction rules overlap
    perfectly. It ensures that translations are applied correctly to all unique
    occurrences of a text, even if the text content itself is repeated.
    """
    seen_signatures = set()
    deduplicated_matches: List[TextMatch] = []
    for match in matches:
        signature = (match.original_text, match.span)
        if signature not in seen_signatures:
            deduplicated_matches.append(match)
            seen_signatures.add(signature)
    return deduplicated_matches


def _group_matches_by_file(matches: List[TextMatch]) -> Dict[Path, List[TextMatch]]:
    """
    Groups and de-duplicates a list of TextMatch objects by their source file.

    This function filters for matches with translated text, groups them by file,
    and then de-duplicates any overlapping matches within each file.
    """
    # 1. Group all valid matches by file
    grouped_by_file: Dict[Path, List[TextMatch]] = {}
    for match in matches:
        if match.translated_text is not None:
            grouped_by_file.setdefault(match.source_file, []).append(match)

    # 2. Return the groups directly without de-duplication.
    # Why: At the write-back stage, we need to apply translations to ALL occurrences,
    # including duplicates. De-duplicating here was the root cause of the bug
    # where only one of several identical texts was being translated.
    return grouped_by_file


def _apply_translations_to_content(content: str, matches: List[TextMatch]) -> str:
    """
    (Default Strategy) Applies a list of translations to a raw string content.

    Why: This helper isolates the core string manipulation logic. It sorts matches
    in reverse order of their position in the text. This is a critical detail:
    by applying changes from the end of the file to the beginning, we ensure that
    the character indices (spans) of earlier matches are not invalidated by
    the length changes from later replacements. This is the fallback for unstructured files.
    """
    # Sort matches by their starting position in reverse order.
    for match in sorted(matches, key=lambda m: m.span[0], reverse=True):
        start, end = match.span
        # Ensure that we have a translated text, otherwise, we'd be inserting None.
        translated_text = match.translated_text or match.original_text
        content = content[:start] + translated_text + content[end:]
    return content


def _apply_translations_to_structured_data(
    content: str,
    matches: List[TextMatch],
    loader: Callable[[str], Any],
    dumper: Callable[[Any], str],
    error_type: type[Exception],
    error_message: str,
) -> str:
    """
    (Generic Structured Strategy) Applies translations to a structured string (JSON/YAML) by parsing it first.

    This function walks through the nested data structure and replaces string values
    that match the 'original_text' of a provided match. If parsing fails, it
    reverts to a simple string replacement strategy.
    """
    try:
        data = loader(content)
    except error_type:
        logging.warning(f"{error_message} Falling back to string replacement.")
        return _apply_translations_to_content(content, matches)

    match_map = {match.original_text: match.translated_text for match in matches if match.translated_text}

    def recursively_update(d: Any) -> Any:
        if isinstance(d, dict):
            return {key: recursively_update(value) for key, value in d.items()}
        if isinstance(d, list):
            return [recursively_update(item) for item in d]
        if isinstance(d, str) and d in match_map:
            return match_map[d]
        return d

    updated_data = recursively_update(data)
    return dumper(updated_data)


def _apply_translations_to_json_structured(content: str, matches: List[TextMatch]) -> str:
    """(JSON Strategy) Applies translations by parsing the content as JSON."""
    return _apply_translations_to_structured_data(
        content,
        matches,
        loader=json.loads,
        dumper=lambda data: json.dumps(data, ensure_ascii=False, indent=4),
        error_type=json.JSONDecodeError,
        error_message="File is not valid JSON.",
    )


def _apply_translations_to_yaml_structured(content: str, matches: List[TextMatch]) -> str:
    """(YAML Strategy) Applies translations by parsing the content as YAML."""
    return _apply_translations_to_structured_data(
        content,
        matches,
        loader=yaml.safe_load,
        dumper=lambda data: yaml.dump(data, allow_unicode=True, sort_keys=False),
        error_type=yaml.YAMLError,
        error_message="File is not valid YAML.",
    )


# Strategy mapping for different file types
WRITER_STRATEGIES: Dict[str, Callable[[str, List[TextMatch]], str]] = {
    ".json": _apply_translations_to_json_structured,
    ".yaml": _apply_translations_to_yaml_structured,
    ".yml": _apply_translations_to_yaml_structured,
}


def _apply_translations_by_strategy(content: str, matches: List[TextMatch], file_path: Path) -> str:
    """
    Selects the appropriate writing strategy based on file extension.
    """
    file_extension = file_path.suffix.lower()
    strategy = WRITER_STRATEGIES.get(file_extension, _apply_translations_to_content)
    logging.info(f"Using '{strategy.__name__}' strategy for {file_path.name}")
    return strategy(content, matches)


def _read_file_for_writing(file_path: Path) -> Tuple[str, str | None]:
    """Reads a file's content and detects its newline character for consistent writing."""
    original_newline = _detect_newline(file_path)
    content = file_path.read_text("utf-8")
    return content, original_newline


def _orchestrate_file_write(file_path: Path, file_matches: List[TextMatch], task: TranslationTask):
    """
    Orchestrates reading, modifying, and writing for a single file.
    This function was created by refactoring the original _write_to_file to
    break it down into smaller, more manageable pieces.
    """
    try:
        logging.info(f"Processing {file_path}: {len(file_matches)} translations to apply.")

        # 1. Read source file
        original_content, original_newline = _read_file_for_writing(file_path)

        # 2. Apply translations to content
        modified_content = _apply_translations_by_strategy(original_content, file_matches, file_path)

        # 3. Write modified content to the correct output path
        output_path = _get_output_path(file_path, task)
        if output_path:
            _write_modified_content(output_path, modified_content, newline=original_newline)
        else:
            logging.warning(f"Output path is not defined for a non-in-place task. Skipping write-back for {file_path}.")

    except OSError as e:
        logging.error(f"Could not read or write file {file_path}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during write-back for {file_path}: {e}")


def precise_write_back(matches: List[TextMatch], task: TranslationTask):
    """
    Groups matches by file and writes the translated content back.

    Why: This function was refactored to improve clarity and reduce complexity by
    delegating the file I/O orchestration to a new `_orchestrate_file_write` helper,
    which in turn uses more specialized functions for reading and writing. This
    adheres to the Single Responsibility Principle.
    """
    if not matches:
        logging.info("No matches with translated text to write back.")
        return

    matches_by_file = _group_matches_by_file(matches)
    logging.info(f"Writing back translations for {len(matches_by_file)} files.")

    for file_path, file_matches in matches_by_file.items():
        _orchestrate_file_write(file_path, file_matches, task)


def _phase_1_capture(task: TranslationTask, config: GlocalConfig) -> Tuple[List[Path], List[TextMatch]]:
    """Phase 1: Find files and extract all text matches based on task rules."""
    files_to_process = list(_find_files(task))
    all_matches = capture_text_matches(task, config, files_to_process)
    return files_to_process, all_matches


def _phase_2_apply_terminating_rules(all_matches: List[TextMatch], task: TranslationTask) -> Tuple[List[TextMatch], List[TextMatch]]:
    """Phase 2: Apply terminating rules (e.g., skip, replace) to filter matches."""
    remaining_matches, terminated_matches = apply_terminating_rules(all_matches, task)
    logging.info(f"Task '{task.name}': {len(terminated_matches)} matches handled by terminating rules.")
    return remaining_matches, terminated_matches


def _phase_3_check_cache(remaining_matches: List[TextMatch], files_to_process: List[Path], task: TranslationTask) -> Tuple[List[TextMatch], List[TextMatch]]:
    """Phase 3: Check cache for remaining matches if in incremental mode."""
    if not task.incremental:
        logging.info(f"Task '{task.name}': Running in full translation mode (cache is ignored).")
        return remaining_matches, []

    logging.info(f"Task '{task.name}': Running in incremental mode. Checking cache...")
    cache_path = _get_task_cache_path(files_to_process, task)
    cache = load_cache(cache_path, task.name)
    logging.info(f"Loaded {len(cache)} items from cache for task '{task.name}'.")

    matches_to_translate: List[TextMatch] = []
    cached_matches: List[TextMatch] = []
    # Create a map of checksums for all remaining matches
    # to avoid re-calculating checksums repeatedly.
    checksum_map = {m.match_id: calculate_checksum(m.original_text) for m in remaining_matches}

    # First, apply all cached translations to any matching text.
    # This is the crucial step: we iterate through all matches and apply
    # the cache, instead of just partitioning the list.
    for match in remaining_matches:
        checksum = checksum_map[match.match_id]
        if checksum in cache:
            if not match.translated_text:  # Apply only if not already translated
                match.translated_text = cache[checksum]
                match.provider = "cached"
            cached_matches.append(match)

    # Now, determine which texts still need to be translated.
    # A text needs translation if any of its instances lack a translated_text.
    unique_texts_to_translate = {m.original_text for m in remaining_matches if not m.translated_text and calculate_checksum(m.original_text) not in cache}

    # Collect all match objects that correspond to the unique texts needing translation.
    for text in unique_texts_to_translate:
        matches_to_translate.extend([m for m in remaining_matches if m.original_text == text and not m.translated_text])

    logging.info(f"Found {len(cached_matches)} cached translations.")
    logging.info(f"{len(matches_to_translate)} texts require new translation.")
    return matches_to_translate, cached_matches


def _phase_4_translate(matches_to_translate: List[TextMatch], task: TranslationTask, config: GlocalConfig):
    """Phase 4: Translate matches that were not handled by rules or cache."""
    if matches_to_translate:
        logging.info(f"Processing {len(matches_to_translate)} matches for API translation.")
        process_matches(matches_to_translate, task, config)


def _phase_5_update_cache(matches_translated: List[TextMatch], files_to_process: List[Path], task: TranslationTask):
    """Phase 5: Update the cache with newly translated matches."""
    if not task.incremental:
        return

    # Why: We only want to cache matches that were successfully translated via an API.
    # We must exclude matches that were already from the cache, or handled by local rules,
    # to prevent incorrect or redundant cache entries.
    matches_to_cache = [m for m in matches_translated if m.translated_text is not None and m.provider not in ("cached", "rule", "skipped")]
    if matches_to_cache:
        cache_path = _get_task_cache_path(files_to_process, task)
        logging.info(f"Updating cache with {len(matches_to_cache)} new, API-translated items.")
        update_cache(cache_path, task.name, matches_to_cache)


def _phase_6_write_back(all_processed_matches: List[TextMatch], task: TranslationTask):
    """Phase 6: Write all modified content back to files."""
    if task.output:
        precise_write_back(all_processed_matches, task)


def run_task(task: TranslationTask, config: GlocalConfig) -> List[TextMatch]:
    """
    Runs a single translation task by orchestrating a multi-phase workflow.

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
