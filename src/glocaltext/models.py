"""Defines the data models used throughout GlocalText."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from glocaltext.config import GlocalConfig
from glocaltext.translators.base import BaseTranslator
from glocaltext.types import TextMatch, TranslationTask


class Provider(str, Enum):
    """Enumeration of the supported translation providers."""

    GEMINI = "gemini"
    GOOGLE = "google"
    MOCK = "mock"
    GEMMA = "gemma"


@dataclass
class ExecutionContext:
    """A data class to hold the context for a single execution run."""

    task: TranslationTask
    config: GlocalConfig
    is_dry_run: bool = False
    is_incremental: bool = False
    translator: BaseTranslator | None = None
    files_to_process: list[Path] = field(default_factory=list)
    all_matches: list[TextMatch] = field(default_factory=list)
    terminated_matches: list[TextMatch] = field(default_factory=list)
    cached_matches: list[TextMatch] = field(default_factory=list)
    matches_to_translate: list[TextMatch] = field(default_factory=list)
