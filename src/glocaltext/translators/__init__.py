"""
Translation provider implementations.

Each translator adheres to the `BaseTranslator` interface and can be
dynamically initialized and selected based on the user's configuration.
"""

from .base import BaseTranslator
from .base_genai import BaseGenAITranslator
from .gemini_translator import GeminiTranslator
from .gemma_translator import GemmaTranslator
from .google_translator import GoogleTranslator
from .mock_translator import MockTranslator

# Central mapping from provider name to translator class.
# This allows for dynamic instantiation of translators.
TRANSLATOR_MAPPING: dict[str, type[BaseTranslator]] = {
    "gemini": GeminiTranslator,
    "google": GoogleTranslator,
    "mock": MockTranslator,
    "gemma": GemmaTranslator,
}

__all__ = [
    "TRANSLATOR_MAPPING",
    "BaseGenAITranslator",
    "BaseTranslator",
    "GeminiTranslator",
    "GemmaTranslator",
    "GoogleTranslator",
    "MockTranslator",
]
