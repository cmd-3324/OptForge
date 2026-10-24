"""CLI for Python cache cleanup."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from optforge.pycacheClean.core import clean_pycache

app = typer.Typer(
    name="pycacheClean",
    help="Remove Python __pycache__ directories from a project tree.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def clean(
    path: str = typer.Argument(".", help="Directory to scan for Python cache directories."),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", help="Search recursively underneath the target path."),
    max_depth: int | None = typer.Option(None, "--max-depth", help="Maximum directory depth to traverse."),
    dry_run: bool = typer.Option(False, "--dry-run", help="List what would be removed without deleting it."),
) -> None:
    """Delete __pycache__ directories under a path."""
    removed = clean_pycache(path, recursive=recursive, max_depth=max_depth, dry_run=dry_run)
    if not removed:
        console.print(f"No __pycache__ directories found under '{path}'.")
        raise typer.Exit(0)

    if dry_run:
        console.print(f"Would remove {len(removed)} cache directory(s):")
    else:
        console.print(f"Removed {len(removed)} cache directory(s):")

    for item in removed:
        console.print(f"  - {item}")


if __name__ == "__main__":
    app()
