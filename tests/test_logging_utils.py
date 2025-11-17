"""Tests for the logging utilities module."""

import logging
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from glocaltext.logging_utils import ConsoleFormatter, FileFormatter, setup_logging


class TestConsoleFormatter(unittest.TestCase):
    """Test suite for ConsoleFormatter class."""

    def test_console_formatter_initialization(self) -> None:
        """1. Initialization: Creates formatter with correct format string and version."""
        version = "1.0.0"
        formatter = ConsoleFormatter(version)

        # Verify the formatter was initialized with correct parameters
        assert formatter.datefmt == "%Y-%m-%dT%H:%M:%S"
        assert formatter.converter == time.gmtime
        # Test by formatting a record to verify version is included
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "GlocalText - 1.0.0" in formatted

    def test_console_formatter_format_time_with_microseconds(self) -> None:
        """2. Time Format: Formats time with 6-digit microseconds and 'Z' suffix."""
        formatter = ConsoleFormatter("1.0.0")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Set a specific timestamp with fractional seconds
        record.created = 1234567890.123456

        formatted_time = formatter.formatTime(record, formatter.datefmt)

        assert formatted_time.endswith("Z")
        assert "." in formatted_time
        # Extract microseconds part
        microseconds_part = formatted_time.split(".")[-1].rstrip("Z")
        assert len(microseconds_part) == 6
        assert microseconds_part == "123456"

    def test_console_formatter_message_format(self) -> None:
        """3. Message Format: Formats complete log message with version and timestamp."""
        version = "2.0.0"
        formatter = ConsoleFormatter(version)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test log message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.123456

        formatted = formatter.format(record)

        assert "GlocalText - 2.0.0" in formatted
        assert "Test log message" in formatted
        assert "Z" in formatted
        assert "T" in formatted  # ISO 8601 date separator


class TestFileFormatter(unittest.TestCase):
    """Test suite for FileFormatter class."""

    def test_file_formatter_initialization(self) -> None:
        """1. Initialization: Creates formatter with detailed format string."""
        formatter = FileFormatter()

        # Verify the formatter was initialized correctly
        assert formatter.datefmt == "%Y-%m-%dT%H:%M:%S"
        assert formatter.converter == time.gmtime
        # Test by formatting a record to verify detailed format
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_func"
        formatted = formatter.format(record)
        assert "test.logger" in formatted
        assert "test_func" in formatted
        assert "42" in formatted
        assert "DEBUG" in formatted

    def test_file_formatter_format_time_with_microseconds(self) -> None:
        """2. Time Format: Formats time with 6-digit microseconds and 'Z' suffix."""
        formatter = FileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="Debug message",
            args=(),
            exc_info=None,
        )
        record.created = 9876543210.654321

        formatted_time = formatter.formatTime(record, formatter.datefmt)

        assert formatted_time.endswith("Z")
        assert "." in formatted_time
        microseconds_part = formatted_time.split(".")[-1].rstrip("Z")
        assert len(microseconds_part) == 6
        assert microseconds_part == "654321"

    def test_file_formatter_detailed_format(self) -> None:
        """3. Detailed Format: Includes logger name, function name, and line number."""
        formatter = FileFormatter()
        record = logging.LogRecord(
            name="glocaltext.module",
            level=logging.DEBUG,
            pathname="/path/to/module.py",
            lineno=123,
            msg="Detailed log",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_function"
        record.created = 1234567890.0

        formatted = formatter.format(record)

        assert "glocaltext.module" in formatted
        assert "test_function" in formatted
        assert "123" in formatted
        assert "DEBUG" in formatted
        assert "Detailed log" in formatted


class TestSetupLogging(unittest.TestCase):
    """Test suite for setup_logging function."""

    def tearDown(self) -> None:
        """Clean up logging state after each test."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.setLevel(logging.WARNING)

    def test_setup_logging_default_mode(self) -> None:
        """1. Default Mode: Sets up INFO level logging without debug file."""
        version = "1.0.0"

        setup_logging(version, debug=False)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        # Should have at least one handler (console)
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1

    def test_setup_logging_debug_mode(self) -> None:
        """2. Debug Mode: Sets up DEBUG level logging with file handler."""
        version = "1.0.0"
        mock_log_dir = Path("/mock/log/dir")
        mock_log_file = mock_log_dir / "debug.log"

        with patch("glocaltext.logging_utils.paths.get_log_dir", return_value=mock_log_dir), patch("glocaltext.logging_utils.paths.ensure_dir_exists") as mock_ensure_dir, patch("glocaltext.logging_utils.FileHandler") as mock_file_handler:
            # Configure mock to have a level attribute
            mock_handler_instance = MagicMock()
            mock_handler_instance.level = logging.DEBUG
            mock_file_handler.return_value = mock_handler_instance

            setup_logging(version, debug=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        mock_ensure_dir.assert_called_once_with(mock_log_dir)
        mock_file_handler.assert_called_once_with(mock_log_file, mode="w", encoding="utf-8")

    def test_setup_logging_clears_existing_handlers(self) -> None:
        """3. Handler Cleanup: Clears existing handlers before setup."""
        root_logger = logging.getLogger()
        # Clear any existing handlers first
        root_logger.handlers.clear()

        # Add a dummy handler
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        initial_count = len(root_logger.handlers)
        assert initial_count >= 1

        setup_logging("1.0.0", debug=False)

        # Should have handlers, but not the dummy one
        assert dummy_handler not in root_logger.handlers
        # Should have at least one new handler
        assert len(root_logger.handlers) >= 1

    def test_setup_logging_console_handler_configuration(self) -> None:
        """4. Console Handler: Configures console handler with correct formatter."""
        version = "2.5.0"

        setup_logging(version, debug=False)

        root_logger = logging.getLogger()
        console_handler = root_logger.handlers[0]
        assert isinstance(console_handler, logging.StreamHandler)
        assert console_handler.level == logging.INFO
        assert isinstance(console_handler.formatter, ConsoleFormatter)

    def test_setup_logging_debug_console_level(self) -> None:
        """5. Debug Console Level: Sets console handler to DEBUG when debug=True."""
        version = "1.0.0"
        mock_log_dir = Path("/mock/log/dir")

        with patch("glocaltext.logging_utils.paths.get_log_dir", return_value=mock_log_dir), patch("glocaltext.logging_utils.paths.ensure_dir_exists"), patch("glocaltext.logging_utils.FileHandler") as mock_file_handler:
            # Configure mock properly
            mock_handler_instance = MagicMock()
            mock_handler_instance.level = logging.DEBUG
            mock_file_handler.return_value = mock_handler_instance

            setup_logging(version, debug=True)

        root_logger = logging.getLogger()
        # Find the console handler (StreamHandler that's not a file handler)
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]
        assert len(console_handlers) >= 1
        assert console_handlers[0].level == logging.DEBUG

    def test_setup_logging_debug_file_handler_failure(self) -> None:
        """6. File Handler Failure: Continues with console logging if file creation fails."""
        version = "1.0.0"

        with patch("glocaltext.logging_utils.paths.get_log_dir", side_effect=OSError("Cannot create directory")):
            setup_logging(version, debug=True)

        root_logger = logging.getLogger()
        # Should still have console handler
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1

    def test_setup_logging_multiple_calls_idempotent(self) -> None:
        """7. Idempotency: Multiple calls clear old handlers and set up fresh ones."""
        version = "1.0.0"

        setup_logging(version, debug=False)
        first_handler_count = len(logging.getLogger().handlers)
        assert first_handler_count == 1

        setup_logging(version, debug=False)
        second_handler_count = len(logging.getLogger().handlers)

        # Should still have only one handler
        assert second_handler_count == 1
        assert first_handler_count == second_handler_count

    def test_setup_logging_file_handler_uses_file_formatter(self) -> None:
        """8. File Formatter: File handler uses FileFormatter in debug mode."""
        version = "1.0.0"
        mock_log_dir = Path("/mock/log/dir")
        mock_file_handler_instance = MagicMock()
        mock_file_handler_instance.level = logging.DEBUG

        with patch("glocaltext.logging_utils.paths.get_log_dir", return_value=mock_log_dir), patch("glocaltext.logging_utils.paths.ensure_dir_exists"), patch("glocaltext.logging_utils.FileHandler", return_value=mock_file_handler_instance):
            setup_logging(version, debug=True)

        # Verify setFormatter was called with FileFormatter
        mock_file_handler_instance.setFormatter.assert_called_once()
        formatter_arg = mock_file_handler_instance.setFormatter.call_args[0][0]
        assert isinstance(formatter_arg, FileFormatter)


if __name__ == "__main__":
    unittest.main()
