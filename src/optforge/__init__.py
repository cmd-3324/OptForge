"""OptForge: cross-platform developer utilities with a stable, scriptable CLI."""

from __future__ import annotations

from optforge.core.version import get_version

__version__ = get_version()


def main() -> None:
    """Entry point for the ``optforge`` dispatcher."""
    from optforge.cli import app

    app()


__all__ = ["__version__", "main"]
