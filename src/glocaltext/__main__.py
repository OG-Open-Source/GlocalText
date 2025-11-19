"""Main entry point for the GlocalText command-line interface."""

import argparse
import logging
import sys
from pathlib import Path

from . import __version__, paths
from .config import GlocalConfig, load_config
from .logging_utils import setup_logging
from .templates import DEFAULT_CONFIG_YAML
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
        "--debug",
        action="store_true",
        help="Enable debug level logging.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'init' command
    init_parser = subparsers.add_parser("init", help="Initialize a new GlocalText project.")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="The directory to initialize the project in (default: current directory).",
    )
    init_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug level logging.",
    )

    # 'run' command (implicit default if no command is specified, but handled explicitly here)
    run_parser = subparsers.add_parser("run", help="Run translation tasks.")
    run_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="The directory to run GlocalText in (default: current directory).",
    )
    run_parser.add_argument(
        "--incremental",
        action="store_true",
        help="Run in incremental mode, translating only new or modified content.",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making any actual changes or API calls.",
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug level logging.",
    )

    # If no arguments are provided, print help
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    return parser.parse_args()


def _init_project(target_path: str) -> None:
    """Initialize a new GlocalText project structure."""
    path = Path(target_path).resolve()
    logger.info("Initializing GlocalText project in: %s", path)

    config_dir = path / paths.OGOS_SUBDIR / "configs"
    config_file = config_dir / "main.yaml"

    if config_file.exists():
        logger.warning("Configuration file already exists at: %s", config_file)
        return

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file.write_text(DEFAULT_CONFIG_YAML, encoding="utf-8")
        logger.info("Created default configuration at: %s", config_file)
        logger.info("Project initialized successfully!")
    except OSError:
        logger.exception("Failed to initialize project")
        sys.exit(1)


def _load_config(root_path: Path) -> GlocalConfig | None:
    """
    Load configuration from the fixed file path relative to root_path.

    Returns:
        An optional GlocalConfig object if loading is successful, otherwise None.

    """
    try:
        config_path = paths.get_config_file_path(root_path)
        logger.info("Loading configuration from: %s", config_path)
        return load_config(str(config_path))
    except FileNotFoundError:
        # The error from find_project_root is more descriptive.
        logger.exception("Could not find a valid configuration file.")
        return None
    except Exception:
        logger.exception("An unexpected error occurred while loading the configuration.")
        return None


def _run_tasks(config: GlocalConfig, project_root: Path, *, incremental: bool, dry_run: bool, debug: bool) -> None:
    """
    Iterate over and execute all enabled translation tasks.

    Args:
        config: The application's configuration object.
        project_root: The root path of the project.
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
            run_task(task, config, project_root, dry_run=dry_run, debug=debug)


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

        if args.command == "init":
            # Validate path for init command
            init_path = Path(args.path).resolve()
            if not init_path.exists():
                logger.error("Path does not exist: %s", init_path)
                sys.exit(1)
            if not init_path.is_dir():
                logger.error("Path is not a directory: %s", init_path)
                sys.exit(1)

            setup_logging(version=__version__, debug=args.debug, project_root=init_path)
            _init_project(str(init_path))
            return

        # Default to 'run' command logic
        target_path = Path(args.path).resolve() if hasattr(args, "path") else Path.cwd()

        # Validate path for run command
        if not target_path.exists():
            logger.error("Path does not exist: %s", target_path)
            sys.exit(1)
        if not target_path.is_dir():
            logger.error("Path is not a directory: %s", target_path)
            sys.exit(1)

        setup_logging(version=__version__, debug=args.debug, project_root=target_path)

        config = _load_config(target_path)

        if config:
            _run_tasks(
                config,
                target_path,
                incremental=getattr(args, "incremental", False),
                dry_run=getattr(args, "dry_run", False),
                debug=args.debug,
            )
        else:
            logger.critical("Failed to load configuration. Aborting.")
            sys.exit(1)

    except Exception:
        logger.exception("An unexpected error occurred")
        logger.critical("An unrecoverable error occurred. Please check the logs for details.")
        sys.exit(1)

    logger.info("All tasks completed.")


if __name__ == "__main__":
    main()
