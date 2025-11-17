"""Utilities for cache management."""

import hashlib
import json
import logging
from pathlib import Path

from glocaltext import paths
from glocaltext.match_state import MatchLifecycle
from glocaltext.models import TextMatch
from glocaltext.types import TranslationTask

from .cache_policies import CachePolicyChain, SkippedMatchPolicy, TranslatedMatchPolicy

__all__ = [
    "_get_task_cache_path",
    "_load_cache",
    "_partition_matches_by_cache",
    "_should_cache_match",
    "_update_cache",
    "calculate_checksum",
]

logger = logging.getLogger(__name__)


def calculate_checksum(text: str) -> str:
    """Calculate the SHA-256 checksum of a given text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _get_task_cache_path(task: TranslationTask) -> Path:
    """
    Get the cache path for a task, respecting custom cache_path if provided.

    If task.cache_path is specified, it's treated as a directory path relative
    to the project root. Otherwise, uses the default .ogos/glocaltext/caches/ directory.

    The cache filename is always based on the task's UUID (task_id), not its name,
    ensuring stability even when the task name changes.
    """
    if task.cache_path:
        # User-specified custom cache directory (relative to project root)
        try:
            cache_dir = paths.find_project_root() / task.cache_path
        except FileNotFoundError:
            logger.warning("Could not determine project root. Falling back to default cache directory.")
            cache_dir = paths.get_cache_dir()
    else:
        # Default cache directory
        cache_dir = paths.get_cache_dir()

    paths.ensure_dir_exists(cache_dir)

    # Use task_id (UUID) as the filename for stability
    return cache_dir / f"{task.task_id}.json"


def _load_cache(cache_path: Path, task_id: str) -> dict[str, str]:
    """Safely load the cache for a specific task from the cache file."""
    logger.debug("Loading cache for task_id '%s' from: %s", task_id, cache_path)
    if not cache_path.exists():
        logger.debug("Cache file not found.")
        return {}
    try:
        # Open in binary mode and let json.load handle decoding from UTF-8 (with BOM support)
        with cache_path.open("rb") as f:
            full_cache = json.load(f)
        task_cache = full_cache.get(task_id, {})
        logger.debug("Loaded %d items from cache for task_id '%s'.", len(task_cache), task_id)
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read or parse cache file at %s.", cache_path)
        return {}
    else:
        return task_cache


def _update_cache(cache_path: Path, task_id: str, matches_to_cache: list[TextMatch]) -> None:
    """Update the cache file by merging new translations."""
    logger.debug(
        "Updating cache for task_id '%s' at: %s with %d new items.",
        task_id,
        cache_path,
        len(matches_to_cache),
    )
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        full_cache: dict[str, dict[str, str]] = {}
        if cache_path.exists():
            try:
                # Open in binary mode to let json.load handle BOMs and encoding.
                with cache_path.open("rb") as f:
                    full_cache = json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Cache file %s is corrupted or unreadable. A new one will be created.", cache_path)

        task_cache = full_cache.get(task_id, {})
        new_entries = {calculate_checksum(match.original_text): match.translated_text for match in matches_to_cache if match.translated_text is not None}

        # Log which entries will be overwritten (cache protection diagnostic)
        for checksum in new_entries:
            if checksum in task_cache:
                logger.warning("[CACHE OVERWRITE] Checksum %s will be updated\n  Old: '%s...'\n  New: '%s...'", checksum[:16], str(task_cache[checksum])[:80], str(new_entries[checksum])[:80])

        if new_entries:
            task_cache.update(new_entries)
            full_cache[task_id] = task_cache
            # Always write with UTF-8
            with cache_path.open("w", encoding="utf-8") as f:
                json.dump(full_cache, f, ensure_ascii=False, indent=4)
    except OSError:
        logger.exception("Could not write to cache file at %s", cache_path)


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
            match.lifecycle = MatchLifecycle.CACHED
            logger.debug("[CACHE HIT] Checksum=%s, Lifecycle set to 'CACHED'", checksum[:16])
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


def _should_cache_match(match: TextMatch) -> bool:
    """
    Determine if a match should be written to cache using policy chain.

    This function serves as a bridge to the CachePolicy strategy pattern,
    maintaining backward compatibility while enabling flexible cache logic.

    Cache Strategy:
    - Use policy chain for intelligent decision-making
    - Policies check lifecycle, skip_reason, and other attributes
    - See CachePolicy classes for detailed logic

    Args:
        match: The TextMatch to evaluate

    Returns:
        True if the match should be cached, False otherwise

    """
    # Must have translated_text to be cacheable (pre-filter)
    if match.translated_text is None:
        return False

    # Never re-cache already cached matches (pre-filter)
    if match.lifecycle == MatchLifecycle.CACHED:
        return False

    # Don't cache replaced matches - they're rule-driven, not translation-driven (pre-filter)
    if match.lifecycle == MatchLifecycle.REPLACED:
        return False

    # Use policy chain for remaining decisions
    policy_chain = CachePolicyChain(
        [
            TranslatedMatchPolicy(),
            SkippedMatchPolicy(),
        ]
    )

    decision = policy_chain.evaluate(match)
    logger.debug(
        "[CACHE DECISION] Match '%s...' -> %s (Reason: %s)",
        match.original_text[:40],
        "CACHE" if decision.should_cache else "SKIP",
        decision.reason,
    )

    return decision.should_cache or False
