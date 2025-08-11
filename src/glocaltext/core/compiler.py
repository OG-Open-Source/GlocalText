import pathlib
import shutil
import typing
from typing import Set
import logging
from collections import defaultdict

from glocaltext.core.config import L10nConfig
from glocaltext.core.i18n import I18nProcessor
from glocaltext.core.cache import TranslationCache
from glocaltext.utils.debug_logger import DebugLogger

Path = pathlib.Path
Dict = typing.Dict
List = typing.List

logger = logging.getLogger(__name__)


class Compiler:
    """
    Compiles translated strings back into a mirrored directory structure,
    ensuring all source files are present in the output.
    """

    def __init__(
        self,
        config: L10nConfig,
        cache: TranslationCache,
        i18n_processor: I18nProcessor,
        debug_logger: DebugLogger,
    ):
        """
        Initializes the Compiler.

        Args:
            config: The localization configuration.
            cache: The TranslationCache object containing all translations.
            i18n_processor: The I18nProcessor instance to get file lists and source text from.
            debug_logger: The logger for debug information.
        """
        self.config = config
        self.cache = cache
        self.i18n_processor = i18n_processor
        self.debug_logger = debug_logger
        logger.debug("Compiler initialized")

    def run(self, project_path: Path):
        """
        Executes the compilation process, creating a full directory mirror.

        Args:
            project_path: The root path of the project.
        """
        logger.debug("Starting compiler run...")
        localized_path = project_path / ".ogos" / "localized"
        logger.debug(f"Output directory set to: {localized_path}")

        # 1. Get all target languages from the cache
        target_languages = self.cache.get_target_languages()
        source_language = self.config.translation_settings.source_lang
        if source_language in target_languages:
            target_languages.remove(source_language)

        logger.debug(f"Target languages for compilation: {target_languages}")

        # 2. Group all extracted strings by their source file
        strings_by_file = defaultdict(list)
        for extracted_string in self.i18n_processor.extracted_strings.values():
            strings_by_file[extracted_string.source_file].append(extracted_string)

        # 3. Iterate through each language and compile
        self.debug_logger.start_phase("COMPILATION")
        for lang_code in target_languages:
            localized_lang_path = localized_path / lang_code
            logger.info(f"Processing language: {lang_code}")

            # Create a clean copy of the project for this language
            shutil.copytree(
                project_path,
                localized_lang_path,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".ogos", ".git"),
            )
            logger.debug(f"Copied project structure to {localized_lang_path}")

            # 4. Apply translations file by file
            for source_file, strings in strings_by_file.items():
                try:
                    relative_path = source_file.relative_to(project_path.resolve())
                    target_file = localized_lang_path / relative_path
                    logger.debug(f"  Applying translations to '{target_file}'")

                    if not target_file.exists():
                        logger.warning(f"    Target file not found, skipping.")
                        continue

                    content = target_file.read_text(encoding="utf-8")

                    replacements_made = 0

                    for s in strings:
                        # The cache now contains the final, fully restored translation
                        final_translation = self.cache.get_translation(
                            s.hash_id, lang_code
                        )
                        if final_translation:
                            new_full_match = s.full_match.replace(
                                s.text, final_translation
                            )

                            if s.full_match in content:
                                content = content.replace(
                                    s.full_match, new_full_match, 1
                                )
                                replacements_made += 1
                                self.debug_logger.log_compilation_details(
                                    lang_code,
                                    str(relative_path),
                                    s.full_match,
                                    new_full_match,
                                )
                            else:
                                logger.warning(
                                    f"    Could not find full_match '{s.full_match}' for hash '{s.hash_id}' in {target_file}"
                                )

                    if replacements_made > 0:
                        target_file.write_text(content, encoding="utf-8")
                        logger.debug(
                            f"  Finished writing file with {replacements_made} replacements."
                        )

                except (FileNotFoundError, UnicodeDecodeError, ValueError) as e:
                    logger.error(
                        f"Error processing file {source_file} for language {lang_code}: {e}"
                    )
                    continue
        logger.info("Compiler run finished.")
