"""GlocalText: A Python-based tool for automated localization."""

import importlib.metadata


def _get_version() -> str:
    """
    Retrieve the package version from metadata.

    Returns:
        The version string, or a development version if not installed.

    """
    try:
        # Dynamically get the version from the installed package
        return importlib.metadata.version("GlocalText")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for when the package is not installed, e.g., in a development environment
        return "0.0.0-dev"


__version__ = _get_version()
