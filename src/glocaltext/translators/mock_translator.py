import logging
from typing import Dict, List, Optional

from ..config import ProviderSettings
from ..models import TranslationResult
from .base import BaseTranslator


class MockTranslator(BaseTranslator):
    """
    A mock translator for testing purposes. It doesn't perform real translations.
    Instead, it prepends a '[MOCK]' prefix to each text.
    """

    def __init__(self, settings: ProviderSettings):
        """
        Initializes the Mock Translator.

        Args:
            settings: Provider-specific configurations. This provider currently
                      does not use any specific settings, but it is accepted
                      for interface consistency.
        """
        super().__init__(settings)

    def translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        debug: bool = False,
        prompts: Optional[Dict[str, str]] = None,
    ) -> List[TranslationResult]:
        """
        'Translates' a list of texts by prepending '[MOCK] ' to each.
        """
        _ = source_language
        _ = prompts
        if not texts:
            return []

        results: List[TranslationResult] = []
        for text in texts:
            mock_translation = f"[MOCK] {text}"
            results.append(
                TranslationResult(
                    translated_text=mock_translation,
                    tokens_used=len(text),  # Simulate token usage
                )
            )

        if debug:
            logging.info(f"MockTranslator processed {len(texts)} texts for target '{target_language}'.")

        return results

    def count_tokens(self, texts: List[str], prompts: Optional[Dict[str, str]] = None) -> int:
        """
        Simulates token counting for the mock translator.
        It returns the total number of characters in the texts, which is a simple
        but effective simulation for testing purposes.
        """
        _ = prompts  # Prompts are not used by this provider
        if not texts:
            return 0
        return sum(len(text) for text in texts)
