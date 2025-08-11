import logging
import re2 as re
from typing import List, Optional, Dict
from deep_translator import GoogleTranslator
from .base import Translator

logger = logging.getLogger(__name__)


class DeepTranslator(Translator):
    def __init__(self):
        logger.debug("Initializing DeepTranslator (Google).")
        self.placeholders: Dict[str, str] = {}
        self.placeholder_counter = 0

    def _protect_callback(self, match):
        """Callback to replace a placeholder with a unique token."""
        placeholder_key = f"__p_{self.placeholder_counter}__"
        self.placeholders[placeholder_key] = match.group(0)
        self.placeholder_counter += 1
        return placeholder_key

    def _protect_placeholders(self, text: str) -> str:
        """
        Replaces placeholders with unique, translation-safe tokens.
        This avoids sending HTML-like structures to the translator.
        """
        self.placeholders = {}
        self.placeholder_counter = 0
        protected_text = re.sub(r"(\{\{\s*\d+\s*\}\})", self._protect_callback, text)
        logger.debug(f"Protecting placeholders: '{text}' -> '{protected_text}'")
        return protected_text

    def _unprotect_placeholders(self, text: str) -> str:
        """Restores original placeholders from the unique tokens."""
        original_text = text
        unprotected_text = text
        for key, value in self.placeholders.items():
            # Use simple replacement, which is safer and faster.
            # Add spaces around the key to avoid accidental replacements if the
            # key appears as a substring in a word.
            unprotected_text = unprotected_text.replace(key, value)

        logger.debug(
            f"Unprotecting placeholders: '{original_text}' -> '{unprotected_text}'"
        )
        return unprotected_text.strip()

    def translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]] = None,
    ) -> List[str]:

        if glossary:
            logger.warning(
                "DeepTranslator does not support glossaries. The glossary will be ignored."
            )

        if source_language == target_language:
            return texts

        translated_texts = []
        for text in texts:
            try:
                # Protect placeholders before sending to Google
                protected_text = self._protect_placeholders(text)
                logger.debug(f"[Google] Inp (Protected): {protected_text}")

                translated_protected_text = GoogleTranslator(
                    source=source_language, target=target_language
                ).translate(protected_text)

                # Unprotect placeholders after receiving from Google
                final_text = self._unprotect_placeholders(translated_protected_text)
                logger.debug(f"[Google] Oup (Final): {final_text}")
                translated_texts.append(final_text)

            except Exception as e:
                logger.error(f"Google Translate failed for text: '{text}'. Error: {e}")
                translated_texts.append(text)  # Return original text on failure
        return translated_texts
