"""Main entry point for the GlocalText command-line interface."""

import argparse
import logging
import sys

from . import __version__, paths
from .config import GlocalConfig, load_config
from .logging_utils import setup_logging
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
        version=f"GlocalText {__version__}",
        help="Show the version number and exit.",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Run in incremental mode, translating only new or modified content.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug level logging.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any actual changes or API calls.",
    )
    return parser.parse_args()


def _load_config() -> GlocalConfig | None:
    """
    Load configuration from the fixed file path.

    Returns:
        An optional GlocalConfig object if loading is successful, otherwise None.

    """
    try:
        config_path = paths.get_config_file_path()
        logger.info("Loading configuration from: %s", config_path)
        return load_config(str(config_path))
    except FileNotFoundError:
        # This is now a critical error if the config anchor can't be found.
        # The error from find_project_root is more descriptive.
        logger.exception("Could not find a valid configuration file.")
        return None
    except Exception:
        logger.exception("An unexpected error occurred while loading the configuration.")
        return None


def _run_tasks(config: GlocalConfig, *, incremental: bool, dry_run: bool, debug: bool) -> None:
    """
    Iterate over and execute all enabled translation tasks.

    Args:
        config: The application's configuration object.
        incremental: A flag indicating whether to run in incremental mode.
        dry_run: A flag indicating whether to perform a dry run.
        debug: A flag indicating whether to run in debug mode.

    """
    for task in config.tasks:
        if task.enabled:
            if incremental:
                task.incremental = True
            logger.info("Running Task: '%s'", task.name)
            logger.debug("Starting task '%s' with config: %s", task.name, task.model_dump_json(indent=2))
            run_task(task, config, dry_run=dry_run, debug=debug)


def main() -> None:
    """
    Run the main entry point for the GlocalText command-line interface.

    Orchestrates the entire process:
    1. Parses command-line arguments.
    2. Loads the configuration.
    3. Runs all enabled tasks.
    """
    try:
        args = _parse_args()
        setup_logging(version=__version__, debug=args.debug)

        config = _load_config()

        if config:
            _run_tasks(config, incremental=args.incremental, dry_run=args.dry_run, debug=args.debug)
        else:
            # If config is None, it means an error occurred during loading.
            # The error has already been logged by _load_config.
            logger.critical("Failed to load configuration. Aborting.")
            sys.exit(1)

    except Exception:
        logger.exception("An unexpected error occurred")
        logger.critical("An unrecoverable error occurred. Please check the logs for details.")
        sys.exit(1)

    logger.info("All tasks completed.")


if __name__ == "__main__":
    main()
