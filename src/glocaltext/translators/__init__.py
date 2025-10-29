"""
Translation provider implementations.

Each translator adheres to the `BaseTranslator` interface and can be
dynamically initialized and selected based on the user's configuration.
"""

from glocaltext.models import Provider

from .base import BaseTranslator
from .gemini_translator import GeminiTranslator
from .gemma_translator import GemmaTranslator
from .google_translator import GoogleTranslator
from .mock_translator import MockTranslator

# Central mapping from provider name to translator class.
# This allows for dynamic instantiation of translators.
TRANSLATOR_MAPPING: dict[Provider, type[BaseTranslator]] = {
    Provider.GEMINI: GeminiTranslator,
    Provider.GOOGLE: GoogleTranslator,
    Provider.MOCK: MockTranslator,
    Provider.GEMMA: GemmaTranslator,
}
