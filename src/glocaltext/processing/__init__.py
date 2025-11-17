"""
Processing pipeline components.

This module provides a set of processor classes for the GlocalText
translation workflow. Each processor implements a specific stage
of the pipeline.
"""

from .base import Processor
from .cache_processors import CacheProcessor, CacheUpdateProcessor
from .capture_processor import CaptureProcessor
from .termination_processor import TerminatingRuleProcessor
from .translation_processor import TranslationProcessor
from .writeback_processor import WriteBackProcessor

__all__ = [
    "CacheProcessor",
    "CacheUpdateProcessor",
    "CaptureProcessor",
    "Processor",
    "TerminatingRuleProcessor",
    "TranslationProcessor",
    "WriteBackProcessor",
]
