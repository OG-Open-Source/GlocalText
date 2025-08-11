import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Set
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ValidationError

# This needs to be imported for the new methods
from glocaltext.core.i18n import ExtractedString
from glocaltext.utils.debug_logger import DebugLogger

logger = logging.getLogger(__name__)


class TranslationValue(BaseModel):
    """
    Represents the translation details for a single language.
    """

    text: str = Field(
        ...,
        description="The current translation text.",
    )
    manual_override: Optional[str] = Field(
        None,
        description="A manual translation provided by a user, which takes precedence.",
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of the last modification (machine or manual).",
    )

    def get_translation(self) -> str:
        """
        Returns the definitive translation, prioritizing manual override.
        """
        return self.manual_override if self.manual_override is not None else self.text


class CacheEntry(BaseModel):
    """
    Represents a single entry in the translation cache, keyed by a content hash.
    It stores the original source text and a dictionary of its translations.
    """

    source_text: str = Field(..., description="The original source text.")
    translations: Dict[str, TranslationValue] = Field(
        default_factory=dict,
        description="A dictionary mapping language codes to their translation values.",
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class TranslationCache:
    """
    Manages a unified, JSON-based cache for translations to avoid redundant API calls.
    The cache structure is: {hash_id: CacheEntry}
    """

    def __init__(self, artifacts_path: Path, debug_logger: DebugLogger):
        """
        Initializes the TranslationCache.

        Args:
            artifacts_path: The path to the directory where artifacts are stored.
            debug_logger: An instance of the debug logger.
        """
        self.artifacts_path = artifacts_path
        self.debug_logger = debug_logger if debug_logger else DebugLogger(Path(), False)
        self.cache_file_path = self.artifacts_path / "translations.json"
        self.artifacts_path.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Cache file path initialized to: {self.cache_file_path}")
        self.cache: Dict[str, CacheEntry] = self._load()

    def _load(self) -> Dict[str, CacheEntry]:
        """
        Loads the cache from a single JSON file if it exists.
        """
        if not self.cache_file_path.exists():
            logger.debug("Cache file not found. Starting with an empty cache.")
            return {}

        logger.debug(f"Attempting to load cache from {self.cache_file_path}")
        try:
            with open(self.cache_file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Use Pydantic to parse the entire dictionary
                return {
                    hash_id: CacheEntry.parse_obj(entry_data)
                    for hash_id, entry_data in data.items()
                }
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Cache file is corrupted or has invalid data: {e}")
            # In case of corruption, it's safer to start fresh
            return {}

    def get(self, hash_id: str) -> Optional[CacheEntry]:
        """
        Retrieves a CacheEntry from the cache.
        """
        entry = self.cache.get(hash_id)
        logger.debug(f"Cache get for {hash_id}: {'Found' if entry else 'Miss'}")
        return entry

    def get_translation(self, hash_id: str, target_lang: str) -> Optional[str]:
        """
        Retrieves the definitive translation for a given string and language.
        """
        entry = self.get(hash_id)
        if not entry or target_lang not in entry.translations:
            return None
        return entry.translations[target_lang].get_translation()

    def set(self, hash_id: str, entry: CacheEntry):
        """
        Sets or updates an entry in the cache.
        """
        self.cache[hash_id] = entry
        logger.debug(f"Set/updated cache entry for {hash_id}")

    def save(self):
        """
        Saves the current state of the cache to a single JSON file.
        """
        logger.debug(
            f"Saving cache with {len(self.cache)} entries to {self.cache_file_path}"
        )

        class CustomEncoder(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, datetime):
                    return o.isoformat()
                if isinstance(o, BaseModel):
                    return o.dict()
                return super().default(o)

        try:
            # Serialize the entire cache dictionary
            cache_data = {
                hash_id: entry.dict() for hash_id, entry in self.cache.items()
            }
            with open(self.cache_file_path, "w", encoding="utf-8") as f:
                json.dump(
                    cache_data, f, indent=2, ensure_ascii=False, cls=CustomEncoder
                )
            logger.debug("Cache saved successfully.")
        except IOError as e:
            logger.error(f"Failed to save cache file to {self.cache_file_path}: {e}")

    def update_with_manual_overrides(self, overrides: Dict[Tuple[str, str], str]):
        """
        Applies a batch of manual overrides to the cache.
        """
        logger.debug(f"Updating cache with {len(overrides)} manual overrides.")
        for (hash_id, lang_code), translation in overrides.items():
            entry = self.get(hash_id)
            if entry and lang_code in entry.translations:
                entry.translations[lang_code].manual_override = translation
                entry.translations[lang_code].last_updated = datetime.now(timezone.utc)
                logger.debug(f"Set manual override for {hash_id}/{lang_code}")
            else:
                logger.warning(
                    f"Cannot set manual override for {hash_id}/{lang_code}: entry not found."
                )
        logger.debug("Finished applying manual overrides.")

    def update_manual_override(self, hash_id: str, lang_code: str, translation: str):
        """
        Sets or updates a manual override for a single translation entry.
        """
        entry = self.get(hash_id)
        if not entry:
            logger.warning(
                f"Cannot set manual override for hash '{hash_id}': entry not found."
            )
            return

        if lang_code not in entry.translations:
            # If the language entry doesn't exist, we can't set an override.
            # This might happen if a new language is added but not yet translated.
            logger.warning(
                f"Cannot set manual override for hash '{hash_id}': language '{lang_code}' not found in translations."
            )
            return

        entry.translations[lang_code].manual_override = translation
        entry.translations[lang_code].last_updated = datetime.now(timezone.utc)
        logger.debug(f"Set manual override for {hash_id}/{lang_code}")
        # Immediately save the change to ensure it persists.
        self.save()

    def get_all_cached_hashes(self) -> Set[str]:
        """Returns a set of all hash_ids currently in the cache."""
        return set(self.cache.keys())

    def get_target_languages(self) -> Set[str]:
        """Returns a set of all unique target language codes in the cache."""
        langs = set()
        for entry in self.cache.values():
            langs.update(entry.translations.keys())
        return langs

    def remove_entries_by_hash(self, hashes_to_remove: Set[str]):
        """Removes all cache entries associated with the given hashes."""
        if not hashes_to_remove:
            logger.debug("No dangling hashes to remove.")
            return

        log_details = [
            f"Attempting to remove {len(hashes_to_remove)} dangling entries from cache:"
        ]
        count = 0
        for hash_id in hashes_to_remove:
            if hash_id in self.cache:
                del self.cache[hash_id]
                log_details.append(f"  - Removed: {hash_id}")
                count += 1
        log_details.append(f"Successfully removed {count} entries.")
        self.debug_logger.log_step("3. Pruning Cache", "\n".join(log_details))
        logger.debug(f"Removed {count} dangling entries from the cache.")
