"""Pytest configuration and fixtures for integration tests."""

import os

import pytest

from glocaltext.config import ProviderSettings
from glocaltext.translators.gemini_translator import GeminiTranslator
from glocaltext.translators.gemma_translator import GemmaTranslator
from glocaltext.translators.google_translator import GoogleTranslator
from glocaltext.translators.mock_translator import MockTranslator


def has_google_api_key() -> bool:
    """Check if Google Translate API key is available."""
    return bool(os.getenv("GOOGLE_TRANSLATE_API_KEY"))


def has_gemini_api_key() -> bool:
    """Check if Gemini API key is available."""
    return bool(os.getenv("GEMINI_API_KEY"))


def has_gemma_api_key() -> bool:
    """Check if Gemma API key is available (same as Gemini)."""
    return bool(os.getenv("GEMINI_API_KEY"))


@pytest.fixture
def mock_translator() -> MockTranslator:
    """
    Provide a MockTranslator instance for testing.

    This translator does not require API keys and can be used
    to test basic functionality without external dependencies.
    """
    return MockTranslator(settings=ProviderSettings())


@pytest.fixture
def google_translator() -> GoogleTranslator | None:
    """
    Provide GoogleTranslator if API key is available.

    Skips the test if GOOGLE_TRANSLATE_API_KEY environment variable is not set.
    Note: GoogleTranslator uses deep-translator which doesn't require explicit API key.
    """
    if not has_google_api_key():
        pytest.skip("Google Translate API key not available (set GOOGLE_TRANSLATE_API_KEY)")
    return GoogleTranslator(settings=ProviderSettings())


@pytest.fixture
def gemini_translator() -> GeminiTranslator | None:
    """
    Provide GeminiTranslator if API key is available.

    Skips the test if GEMINI_API_KEY environment variable is not set.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("Gemini API key not available (set GEMINI_API_KEY)")
    return GeminiTranslator(settings=ProviderSettings(api_key=api_key))


@pytest.fixture
def gemma_translator() -> GemmaTranslator | None:
    """
    Provide GemmaTranslator if API key is available.

    Skips the test if GEMINI_API_KEY environment variable is not set.
    Note: Gemma uses the same API key as Gemini.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("Gemini API key not available (set GEMINI_API_KEY)")
    return GemmaTranslator(settings=ProviderSettings(api_key=api_key))


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for pytest."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests requiring API keys (deselect with '-m \"not integration\"')",
    )
