"""A mock translator for testing purposes."""

import logging

from glocaltext.config import ProviderSettings

from .base import BaseTranslator, TranslationResult

logger = logging.getLogger(__name__)


class MockTranslatorError(Exception):
    """Custom exception for mock translator errors."""


class MockTranslator(BaseTranslator):
    """
    A mock translator for testing that prepends a '[MOCK]' prefix.

    It can also be configured to raise an exception for testing error handling.
    """

    def __init__(self, settings: ProviderSettings, *, return_error: bool = False) -> None:
        """
        Initialize the Mock Translator.

        Args:
            settings: Provider-specific configurations (ignored).
            return_error: If True, the translate method will raise an exception.

        """
        super().__init__(settings)
        self.return_error = return_error

    def translate(
        self,
        texts: list[str],
        target_language: str,
        source_language: str | None = None,
        *,
        debug: bool = False,
        prompts: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """
        Prepend '[MOCK] ' to each text to simulate translation.

        Raises:
            Exception: If `return_error` was set to True during initialization.

        """
        _ = source_language
        _ = prompts

        if self.return_error:
            msg = "Mock translator was configured to fail."
            raise MockTranslatorError(msg)

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
            logger.debug(
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
