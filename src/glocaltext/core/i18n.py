import os
import re2 as re
import typing
import logging
import xxhash
from pathlib import Path
from typing import Dict, Set, List, Tuple
from collections import defaultdict

from pydantic import BaseModel, Field

from glocaltext.core.config import I18nConfig
from glocaltext.utils.debug_logger import DebugLogger
from glocaltext.utils.hashing import normalize_and_hash

logger = logging.getLogger(__name__)


class ExtractedString(BaseModel):
    """
    Represents a single string extracted from a source file.
    """

    hash_id: str = Field(..., description="The xxhash of the text (seed=0)")
    artifact_hash: str = Field(
        ..., description="The hash used for intermediate artifacts (*#...#*)"
    )
    protection_hash: str = Field(
        ..., description="The hash used for protecting text in logs ({{...}})"
    )
    text: str = Field(..., description="The actual extracted string")
    text_to_translate: str = Field(
        ..., description="Text with protected parts replaced by placeholders"
    )
    full_match: str = Field(..., description="The full regex match, e.g., _('text')")
    source_file: Path = Field(..., description="The file where it was found")
    line_number: int = Field(..., description="The line number where it was found")
    protected_map: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of temporary placeholders to original protected content",
    )
    protected_values_in_order: List[str] = Field(
        default_factory=list,
        description="A list of the original protected values in the order they appeared in the source string.",
    )


class I18nProcessor:
    """
    Handles the extraction of user-visible strings from source files.
    """

    def __init__(
        self,
        config: I18nConfig,
        project_path: Path,
        debug_logger: DebugLogger,
    ):
        """
        Initializes the processor with the given configuration and project path.

        Args:
            config: The internationalization configuration.
            project_path: The root path of the project to scan.
            debug_logger: The logger for debug information.
        """
        self.config = config
        self.project_path = project_path
        self.debug_logger = debug_logger
        self.extracted_strings: Dict[str, ExtractedString] = {}
        self._processed_files: Set[Path] = set()
        logger.debug("I18nProcessor initialized")

    def get_processed_files(self) -> Set[Path]:
        """Returns the set of all file paths that were processed."""
        return self._processed_files

    def exclude_files_from_processing(
        self, relative_paths_to_exclude: Set[str], base_path: Path
    ):
        """
        Removes a set of files from the internal list of processed files.
        """
        absolute_paths_to_exclude = {
            base_path.resolve() / p for p in relative_paths_to_exclude
        }

        initial_count = len(self._processed_files)
        self._processed_files -= absolute_paths_to_exclude
        final_count = len(self._processed_files)

        if initial_count > final_count:
            logger.debug(
                f"Excluded {initial_count - final_count} protected files from processing."
            )

    def run(self) -> Dict[str, ExtractedString]:
        """
        Scans source files, extracts strings, and returns them.

        Returns:
            A dictionary mapping unique string hash IDs to ExtractedString objects.
        """
        logger.debug("Running I18nProcessor...")
        # 1. File Scanning (relative to project_path, no chdir)
        include_patterns = self.config.source.include
        logger.debug(f"Include patterns: {include_patterns}")
        files_to_scan: Set[Path] = {
            p.resolve()
            for pattern in include_patterns
            for p in self.project_path.rglob(pattern)
        }
        logger.debug(f"Found {len(files_to_scan)} files to scan from include patterns.")

        exclude_patterns = self.config.source.exclude
        logger.debug(f"Exclude patterns: {exclude_patterns}")
        files_to_ignore: Set[Path] = {
            p.resolve()
            for pattern in exclude_patterns
            for p in self.project_path.rglob(pattern)
        }
        logger.debug(
            f"Found {len(files_to_ignore)} files to ignore from exclude patterns."
        )

        filtered_files = files_to_scan - files_to_ignore
        logger.debug(f"Files after inclusion/exclusion: {len(filtered_files)}")

        # Exclude files within any .ogos directory
        self._processed_files = {p for p in filtered_files if ".ogos" not in p.parts}
        logger.debug(
            f"Final file count after excluding '.ogos' directories: {len(self._processed_files)}"
        )
        self.debug_logger.start_phase("SCANNING")
        self.debug_logger.add_phase_summary(
            f"Found {len(files_to_scan)} files from include patterns."
        )
        self.debug_logger.add_phase_summary(
            f"Found {len(files_to_ignore)} files to ignore from exclude patterns."
        )
        self.debug_logger.add_phase_summary(
            f"Filtered down to {len(filtered_files)} files."
        )
        self.debug_logger.add_phase_summary(
            f"Final file count after excluding '.ogos' directories: {len(self._processed_files)}"
        )
        logger.info(f"Found {len(self._processed_files)} files to process.")

        # 2. String Extraction
        self.debug_logger.start_phase("EXTRACTION")
        self._process_files()

        # 3. Generate intermediate files with hashes
        self._generate_intermediate_files()

        return self.extracted_strings

    def _process_files(self):
        """Iterates through files and orchestrates the extraction process."""
        for file_path in self._processed_files:
            logger.debug(f"Processing file: {file_path}")
            self.debug_logger.start_file_unit(file_path)
            try:
                content = file_path.read_text(encoding="utf-8")
                self._extract_and_process_strings_from_file(file_path, content)
            except (IOError, UnicodeDecodeError) as e:
                logger.error(f"Error processing file {file_path}: {e}")
            finally:
                self.debug_logger.end_file_unit()

        logger.info(f"Extracted {len(self.extracted_strings)} unique strings.")

    def _extract_and_process_strings_from_file(self, file_path: Path, content: str):
        """Extracts, filters, protects, and stores strings from a single file's content."""
        for capture_rule in self.config.capture_rules:
            for match in re.finditer(capture_rule.pattern, content):
                try:
                    extracted_text = match.group(capture_rule.capture_group)
                    line_number = content.count("\n", 0, match.start()) + 1
                    hash_id = normalize_and_hash(extracted_text, seed=0)
                    location = (
                        f"{file_path.relative_to(self.project_path)}:{line_number}"
                    )

                    source_info = {
                        "source_text": extracted_text,
                        "location": location,
                    }
                    self.debug_logger.log_string_action(
                        hash_id,
                        "Extract",
                        f"Rule: {capture_rule.pattern}, Full Match: '{match.group(0)}'",
                        source_info,
                    )

                    if self._is_string_ignored(hash_id, extracted_text):
                        self.debug_logger.set_string_status(hash_id, "IGNORED")
                        continue

                    text_to_translate, protected_map, protected_values_in_order = (
                        self._apply_protection(hash_id, extracted_text)
                    )

                    self._store_string(
                        hash_id,
                        extracted_text,
                        text_to_translate,
                        match.group(0),
                        file_path,
                        line_number,
                        protected_map,
                        protected_values_in_order,
                    )
                    self.debug_logger.set_string_status(hash_id, "PROCESSED")

                except IndexError:
                    logger.error(
                        f"Capture group {capture_rule.capture_group} not found for pattern {capture_rule.pattern}"
                    )

    def _is_string_ignored(self, hash_id: str, text: str) -> bool:
        """Checks if a string matches any of the ignore rules."""
        for ignore_rule in self.config.ignore_rules:
            if re.fullmatch(ignore_rule.pattern, text):
                self.debug_logger.log_string_action(
                    hash_id, "Ignore", f"Matched rule: {ignore_rule.pattern}"
                )
                return True
        return False

    def _apply_protection(
        self, hash_id: str, text: str
    ) -> Tuple[str, Dict[str, str], List[str]]:
        """Applies protection rules to a string, returning the modified text and protection maps."""
        protected_map: Dict[str, str] = {}
        protected_values_in_order: List[str] = []
        text_to_translate = text

        if not self.config.protection_rules:
            return text, protected_map, protected_values_in_order

        combined_pattern = "|".join(
            rule.pattern for rule in self.config.protection_rules
        )

        def replace_callback(match_obj):
            part = match_obj.group(0)
            if part not in protected_values_in_order:
                protected_values_in_order.append(part)

            protection_hash_hex = normalize_and_hash(part, seed=1)
            protection_hash_int = int(protection_hash_hex, 16)
            placeholder = f"{{{{{protection_hash_int}}}}}"

            if placeholder not in protected_map:
                protected_map[placeholder] = part
                self.debug_logger.log_string_action(
                    hash_id, "Protect", f"'{part}' -> {placeholder}"
                )
            return placeholder

        text_to_translate = re.sub(combined_pattern, replace_callback, text)

        return text_to_translate, protected_map, protected_values_in_order

    def _store_string(
        self,
        hash_id: str,
        text: str,
        text_to_translate: str,
        full_match: str,
        source_file: Path,
        line_number: int,
        protected_map: Dict[str, str],
        protected_values_in_order: List[str],
    ):
        """Creates and stores an ExtractedString object if it's unique."""
        if hash_id in self.extracted_strings:
            self.debug_logger.log_string_action(
                hash_id, "Store", "Duplicate string found, skipping."
            )
            return

        artifact_hash = f"*#{hash_id}#*"
        self.extracted_strings[hash_id] = ExtractedString(
            hash_id=hash_id,
            artifact_hash=artifact_hash,
            protection_hash="",  # Obsolete
            text=text,
            text_to_translate=text_to_translate,
            full_match=full_match,
            source_file=source_file,
            line_number=line_number,
            protected_map=protected_map,
            protected_values_in_order=protected_values_in_order,
        )
        self.debug_logger.log_string_action(
            hash_id,
            "Store",
            f"New unique string added to queue. Text to translate: '{text_to_translate}'",
        )

    def _generate_intermediate_files(self):
        """Generates the .i18n artifact files with placeholders."""

        logger.debug("Generating intermediate files with hashes...")
        artifacts_dir = self.project_path / ".ogos" / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        strings_by_file = defaultdict(list)
        for s in self.extracted_strings.values():
            strings_by_file[s.source_file].append(s)

        for file_path, strings in strings_by_file.items():
            if not file_path.exists():
                logger.warning(
                    f"Source file {file_path} not found, skipping intermediate file generation."
                )
                continue

            try:
                content = file_path.read_text(encoding="utf-8")

                # Sort by line number in reverse to avoid messing up line numbers during replacement
                strings.sort(key=lambda s: s.line_number, reverse=True)

                for s in strings:
                    # A simple string replacement might be too broad.
                    # A more robust approach would be to replace based on line and column,
                    # but for now, this is a good approximation.
                    if s.full_match in content:
                        new_full_match = s.full_match.replace(s.text, s.artifact_hash)
                        content = content.replace(s.full_match, new_full_match, 1)

                intermediate_file_path = artifacts_dir / f"{file_path.name}.i18n"
                intermediate_file_path.write_text(content, encoding="utf-8")
                logger.debug(
                    f"  - Wrote intermediate file for {file_path.name} to {intermediate_file_path}"
                )

            except (IOError, UnicodeDecodeError) as e:
                logger.error(f"Error generating intermediate file for {file_path}: {e}")

    def extract_raw_strings_from_file(self, file_path: Path) -> typing.List[str]:
        """
        Extracts a list of raw strings from a single file based on the configured rules.
        """
        raw_strings = []
        logger.debug(f"Extracting raw strings from: {file_path}")
        try:
            content = file_path.read_text(encoding="utf-8")

            # Note: sync does not currently use ignore_rules as it compares source and localized files directly.
            # This could be a future enhancement if needed.
            for rule in self.config.capture_rules:
                for match in re.finditer(rule.pattern, content):
                    try:
                        extracted_text = match.group(rule.capture_group)
                        raw_strings.append(extracted_text)
                    except IndexError:
                        logger.error(
                            f"Capture group {rule.capture_group} not found for pattern {rule.pattern} in file {file_path}"
                        )
        except (IOError, UnicodeDecodeError) as e:
            logger.error(f"Error reading file {file_path}: {e}")
        return raw_strings

    def get_source_text(self, hash_id: str) -> typing.Optional[str]:
        """
        Retrieves the original source text for a given hash ID.

        Args:
            hash_id: The hash ID of the string to retrieve.

        Returns:
            The source text, or None if not found.
        """
        entry = self.extracted_strings.get(hash_id)
        return entry.text if entry else None

    def get_file_hash(self, file_path: Path) -> str:
        """Computes the xxhash of a file's content."""
        hasher = xxhash.xxh64()
        with open(file_path, "rb") as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
