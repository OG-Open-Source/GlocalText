"""
Translation provider implementations.

Each translator adheres to the `BaseTranslator` interface and can be
dynamically initialized and selected based on the user's configuration.
"""

from .base import BaseTranslator
from .gemini_translator import GeminiTranslator
from .google_translator import GoogleTranslator
from .mock_translator import MockTranslator

# Central mapping from provider name to translator class.
# This allows for dynamic instantiation of translators.
TRANSLATOR_MAPPING: dict[str, type[BaseTranslator]] = {
    "gemini": GeminiTranslator,
    "google": GoogleTranslator,
    "mock": MockTranslator,
}
