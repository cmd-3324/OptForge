"""Version resolution that works from an installed wheel and a source checkout."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from optforge._version import __version__


def get_version(distribution: str = "optforge") -> str:
    """Return the installed distribution version, or the source-tree version."""
    try:
        return version(distribution)
    except PackageNotFoundError:
        return __version__
