"""Translator implementation using the Google Translate API."""
# Implementation for the Google Translate API using deep-translator

from deep_translator import GoogleTranslator as DeepGoogleTranslator

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult

from .base import BaseTranslator


class GoogleTranslator(BaseTranslator):
    """A translator using the Google Translate API via the 'deep-translator' library."""

    def __init__(self, settings: ProviderSettings) -> None:
        """
        Initialize the Google Translator.

        Args:
            settings: Provider-specific configurations, which are ignored by this provider.

        """
        super().__init__(settings)
        # deep-translator handles the client setup internally.

    def translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None = "auto",
        *,
        debug: bool = False,
        prompts: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """
        Translate a list of texts using deep-translator.

        Args:
            texts: A list of strings to translate.
            target_language: The target language code (e.g., 'zh-TW').
            source_language: The source language code (e.g., 'en'). Defaults to 'auto'.
            debug: This provider does not support debug mode and ignores this argument.
            prompts: This argument is ignored by this translator.


        Returns:
            A list of TranslationResult objects.

        Raises:
            ConnectionError: If the translation request fails.

        """
        _ = prompts
        _ = debug
        if not texts:
            return []

        try:
            # deep-translator can handle batch translation in a single call.
            translated_texts = DeepGoogleTranslator(source=source_language or "auto", target=target_language).translate_batch(texts)
            return [TranslationResult(translated_text=t) for t in translated_texts]
        except Exception as e:
            msg = f"deep-translator (Google) request failed: {e}"
            raise ConnectionError(msg) from e

    def count_tokens(self, texts: list[str], prompts: dict[str, str] | None = None) -> int:
        """
        Estimate the token count for Google Translate.

        This is a rough approximation, assuming 4 characters per token.
        """
        _ = prompts  # Prompts are not used by this provider
        if not texts:
            return 0
        # Rough estimation: 4 characters per token.
        total_chars = sum(len(text) for text in texts)
        return total_chars // 4
