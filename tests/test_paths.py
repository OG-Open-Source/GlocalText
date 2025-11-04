"""Tests for the path management module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from glocaltext.paths import (
    CONFIG_FILE_NAMES,
    OGOS_SUBDIR,
    ensure_dir_exists,
    find_project_root,
    get_cache_dir,
    get_config_file_path,
    get_log_dir,
    get_report_dir,
)


@pytest.fixture(autouse=True)
def clear_lru_caches() -> None:
    """Clear LRU caches before each test."""
    find_project_root.cache_clear()


def test_find_project_root_success(tmp_path: Path) -> None:
    """Verify project root is found when the anchor directory exists."""
    project_root = tmp_path
    ogos_dir = project_root / OGOS_SUBDIR / "configs"
    ogos_dir.mkdir(parents=True, exist_ok=True)
    # CORRECT: Use the first element from the list
    (ogos_dir / CONFIG_FILE_NAMES[0]).touch()

    # Start searching from a subdirectory to test the upward search
    search_start_dir = ogos_dir / "level1"
    search_start_dir.mkdir()

    with patch("pathlib.Path.cwd", return_value=search_start_dir):
        assert find_project_root() == project_root


def test_find_project_root_failure_no_anchor(tmp_path: Path) -> None:
    """Verify FileNotFoundError is raised when no anchor directory is found."""
    with patch("pathlib.Path.cwd", return_value=tmp_path), pytest.raises(FileNotFoundError, match="Could not find a configuration file"):
        find_project_root()


def test_get_config_file_path_success(tmp_path: Path) -> None:
    """Verify the correct config file path is returned."""
    project_root = tmp_path
    config_dir = project_root / OGOS_SUBDIR / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    # CORRECT: Use the first element from the list
    config_file = config_dir / CONFIG_FILE_NAMES[0]
    config_file.touch()

    with patch("glocaltext.paths.find_project_root", return_value=project_root):
        assert get_config_file_path() == config_file


def test_get_config_file_path_disappears(tmp_path: Path) -> None:
    """Verify an error is raised if the config file vanishes after root is found."""
    project_root = tmp_path
    config_dir = project_root / OGOS_SUBDIR / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)
    # NOTE: We do not create the config file here.

    with patch("glocaltext.paths.find_project_root", return_value=project_root), pytest.raises(FileNotFoundError, match="Configuration file disappeared"):
        get_config_file_path()


def test_directory_getters(tmp_path: Path) -> None:
    """Verify that directory getter functions return correct paths."""
    with patch("glocaltext.paths.find_project_root", return_value=tmp_path):
        assert get_log_dir() == tmp_path / OGOS_SUBDIR / "logs"
        assert get_report_dir() == tmp_path / OGOS_SUBDIR / "reports"
        assert get_cache_dir() == tmp_path / OGOS_SUBDIR / "caches"


def test_ensure_dir_exists(tmp_path: Path) -> None:
    """Verify that a directory is created if it does not exist."""
    dir_path = tmp_path / "new_dir" / "sub_dir"
    assert not dir_path.exists()

    # Create the directory
    ensure_dir_exists(dir_path)
    assert dir_path.is_dir()

    # Call it again to ensure it doesn't fail if the directory already exists
    ensure_dir_exists(dir_path)
