"""Main entry point for the GlocalText command-line interface."""

import argparse
import logging
import time
from typing import Any

from . import __version__
from .config import GlocalConfig, load_config
from .reporting import generate_summary_report
from .workflow import run_task

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the GlocalText CLI.

    Returns:
        argparse.Namespace: An object containing the parsed command-line arguments.

    """
    parser = argparse.ArgumentParser(description="GlocalText Localization Tool")
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="glocaltext_config.yaml",
        help="Path to the configuration file (default: glocaltext_config.yaml)",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Run in incremental mode, translating only new or modified content.",
    )
    parser.add_argument(
        "--debug",
        nargs="?",
        const=True,
        default=False,
        help="Enable debug logging. Optionally provide a directory path to save the debug log file.",
    )
    return parser.parse_args()


def _load_config(args: argparse.Namespace) -> GlocalConfig | None:
    """
    Load configuration from a file and apply command-line overrides.

    This function loads the main configuration file and allows for dynamic
    adjustments based on command-line flags, such as enabling debug mode.

    Args:
        args: The parsed command-line arguments.

    Returns:
        An optional GlocalConfig object if loading is successful, otherwise None.

    """
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.exception("Configuration file not found at: %s", args.config)
        return None
    else:
        if args.debug:
            config.debug_options.enabled = True
            if isinstance(args.debug, str):
                config.debug_options.log_path = args.debug
        return config


def _run_tasks(config: GlocalConfig, *, incremental: bool) -> list[Any]:
    """
    Iterate over and execute all enabled translation tasks.

    Args:
        config: The application's configuration object.
        incremental: A flag indicating whether to run in incremental mode.

    Returns:
        A list of all matches found across all executed tasks.

    """
    all_matches: list[Any] = []
    for task in config.tasks:
        if task.enabled:
            if incremental:
                task.incremental = True
            logger.info("\n--- Running Task: %s ---", task.name)
            task_matches = run_task(task, config)
            all_matches.extend(task_matches)
            logger.info("--- Task Finished: %s ---", task.name)
    return all_matches


def main() -> None:
    """
    Run the main entry point for the GlocalText command-line interface.

    Orchestrates the entire process:
    1. Parses command-line arguments.
    2. Loads the configuration.
    3. Runs all enabled tasks.
    4. Generates a summary report.
    """
    start_time = time.time()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    try:
        args = _parse_args()
        config = _load_config(args)

        if config:
            all_matches = _run_tasks(config, incremental=args.incremental)
            generate_summary_report(all_matches, start_time, config)

    except Exception:
        logger.exception("An unexpected error occurred")

    logger.info("\nAll tasks completed.")


if __name__ == "__main__":
    main()
