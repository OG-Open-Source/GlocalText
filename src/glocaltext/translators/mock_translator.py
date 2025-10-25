import logging
from typing import Dict, List, Optional

from ..models import TranslationResult
from .base import BaseTranslator


class MockTranslator(BaseTranslator):
    """
    A mock translator for testing purposes. It doesn't perform real translations.
    Instead, it prepends a '[MOCK]' prefix to each text.
    """

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
