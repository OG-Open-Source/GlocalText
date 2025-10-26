# Defines the base class for all translators
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from ..config import ProviderSettings
from ..models import TranslationResult


class BaseTranslator(ABC):
    """Abstract base class for all translator implementations."""

    def __init__(self, settings: Optional[ProviderSettings] = None):
        """
        Initializes the translator with provider-specific settings.

        Args:
            settings: A Pydantic model containing provider-specific configurations.
                      This may include API keys, model names, retry policies, etc.
                      Each subclass is responsible for validating the settings it requires.
        """
        self.settings = settings

    @abstractmethod
    def translate(
        self,
        texts: List[str],
        target_language: str,
        source_language: str | None = None,
        debug: bool = False,
        prompts: Dict[str, str] | None = None,
    ) -> List[TranslationResult]:
        """Translates a list of texts.

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
    def count_tokens(self, texts: List[str], prompts: Optional[Dict[str, str]] = None) -> int:
        """
        Calculates the total number of tokens that a list of texts will consume,
        including any prompt overhead.

        Args:
            texts: The list of texts to be measured.
            prompts: An optional dictionary of custom prompts that might affect token count.

        Returns:
            The total estimated token count for the API call.
        """
        raise NotImplementedError
