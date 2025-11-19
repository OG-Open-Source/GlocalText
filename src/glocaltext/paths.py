"""Manages the discovery and provision of fixed paths for the GlocalText application."""
# src/glocaltext/paths.py

from functools import lru_cache
from pathlib import Path
from typing import Final

CONFIG_FILE_NAMES: Final[list[str]] = ["main.yaml", "main.yml"]
OGOS_SUBDIR: Final[Path] = Path(".ogos") / "glocaltext"


@lru_cache(maxsize=1)
def find_project_root(start_path: Path | None = None) -> Path:
    """
    Find the project root by searching upwards from the start_path (or CWD) for the '.ogos' anchor.

    The directory containing the '.ogos' directory is considered the project root.

    Args:
        start_path: The path to start searching from. Defaults to CWD.

    Raises:
        FileNotFoundError: If the anchor config file is not found in any parent directory.

    """
    current_dir = (start_path or Path.cwd()).resolve()
    for parent in [current_dir, *current_dir.parents]:
        config_dir = parent / OGOS_SUBDIR / "configs"
        if config_dir.is_dir():
            for config_file in CONFIG_FILE_NAMES:
                if (config_dir / config_file).is_file():
                    return parent

    msg = f"Could not find a configuration file ({' or '.join(CONFIG_FILE_NAMES)}) in an '{OGOS_SUBDIR / 'configs'}' directory from the current location upwards. Please run glocaltext from within a configured project."
    raise FileNotFoundError(msg)


def get_config_file_path(root_path: Path | None = None) -> Path:
    """Find and return the full path to the main.yaml or main.yml config file."""
    root = find_project_root(root_path)
    config_dir = root / OGOS_SUBDIR / "configs"
    for config_file in CONFIG_FILE_NAMES:
        path = config_dir / config_file
        if path.is_file():
            return path
    # This part should be unreachable if find_project_root() succeeds.
    msg = "Configuration file disappeared after being found."
    raise FileNotFoundError(msg)


def get_log_dir(root_path: Path | None = None) -> Path:
    """Return the path to the log directory."""
    return find_project_root(root_path) / OGOS_SUBDIR / "logs"


def get_report_dir(root_path: Path | None = None) -> Path:
    """Return the path to the report directory."""
    return find_project_root(root_path) / OGOS_SUBDIR / "reports"


def get_cache_dir(root_path: Path | None = None) -> Path:
    """Return the path to the cache directory."""
    return find_project_root(root_path) / OGOS_SUBDIR / "caches"


def ensure_dir_exists(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
