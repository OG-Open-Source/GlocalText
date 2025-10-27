"""Defines the base class for all translators."""

from abc import ABC, abstractmethod

from glocaltext.config import ProviderSettings
from glocaltext.models import TranslationResult


class BaseTranslator(ABC):
    """Abstract base class for all translator implementations."""

    def __init__(self, settings: ProviderSettings | None = None) -> None:
        """
        Initialize the translator with provider-specific settings.

        Args:
            settings: A Pydantic model containing provider-specific configurations.

        """
        self.settings = settings

    @abstractmethod
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
        Translate a list of texts.

        Args:
            texts: A list of strings to be translated.
            target_language: The target language code.
            source_language: The source language code (optional).
            debug: If True, enables debug logging.
            prompts: A dictionary of prompts to use for this translation.

        Returns:
            A list of TranslationResult objects.

        """
        raise NotImplementedError

    @abstractmethod
    def count_tokens(self, texts: list[str], prompts: dict[str, str] | None = None) -> int:
        """
        Calculate the total number of tokens that a list of texts will consume.

        This includes any prompt overhead.

        Args:
            texts: The list of texts to be measured.
            prompts: An optional dictionary of custom prompts that might affect token count.

        Returns:
            The total estimated token count for the API call.

        """
        raise NotImplementedError
