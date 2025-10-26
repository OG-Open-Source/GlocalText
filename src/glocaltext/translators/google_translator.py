# Implementation for the Google Translate API using deep-translator
from typing import Dict, List, Optional

from deep_translator import GoogleTranslator as DeepGoogleTranslator

from ..config import ProviderSettings
from ..models import TranslationResult
from .base import BaseTranslator


class GoogleTranslator(BaseTranslator):
    """Translator using the Google Translate API via the 'deep-translator' library.
    This does not require an API key for basic usage.
    """

    def __init__(self, settings: ProviderSettings):
        """
        Initializes the Google Translator.

        Args:
            settings: Provider-specific configurations. This provider currently
                      does not use any specific settings, but it is accepted
                      for interface consistency.
        """
        super().__init__(settings)
        # deep-translator handles the client setup internally.

    def translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: str | None = "auto",
        debug: bool = False,
        prompts: Dict[str, str] | None = None,
    ) -> List[TranslationResult]:
        """Translate a list of texts using deep-translator.

        Args:
            texts: A list of strings to translate.
            target_language: The target language code (e.g., 'zh-TW').
            source_language: The source language code (e.g., 'en'). Defaults to 'auto'.
            prompts: This argument is ignored by this translator.
            debug: This provider does not support debug mode. This argument is ignored.

        Returns:
            A list of TranslationResult objects.

        """
        # These arguments are part of the base class interface but are not used by this provider.
        _ = prompts
        _ = debug
        if not texts:
            return []

        try:
            # deep-translator can handle batch translation in a single call.
            translated_texts = DeepGoogleTranslator(source=source_language or "auto", target=target_language).translate_batch(texts)

            return [TranslationResult(translated_text=t) for t in translated_texts]

        except Exception as e:
            raise ConnectionError(f"deep-translator (Google) request failed: {e}")

    def count_tokens(self, texts: List[str], prompts: Optional[Dict[str, str]] = None) -> int:
        """
        Estimates the token count for Google Translate.
        This is a rough approximation as the underlying API does not expose token information.
        We assume an average of 4 characters per token.
        """
        _ = prompts  # Prompts are not used by this provider
        if not texts:
            return 0
        # Rough estimation: 4 characters per token.
        total_chars = sum(len(text) for text in texts)
        return total_chars // 4
