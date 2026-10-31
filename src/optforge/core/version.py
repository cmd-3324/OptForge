"""Version resolution that works from an installed wheel and a source checkout."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

FALLBACK_VERSION = "0.2.0"


def get_version(distribution: str = "optforge") -> str:
    """Return the installed distribution version, or the source-tree fallback."""
    try:
        return version(distribution)
    except PackageNotFoundError:
        return FALLBACK_VERSION
