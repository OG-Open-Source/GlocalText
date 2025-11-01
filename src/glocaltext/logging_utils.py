"""Custom logging utilities for the GlocalText application."""
# src/glocaltext/logging_utils.py

import logging
import sys
import time
from logging import FileHandler


# Console Log Formatter
class ConsoleFormatter(logging.Formatter):
    """A custom formatter for console output to provide clean, user-friendly logs."""

    def __init__(self, version: str) -> None:
        """
        Initialize the formatter with the application version.

        Args:
            version: The GlocalText application version.

        """
        super().__init__(
            fmt=f"%(asctime)s | GlocalText - {version} | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        self.converter = time.gmtime

    def format_time(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Format the time with milliseconds and a 'Z' for UTC."""
        ct = self.converter(record.created)
        s = time.strftime(datefmt, ct) if datefmt else time.strftime(self.default_time_format, ct)
        return f"{s}.{record.msecs:03d}Z"


# File Log Formatter
class FileFormatter(logging.Formatter):
    """A detailed formatter for debug log files, aimed at developers."""

    def __init__(self) -> None:
        """Initialize the detailed file formatter."""
        super().__init__(
            fmt="%(asctime)s | %(name)-20s | %(funcName)-20s:%(lineno)-4d | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        self.converter = time.gmtime

    def format_time(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        """Format the time with milliseconds and a 'Z' for UTC."""
        ct = self.converter(record.created)
        s = time.strftime(datefmt, ct) if datefmt else time.strftime(self.default_time_format, ct)
        return f"{s}.{record.msecs:03d}Z"


def setup_logging(version: str, *, debug: bool = False) -> None:
    """
    Configure the root logger for the GlocalText application.

    This function sets up a dual-logging system:
    1.  Console: User-facing messages. Level is INFO by default, DEBUG if debug=True.
    2.  File (DEBUG): Developer-facing, detailed logs written to 'glocaltext_debug.log'
        when debug=True.

    Args:
        version: The application version, included in console logs.
        debug: If True, enables detailed file logging and sets console level to DEBUG.

    """
    root_logger = logging.getLogger()
    # Clear any handlers created by basicConfig or previous setups
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Determine the logging level based on the debug flag
    console_level = logging.DEBUG if debug else logging.INFO
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # --- Console Handler ---
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(ConsoleFormatter(version))
    # The filter that only allowed INFO is removed to allow DEBUG messages through.
    root_logger.addHandler(console_handler)

    if debug:
        # --- File Handler (DEBUG) ---
        file_handler = FileHandler("glocaltext_debug.log", mode="w", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)

        # Use the root logger to announce debug mode, so it appears on all handlers
        logging.getLogger().info("Debug mode enabled. Console level set to DEBUG. Detailed logs will be written to glocaltext_debug.log")
