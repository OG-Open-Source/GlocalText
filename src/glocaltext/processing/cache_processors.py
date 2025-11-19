"""Cache-related processors."""

import json
import logging

from glocaltext import paths
from glocaltext.models import ExecutionContext

from .base import Processor
from .cache_utils import (
    _get_task_cache_path,
    _load_cache,
    _partition_matches_by_cache,
    _should_cache_match,
    _update_cache,
    calculate_checksum,
)

__all__ = ["CacheProcessor", "CacheUpdateProcessor"]

logger = logging.getLogger(__name__)


class CacheProcessor(Processor):
    """Phase 3: Check cache for remaining matches if in incremental mode."""

    def process(self, context: ExecutionContext) -> None:
        """Check the cache for translations and partition the matches."""
        if not context.is_incremental:
            context.matches_to_translate = context.all_matches
            return

        try:
            cache_path = _get_task_cache_path(context.task, context.project_root)
            paths.ensure_dir_exists(cache_path.parent)
            cache = _load_cache(cache_path, context.task.task_id)
        except FileNotFoundError:
            logger.warning("Could not determine cache path because project root was not found. Proceeding without cache.")
            context.matches_to_translate = context.all_matches
            return

        # Partition all captured matches, not just a subset.
        matches_to_translate, cached_matches = _partition_matches_by_cache(context.all_matches, cache)

        context.matches_to_translate = matches_to_translate
        context.cached_matches = cached_matches

        unique_texts_count = len({m.original_text for m in context.matches_to_translate})
        logger.debug("Found %d cached translations.", len(context.cached_matches))
        logger.info("%d unique texts require new translation.", unique_texts_count)


class CacheUpdateProcessor(Processor):
    """Phase 5: Update the cache with newly translated matches."""

    def process(self, context: ExecutionContext) -> None:
        """Update the cache with new API-translated items."""
        if context.is_dry_run:
            logger.debug("[DRY RUN] Skipping cache update.")
            return

        if not context.is_incremental:
            return

        # Filter matches for caching based on lifecycle and skip reason
        # - CACHED: Already in cache, don't re-write
        # - REPLACED: Modified by replace rules, don't cache
        # - SKIPPED with skip_reason.category == "rule": User rules may change, don't cache
        # - SKIPPED with skip_reason.category in ("optimization", "validation"): Should cache for performance
        matches_to_cache = [m for m in context.matches_to_translate if _should_cache_match(m)]

        if not matches_to_cache:
            return

        try:
            cache_path = _get_task_cache_path(context.task, context.project_root)

            # Load existing cache to verify checksums
            try:
                existing_cache = _load_cache(cache_path, context.task.task_id)
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Could not load existing cache for verification: %s. Proceeding with update.", e)
                existing_cache = {}

            # Extra verification: filter out matches whose checksum already exists in cache
            verified_matches = []
            for match in matches_to_cache:
                checksum = calculate_checksum(match.original_text)
                if checksum in existing_cache:
                    # This checksum is already in cache - skip to protect manual edits
                    logger.warning("[CACHE PROTECTION] Checksum %s already in cache. Skipping update to protect manual edits.", checksum[:16])
                    continue
                verified_matches.append(match)

            if verified_matches:
                logger.debug("Updating cache with %d new, API-translated items.", len(verified_matches))
                _update_cache(cache_path, context.task.task_id, verified_matches)
        except FileNotFoundError:
            logger.exception("Could not update cache because project root was not found.")
