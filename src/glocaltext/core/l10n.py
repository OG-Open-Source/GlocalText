# glocaltext/core/l10n.py

"""
The L10nProcessor orchestrates the entire localization (l10n) process.
"""
import logging
import re2 as re
from typing import Dict, Set, List, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.text import Text

from glocaltext.core.config import L10nConfig
from glocaltext.core.i18n import I18nProcessor, ExtractedString
from glocaltext.core.cache import TranslationCache, CacheEntry, TranslationValue
from glocaltext.core.postprocessor import PostProcessor
from glocaltext.core.translators.base import Translator
from glocaltext.core.translators.gemini import GeminiTranslator
from glocaltext.core.translators.deep_translator import DeepTranslator
from glocaltext.core.translators.openai import OpenAITranslator
from glocaltext.core.translators.ollama import OllamaTranslator
from glocaltext.utils.debug_logger import DebugLogger

logger = logging.getLogger(__name__)


class L10nProcessor:
    """
    The central coordinator for the localization process.
    """

    def __init__(
        self,
        config: L10nConfig,
        cache: TranslationCache,
        i18n_processor: I18nProcessor,
        debug_logger: DebugLogger,
    ):
        """
        Initializes the L10nProcessor.

        Args:
            config: The localization configuration.
            cache: The translation cache.
            i18n_processor: The I18nProcessor instance to access extracted string data.
            debug_logger: The logger for debug information.
        """
        self.config = config
        self.cache = cache
        self.i18n_processor = i18n_processor
        self.post_processor = PostProcessor(config)
        self.debug_logger = debug_logger
        self.console = Console()
        logger.debug("L10nProcessor initialized")

        # Translator Factory
        provider = self.config.translation_settings.provider
        provider_configs = self.config.provider_configs
        logger.debug(f"Translation provider specified: '{provider}'")

        if provider == "gemini":
            if not provider_configs or not provider_configs.gemini:
                raise ValueError("Gemini provider config is missing.")
            self.translator: Translator = GeminiTranslator(
                config=provider_configs.gemini
            )
        elif provider == "openai":
            if not provider_configs or not provider_configs.openai:
                raise ValueError("OpenAI provider config is missing.")
            self.translator: Translator = OpenAITranslator(
                **provider_configs.openai.dict()
            )
        elif provider == "google":
            self.translator: Translator = DeepTranslator()
        elif provider == "ollama":
            if not provider_configs or not provider_configs.ollama:
                raise ValueError("Ollama provider config is missing.")
            self.translator: Translator = OllamaTranslator(
                **provider_configs.ollama.dict()
            )
        else:
            raise ValueError(f"Unknown translation provider: {provider}")
        logger.debug(f"Translator '{self.translator.__class__.__name__}' initialized.")

    def _prompt_for_conflict_resolution(
        self,
        old_text: str,
        new_text: str,
        existing_translations: Dict[str, TranslationValue],
    ) -> str:
        """
        Displays an interactive prompt to the user to resolve a source text conflict.
        """
        self.console.print(
            Panel(
                "[bold yellow]Source String Conflict Detected[/bold yellow]",
                expand=False,
            )
        )

        old_panel = Panel(
            Text(old_text, style="red"), title="Old Source Text", border_style="red"
        )
        new_panel = Panel(
            Text(new_text, style="green"), title="New Source Text", border_style="green"
        )

        self.console.print(old_panel)
        self.console.print(new_panel)

        if existing_translations:
            trans_text = Text()
            for lang, trans_val in existing_translations.items():
                trans_text.append(
                    f"  [bold]{lang}:[/bold] {trans_val.get_translation()}\n"
                )
            self.console.print(
                Panel(trans_text, title="Existing Translations", border_style="cyan")
            )

        choice = Prompt.ask(
            "[bold]Choose an action:[/bold]\n"
            "  1. [green]Translate[/green] the new text (recommended)\n"
            "  2. [yellow]Keep[/yellow] the old translations with the new text\n"
            "  3. [red]Skip[/red] and do nothing for now",
            choices=["1", "2", "3"],
            default="1",
        )
        return {"1": "translate", "2": "keep", "3": "skip"}[choice]

    def _prompt_for_general_conflict_resolution(self, file_path: str) -> str:
        """
        Displays an interactive prompt for a general file conflict.
        """
        self.console.print(
            Panel(
                f"[bold red]Conflict Detected for:[/bold red]\n{file_path}",
                expand=False,
            )
        )
        choice = Prompt.ask(
            "[bold]Choose how to resolve:[/bold]\n"
            "  1. [green]Use Source[/green] version (re-translates the file)\n"
            "  2. [yellow]Use Localized[/yellow] version (updates translations with your changes)",
            choices=["1", "2"],
            default="1",
        )
        return {"1": "source", "2": "localized"}[choice]

    def process_and_translate(
        self, strings_to_translate: Dict[str, ExtractedString], *, force: bool
    ):
        """
        Processes a dictionary of strings that need translation.
        """
        if not strings_to_translate:
            logger.info("No new or updated strings to translate.")
            return

        logger.info(
            f"Processing {len(strings_to_translate)} strings for translation..."
        )

        # Ensure all strings to be translated have a cache entry
        self._ensure_cache_entries(strings_to_translate)

        # Group texts by target language to perform batch translations
        self.debug_logger.start_phase("TRANSLATION")
        for lang_code in self.config.translation_settings.target_lang:
            self._translate_for_language(strings_to_translate, lang_code, force)

    def _ensure_cache_entries(self, strings: Dict[str, ExtractedString]):
        """Ensures that every string to be processed has a basic entry in the cache."""
        for hash_id, extracted_string in strings.items():
            if not self.cache.get(hash_id):
                logger.debug(f"Creating new cache entry for {hash_id}.")
                entry = CacheEntry(
                    source_text=extracted_string.text,
                    # The full_match is stored with the source text for context
                    # but is not part of the CacheEntry model itself.
                    # We rely on the I18nProcessor to provide it during compilation.
                )
                self.cache.set(hash_id, entry)

    def _translate_for_language(
        self,
        all_strings: Dict[str, ExtractedString],
        lang_code: str,
        force: bool,
    ):
        """Translates a batch of strings for a single target language."""
        logger.debug(f"  -> Translating to '{lang_code}'")

        # Determine which texts actually need translation for this language
        texts_for_lang_batch = []
        hash_map = {}  # Maps batch index back to hash_id
        idx = 0
        for hash_id, extracted_string in all_strings.items():
            cached_entry = self.cache.get(hash_id)
            # Translate if forced, or if the language is missing in the cache entry
            if force or not cached_entry or lang_code not in cached_entry.translations:
                texts_for_lang_batch.append(extracted_string.text_to_translate)
                hash_map[idx] = hash_id
                idx += 1

        if not texts_for_lang_batch:
            logger.debug(
                f"    - All strings already have a '{lang_code}' translation. Skipping."
            )
            return

        logger.debug(f"    - Batch size for '{lang_code}': {len(texts_for_lang_batch)}")

        self.debug_logger.add_phase_summary(f"Target Language: {lang_code}")
        self.debug_logger.add_phase_summary(f"Batch Size: {len(texts_for_lang_batch)}")

        try:
            translated_templates = self.translator.translate(
                texts=texts_for_lang_batch,
                source_language=(
                    self.config.translation_settings.source_lang
                    if lang_code != self.config.translation_settings.source_lang
                    else "auto"
                ),
                target_language=lang_code,
                glossary=self.config.glossary,
            )

            for i, translated_template in enumerate(translated_templates):
                hash_id = hash_map[i]
                cached_entry = self.cache.get(hash_id)
                if cached_entry and translated_template:
                    # Restore protected parts immediately after translation
                    final_translation = translated_template
                    protected_map = all_strings[hash_id].protected_map

                    if protected_map:
                        final_translation = self._restore_protected_text(
                            translated_template, all_strings[hash_id]
                        )

                    self.debug_logger.log_translation_details(
                        hash_id, lang_code, translated_template, final_translation
                    )

                    logger.debug(
                        f"    - Translation successful for {hash_id}: '{final_translation}'"
                    )
                    new_trans_value = TranslationValue(text=final_translation)
                    cached_entry.translations[lang_code] = new_trans_value
                    self.cache.set(hash_id, cached_entry)
                else:
                    logger.warning(
                        f"    - Translation returned empty or invalid result for hash {hash_id} to {lang_code}. It will be retried on the next run."
                    )

            self.debug_logger.add_phase_summary(
                f"Successfully processed {len(translated_templates)} strings for {lang_code}."
            )

        except Exception as e:
            self.debug_logger.add_phase_summary(
                f"ERROR translating for {lang_code}: {e}"
            )
            logger.error(
                f"Failed to translate batch for {lang_code}: {e}", exc_info=True
            )

    def _restore_protected_text(
        self, translated_template: str, extracted_string: ExtractedString
    ) -> str:
        """
        Restores protected placeholders based on the original order of appearance.
        """
        hash_id = extracted_string.hash_id
        ordered_original_values = extracted_string.protected_values_in_order

        final_translation = translated_template
        # Find all placeholders in the translated text, e.g., {{...}}
        found_placeholders = re.findall(r"\{\{.*?\}\}", final_translation)

        if len(found_placeholders) != len(ordered_original_values):
            logger.error(
                f"Placeholder count mismatch for hash '{hash_id}'. Skipping restoration."
            )
            return translated_template  # Return template as-is to avoid corruption

        for i, placeholder_in_template in enumerate(found_placeholders):
            original_value = ordered_original_values[i]
            final_translation = final_translation.replace(
                placeholder_in_template, original_value, 1
            )

        return final_translation
