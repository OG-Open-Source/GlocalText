"""A mock translator for testing purposes."""

import logging

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult

from .base import BaseTranslator

logger = logging.getLogger(__name__)


class MockTranslator(BaseTranslator):
    """A mock translator for testing that prepends a '[MOCK]' prefix."""

    def __init__(self, settings: ProviderSettings) -> None:
        """
        Initialize the Mock Translator.

        Args:
            settings: Provider-specific configurations (ignored).

        """
        super().__init__(settings)

    def translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None = None,
        *,
        debug: bool = False,
        prompts: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """Prepend '[MOCK] ' to each text to simulate translation."""
        _ = source_language
        _ = prompts
        if not texts:
            return []

        results: list[TranslationResult] = []
        for text in texts:
            mock_translation = f"[MOCK] {text}"
            results.append(
                TranslationResult(
                    translated_text=mock_translation,
                    tokens_used=len(text),  # Simulate token usage
                ),
            )

        if debug:
            logger.info(
                "MockTranslator processed %d texts for target '%s'.",
                len(texts),
                target_language,
            )

        return results

    def count_tokens(self, texts: list[str], prompts: dict[str, str] | None = None) -> int:
        """Simulate token counting by returning the total character count."""
        _ = prompts  # Prompts are not used by this provider
        if not texts:
            return 0
        return sum(len(text) for text in texts)
