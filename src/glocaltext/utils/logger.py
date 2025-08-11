import logging
import sys
import time
from importlib import metadata
from pathlib import Path


def setup_logger(level=logging.INFO, debug: bool = False, artifacts_path: Path = None):
    """
    Set up the logger for console and optional file output in debug mode.
    """
    try:
        version = metadata.version("GlocalText")
    except metadata.PackageNotFoundError:
        version = "0.0.0-dev"

    logger = logging.getLogger("glocaltext")
    logger.setLevel(
        logging.DEBUG
    )  # Set logger to the lowest level to capture all messages
    logger.propagate = False  # Prevent messages from propagating to the root logger

    # Clear existing handlers to avoid duplication
    if logger.hasHandlers():
        logger.handlers.clear()

    log_format = f"%(asctime)s | GlocalText - {version} - %(levelname)s - %(message)s"
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%dT%H:%M:%SZ")
    formatter.converter = time.gmtime

    # Console Handler
    # Ensure the stream is opened with UTF-8 encoding
    stream = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    console_handler = logging.StreamHandler(stream)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler for Debug Mode
    if debug:
        if not artifacts_path:
            raise ValueError("artifacts_path must be provided when debug is True.")

        debug_log_path = artifacts_path / "debug.log"
        artifacts_path.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(debug_log_path, mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
