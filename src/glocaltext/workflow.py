"""Manages the overall GlocalText translation workflow."""

import logging
from typing import TYPE_CHECKING

from .config import GlocalConfig, TranslationTask
from .models import ExecutionContext, TextMatch
from .processing import (
    CacheProcessor,
    CacheUpdateProcessor,
    CaptureProcessor,
    Processor,
    TerminatingRuleProcessor,
    TranslationProcessor,
    WriteBackProcessor,
)
from .reporters.dry_run_reporter import DryRunReporter
from .reporters.summary_reporter import SummaryReporter

if TYPE_CHECKING:
    from collections.abc import Sequence

# Configure logging
logger = logging.getLogger(__name__)


def run_task(task: TranslationTask, config: GlocalConfig, *, dry_run: bool = False, debug: bool = False) -> list[TextMatch]:
    """
    Run a single translation task by orchestrating a multi-phase processor pipeline.

    This function initializes the execution context and defines the sequence of
    processors that form the translation pipeline. It then iterates through the
    pipeline, calling each processor's `process` method to progressively build
    up the translation results. Finally, it generates a report based on the
    outcome.

    Args:
        task: The translation task to execute.
        config: The global application configuration.
        dry_run: If True, skips API calls and file modifications.
        debug: If True, enables debug logging and behaviors.

    Returns:
        A list containing all processed TextMatch objects.

    """
    context = ExecutionContext(
        task=task,
        config=config,
        is_incremental=task.incremental,
        is_dry_run=dry_run,
        is_debug=debug,
    )

    logger.info(
        "Running task '%s' in %s mode.",
        context.task.name,
        "incremental" if context.is_incremental else "full",
    )

    # Define the processor pipeline
    pipeline: Sequence[Processor] = [
        CaptureProcessor(),
        TerminatingRuleProcessor(),
        CacheProcessor(),
        TranslationProcessor(),
        CacheUpdateProcessor(),
        WriteBackProcessor(),
    ]

    # Execute the pipeline
    for processor in pipeline:
        logger.debug("Executing processor: %s", processor.__class__.__name__)
        processor.process(context)

    # Generate the appropriate report
    reporter = DryRunReporter() if context.is_dry_run else SummaryReporter()
    reporter.generate(context)

    return context.terminated_matches + context.cached_matches + context.matches_to_translate
