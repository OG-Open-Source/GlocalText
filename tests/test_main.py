"""Tests for the main CLI entry point."""

import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from glocaltext import __version__
from glocaltext.__main__ import _load_config, _parse_args, _run_tasks, main
from glocaltext.config import GlocalConfig, ProviderSettings
from glocaltext.types import Source, TranslationTask


class TestParseArgs(unittest.TestCase):
    """Test suite for CLI argument parsing."""

    @patch("sys.argv", ["glocaltext"])
    def test_parse_args_no_arguments(self) -> None:
        """1. Default Args: Parses with no arguments, all flags False."""
        args = _parse_args()
        assert isinstance(args, Namespace)
        assert args.incremental is False
        assert args.debug is False
        assert args.dry_run is False

    @patch("sys.argv", ["glocaltext", "--incremental"])
    def test_parse_args_incremental_flag(self) -> None:
        """2. Incremental Flag: Correctly parses --incremental."""
        args = _parse_args()
        assert args.incremental is True
        assert args.debug is False
        assert args.dry_run is False

    @patch("sys.argv", ["glocaltext", "--debug"])
    def test_parse_args_debug_flag(self) -> None:
        """3. Debug Flag: Correctly parses --debug."""
        args = _parse_args()
        assert args.debug is True
        assert args.incremental is False
        assert args.dry_run is False

    @patch("sys.argv", ["glocaltext", "--dry-run"])
    def test_parse_args_dry_run_flag(self) -> None:
        """4. Dry Run Flag: Correctly parses --dry-run."""
        args = _parse_args()
        assert args.dry_run is True
        assert args.incremental is False
        assert args.debug is False

    @patch("sys.argv", ["glocaltext", "--incremental", "--debug", "--dry-run"])
    def test_parse_args_all_flags_combined(self) -> None:
        """5. Combined Flags: Correctly parses multiple flags together."""
        args = _parse_args()
        assert args.incremental is True
        assert args.debug is True
        assert args.dry_run is True

    @patch("sys.argv", ["glocaltext", "--version"])
    def test_parse_args_version_flag(self) -> None:
        """6. Version Flag: --version triggers SystemExit with version output."""
        with pytest.raises(SystemExit) as exc_info:
            _parse_args()
        assert exc_info.value.code == 0


class TestLoadConfig(unittest.TestCase):
    """Test suite for configuration loading."""

    @patch("glocaltext.__main__.paths.get_config_file_path")
    @patch("glocaltext.__main__.load_config")
    def test_load_config_success(self, mock_load_config: MagicMock, mock_get_path: MagicMock) -> None:
        """1. Success: Successfully loads configuration from the default path."""
        mock_config_path = Path("/project/glocaltext.yaml")
        mock_get_path.return_value = mock_config_path
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config

        with self.assertLogs("glocaltext.__main__", level="INFO") as cm:
            result = _load_config()

        assert result is mock_config
        mock_get_path.assert_called_once()
        mock_load_config.assert_called_once_with(str(mock_config_path))
        assert any("Loading configuration from:" in log for log in cm.output)

    @patch("glocaltext.__main__.paths.get_config_file_path")
    @patch("glocaltext.__main__.load_config")
    def test_load_config_file_not_found(self, mock_load_config: MagicMock, mock_get_path: MagicMock) -> None:
        """2. FileNotFoundError: Returns None and logs exception when config file not found."""
        mock_get_path.return_value = Path("/project/glocaltext.yaml")
        mock_load_config.side_effect = FileNotFoundError("Config file not found")

        with self.assertLogs("glocaltext.__main__", level="ERROR") as cm:
            result = _load_config()

        assert result is None
        assert any("Could not find a valid configuration file" in log for log in cm.output)

    @patch("glocaltext.__main__.paths.get_config_file_path")
    @patch("glocaltext.__main__.load_config")
    def test_load_config_unexpected_exception(self, mock_load_config: MagicMock, mock_get_path: MagicMock) -> None:
        """3. Unexpected Error: Returns None and logs exception on unexpected errors."""
        mock_get_path.return_value = Path("/project/glocaltext.yaml")
        mock_load_config.side_effect = ValueError("Invalid YAML structure")

        with self.assertLogs("glocaltext.__main__", level="ERROR") as cm:
            result = _load_config()

        assert result is None
        assert any("An unexpected error occurred while loading the configuration" in log for log in cm.output)

    @patch("glocaltext.__main__.paths.get_config_file_path")
    def test_load_config_path_resolution_error(self, mock_get_path: MagicMock) -> None:
        """4. Path Error: Returns None when path resolution fails."""
        mock_get_path.side_effect = FileNotFoundError("Cannot find project root")

        with self.assertLogs("glocaltext.__main__", level="ERROR") as cm:
            result = _load_config()

        assert result is None
        assert any("Could not find a valid configuration file" in log for log in cm.output)


class TestRunTasks(unittest.TestCase):
    """Test suite for task execution logic."""

    def setUp(self) -> None:
        """Set up mock configuration and tasks."""
        self.mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        self.enabled_task = TranslationTask(
            name="enabled_task",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            enabled=True,
        )
        self.disabled_task = TranslationTask(
            name="disabled_task",
            source_lang="en",
            target_lang="de",
            translator="mock",
            source=Source(include=["*.txt"]),
            enabled=False,
        )

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_executes_enabled_tasks(self, mock_run_task: MagicMock) -> None:
        """1. Enabled Tasks: Executes only enabled tasks."""
        self.mock_config.tasks = [self.enabled_task, self.disabled_task]

        with self.assertLogs("glocaltext.__main__", level="INFO") as cm:
            _run_tasks(self.mock_config, incremental=False, dry_run=False, debug=False)

        mock_run_task.assert_called_once_with(self.enabled_task, self.mock_config, dry_run=False, debug=False)
        assert any("Running Task: 'enabled_task'" in log for log in cm.output)
        assert not any("disabled_task" in log for log in cm.output)

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_skips_disabled_tasks(self, mock_run_task: MagicMock) -> None:
        """2. Disabled Tasks: Skips tasks where enabled=False."""
        self.mock_config.tasks = [self.disabled_task]

        _run_tasks(self.mock_config, incremental=False, dry_run=False, debug=False)

        mock_run_task.assert_not_called()

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_incremental_mode_override(self, mock_run_task: MagicMock) -> None:
        """3. Incremental Override: Sets task.incremental=True when incremental flag is passed."""
        self.enabled_task.incremental = False
        self.mock_config.tasks = [self.enabled_task]

        _run_tasks(self.mock_config, incremental=True, dry_run=False, debug=False)

        assert self.enabled_task.incremental is True
        mock_run_task.assert_called_once()

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_preserves_existing_incremental(self, mock_run_task: MagicMock) -> None:
        """4. Incremental Preserve: Does not override task.incremental if flag is False."""
        self.enabled_task.incremental = True
        self.mock_config.tasks = [self.enabled_task]

        _run_tasks(self.mock_config, incremental=False, dry_run=False, debug=False)

        assert self.enabled_task.incremental is True
        mock_run_task.assert_called_once()

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_passes_dry_run_flag(self, mock_run_task: MagicMock) -> None:
        """5. Dry Run Mode: Correctly passes dry_run flag to run_task."""
        self.mock_config.tasks = [self.enabled_task]

        _run_tasks(self.mock_config, incremental=False, dry_run=True, debug=False)

        mock_run_task.assert_called_once_with(self.enabled_task, self.mock_config, dry_run=True, debug=False)

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_passes_debug_flag(self, mock_run_task: MagicMock) -> None:
        """6. Debug Mode: Correctly passes debug flag to run_task."""
        self.mock_config.tasks = [self.enabled_task]

        with self.assertLogs("glocaltext.__main__", level="DEBUG") as cm:
            _run_tasks(self.mock_config, incremental=False, dry_run=False, debug=True)

        mock_run_task.assert_called_once_with(self.enabled_task, self.mock_config, dry_run=False, debug=True)
        assert any("Starting task 'enabled_task' with config:" in log for log in cm.output)

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_empty_task_list(self, mock_run_task: MagicMock) -> None:
        """7. Empty Tasks: Handles empty task list gracefully."""
        self.mock_config.tasks = []

        _run_tasks(self.mock_config, incremental=False, dry_run=False, debug=False)

        mock_run_task.assert_not_called()

    @patch("glocaltext.__main__.run_task")
    def test_run_tasks_multiple_enabled_tasks(self, mock_run_task: MagicMock) -> None:
        """8. Multiple Tasks: Executes all enabled tasks in order."""
        task1 = TranslationTask(
            name="task1",
            source_lang="en",
            target_lang="fr",
            translator="mock",
            source=Source(include=["*.txt"]),
            enabled=True,
        )
        task2 = TranslationTask(
            name="task2",
            source_lang="en",
            target_lang="de",
            translator="mock",
            source=Source(include=["*.txt"]),
            enabled=True,
        )
        self.mock_config.tasks = [task1, task2]

        _run_tasks(self.mock_config, incremental=False, dry_run=False, debug=False)

        assert mock_run_task.call_count == 2
        mock_run_task.assert_has_calls(
            [
                call(task1, self.mock_config, dry_run=False, debug=False),
                call(task2, self.mock_config, dry_run=False, debug=False),
            ]
        )


class TestMainFunction(unittest.TestCase):
    """Test suite for the main() entry point."""

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__.setup_logging")
    @patch("glocaltext.__main__._parse_args")
    def test_main_successful_execution(
        self,
        mock_parse_args: MagicMock,
        mock_setup_logging: MagicMock,
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """1. Success: Full successful execution of main workflow."""
        mock_args = Namespace(incremental=False, debug=False, dry_run=False)
        mock_parse_args.return_value = mock_args
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config

        with self.assertLogs("glocaltext.__main__", level="INFO") as cm:
            main()

        mock_parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with(version=__version__, debug=False)
        mock_load_config.assert_called_once()
        mock_run_tasks.assert_called_once_with(mock_config, incremental=False, dry_run=False, debug=False)
        assert any("All tasks completed" in log for log in cm.output)

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__.setup_logging")
    @patch("glocaltext.__main__._parse_args")
    @patch("sys.exit")
    def test_main_config_load_failure(
        self,
        mock_exit: MagicMock,
        mock_parse_args: MagicMock,
        _mock_setup_logging: MagicMock,  # noqa: PT019
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """2. Config Failure: Exits with code 1 when config loading fails."""
        mock_args = Namespace(incremental=False, debug=False, dry_run=False)
        mock_parse_args.return_value = mock_args
        mock_load_config.return_value = None

        with self.assertLogs("glocaltext.__main__", level="CRITICAL") as cm:
            main()

        mock_run_tasks.assert_not_called()
        assert any("Failed to load configuration" in log for log in cm.output)
        mock_exit.assert_called_once_with(1)

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__._parse_args")
    @patch("sys.exit")
    def test_main_unexpected_exception(
        self,
        mock_exit: MagicMock,
        mock_parse_args: MagicMock,
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """3. Unexpected Error: Catches and logs unexpected exceptions, exits with code 1."""
        mock_args = Namespace(incremental=False, debug=False, dry_run=False)
        mock_parse_args.return_value = mock_args
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config
        mock_run_tasks.side_effect = RuntimeError("Unexpected runtime error")

        with self.assertLogs("glocaltext.__main__", level="ERROR") as cm:
            main()

        assert any("An unexpected error occurred" in log for log in cm.output)
        assert any("An unrecoverable error occurred" in log for log in cm.output)
        mock_exit.assert_called_once_with(1)

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__.setup_logging")
    @patch("glocaltext.__main__._parse_args")
    def test_main_with_debug_flag(
        self,
        mock_parse_args: MagicMock,
        mock_setup_logging: MagicMock,
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """4. Debug Mode: Correctly passes debug flag through the workflow."""
        mock_args = Namespace(incremental=False, debug=True, dry_run=False)
        mock_parse_args.return_value = mock_args
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config

        main()

        mock_setup_logging.assert_called_once_with(version=__version__, debug=True)
        mock_run_tasks.assert_called_once_with(mock_config, incremental=False, dry_run=False, debug=True)

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__._parse_args")
    def test_main_with_incremental_flag(
        self,
        mock_parse_args: MagicMock,
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """5. Incremental Mode: Correctly passes incremental flag to _run_tasks."""
        mock_args = Namespace(incremental=True, debug=False, dry_run=False)
        mock_parse_args.return_value = mock_args
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config

        main()

        mock_run_tasks.assert_called_once_with(mock_config, incremental=True, dry_run=False, debug=False)

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__._parse_args")
    def test_main_with_dry_run_flag(
        self,
        mock_parse_args: MagicMock,
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """6. Dry Run Mode: Correctly passes dry_run flag to _run_tasks."""
        mock_args = Namespace(incremental=False, debug=False, dry_run=True)
        mock_parse_args.return_value = mock_args
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config

        main()

        mock_run_tasks.assert_called_once_with(mock_config, incremental=False, dry_run=True, debug=False)

    @patch("glocaltext.__main__._run_tasks")
    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__.setup_logging")
    @patch("glocaltext.__main__._parse_args")
    def test_main_with_all_flags(
        self,
        mock_parse_args: MagicMock,
        mock_setup_logging: MagicMock,
        mock_load_config: MagicMock,
        mock_run_tasks: MagicMock,
    ) -> None:
        """7. All Flags: Correctly handles all flags enabled simultaneously."""
        mock_args = Namespace(incremental=True, debug=True, dry_run=True)
        mock_parse_args.return_value = mock_args
        mock_config = GlocalConfig(providers={"mock": ProviderSettings()})
        mock_load_config.return_value = mock_config

        main()

        mock_setup_logging.assert_called_once_with(version=__version__, debug=True)
        mock_run_tasks.assert_called_once_with(mock_config, incremental=True, dry_run=True, debug=True)

    @patch("glocaltext.__main__._load_config")
    @patch("glocaltext.__main__._parse_args")
    def test_main_parse_args_exception(
        self,
        mock_parse_args: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """8. Parse Args Error: Handles exceptions during argument parsing."""
        mock_parse_args.side_effect = SystemExit(2)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 2
        mock_load_config.assert_not_called()


if __name__ == "__main__":
    unittest.main()
