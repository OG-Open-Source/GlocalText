import hashlib
import json
import logging
import os
from glob import glob
from pathlib import Path
from typing import Dict, Iterable, List

import regex
from google.generativeai.generative_models import GenerativeModel

from .config import BatchOptions, GlocalConfig, TranslationTask
from .models import TextMatch
from .translate import apply_terminating_rules, process_matches
from .translators.base import BaseTranslator

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


def create_token_based_batches(matches: List[TextMatch], model: GenerativeModel, batch_options: BatchOptions) -> List[List[TextMatch]]:
    if not batch_options.enabled:
        return [matches] if matches else []
    batches: List[List[TextMatch]] = []
    current_batch: List[TextMatch] = []
    current_batch_tokens = 0
    for match in matches:
        match_tokens = model.count_tokens(match.original_text).total_tokens
        if current_batch and ((current_batch_tokens + match_tokens > batch_options.max_tokens_per_batch) or (len(current_batch) >= batch_options.batch_size)):
            batches.append(current_batch)
            current_batch = []
            current_batch_tokens = 0
        current_batch.append(match)
        current_batch_tokens += match_tokens
    if current_batch:
        batches.append(current_batch)
    logging.info(f"Created {len(batches)} batches based on token limits.")
    return batches


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
            for match in regex.finditer(rule_pattern, content, regex.MULTILINE):
                if match.groups():
                    matches.append(
                        TextMatch(
                            original_text=match.group(1),
                            source_file=file_path,
                            span=match.span(1),
                            task_name=task.name,
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
            ext=file_path.suffix,
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


def precise_write_back(matches: List[TextMatch], task: TranslationTask):
    if not matches:
        logging.info("No matches with translated text to write back.")
        return
    matches_by_file: Dict[Path, List[TextMatch]] = {}
    for match in matches:
        if match.translated_text is not None:
            matches_by_file.setdefault(match.source_file, []).append(match)
    logging.info(f"Writing back translations for {len(matches_by_file)} files.")
    for file_path, file_matches in matches_by_file.items():
        try:
            file_matches.sort(key=lambda m: m.span[0], reverse=True)
            logging.info(f"Processing {file_path}: {len(file_matches)} translations to apply.")
            original_newline = _detect_newline(file_path)
            content = file_path.read_text("utf-8")
            for match in file_matches:
                start, end = match.span
                translated_text = match.translated_text or match.original_text
                content = content[:start] + translated_text + content[end:]
            output_path = _get_output_path(file_path, task)
            if output_path:
                _write_modified_content(output_path, content, newline=original_newline)
            else:
                logging.warning(f"Output path is not defined for a non-in-place task. Skipping write-back for {file_path}.")
        except OSError as e:
            logging.error(f"Could not read or write file {file_path}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during write-back for {file_path}: {e}")


def run_task(task: TranslationTask, translators: Dict[str, BaseTranslator], config: GlocalConfig) -> List[TextMatch]:
    """
    Runs a single translation task with a robust, cache-aware workflow.
    """
    # Phase 1: Capture
    files_to_process = list(_find_files(task))
    all_matches = capture_text_matches(task, config, files_to_process)

    # Phase 2: Apply Terminating Rules (e.g., skip, replace)
    remaining_matches, terminated_matches = apply_terminating_rules(all_matches, task)
    logging.info(f"Task '{task.name}': {len(terminated_matches)} matches handled by terminating rules.")

    # Phase 3: Check Cache for remaining matches
    matches_to_translate: List[TextMatch] = []
    cached_matches: List[TextMatch] = []
    if task.incremental:
        logging.info(f"Task '{task.name}': Running in incremental mode. Checking cache...")
        cache_path = _get_task_cache_path(files_to_process, task)
        cache = load_cache(cache_path, task.name)
        logging.info(f"Loaded {len(cache)} items from cache for task '{task.name}'.")
        for match in remaining_matches:
            checksum = calculate_checksum(match.original_text)
            if checksum in cache:
                match.translated_text = cache[checksum]
                match.provider = "cached"
                cached_matches.append(match)
            else:
                matches_to_translate.append(match)
        logging.info(f"Found {len(cached_matches)} cached translations.")
        logging.info(f"{len(matches_to_translate)} texts require new translation.")
    else:
        logging.info(f"Task '{task.name}': Running in full translation mode (cache is ignored).")
        matches_to_translate = remaining_matches

    # Phase 4: Pre-process & Translate via API
    if matches_to_translate:
        logging.info(f"Processing {len(matches_to_translate)} matches for API translation.")
        process_matches(matches_to_translate, translators, task, config)

    # Phase 5: Update Cache
    if task.incremental:
        # THE DEFINITIVE FIX:
        # Filter the list that went to the API and only take items that were successfully translated by a provider.
        # Exclude items that were handled by terminating rules (provider='rule' or 'skipped') or were found in the cache.
        matches_to_actually_cache = [m for m in matches_to_translate if m.translated_text is not None and m.provider not in ("cached", "rule", "skipped")]
        if matches_to_actually_cache:
            cache_path = _get_task_cache_path(files_to_process, task)
            logging.info(f"Updating cache with {len(matches_to_actually_cache)} new, API-translated items.")
            update_cache(cache_path, task.name, matches_to_actually_cache)

    # Phase 6: Combine & Write Back
    # The final set for write-back includes all categories, ensuring everything is written correctly.
    final_matches = terminated_matches + cached_matches + matches_to_translate
    if task.output:
        precise_write_back(final_matches, task)

    return final_matches
