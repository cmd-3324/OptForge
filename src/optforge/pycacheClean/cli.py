"""``pycache-clean``: remove ``__pycache__`` directories safely and visibly."""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.text import Text

from optforge.core.cli import ErrorBoundary, ExitCode
from optforge.core.console import ConsoleIO
from optforge.core.formatting import format_bytes
from optforge.core.version import get_version
from optforge.pycacheclean.service import CacheService

app = typer.Typer(
    name="pycache-clean",
    help="Remove Python __pycache__ directories. Skips virtualenvs by default.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = ConsoleIO()


def _service() -> CacheService:
    return CacheService()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pycache-clean (optforge {get_version()})")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    path: Annotated[str, typer.Argument(help="Directory to scan for cache directories.")] = ".",
    recursive: Annotated[
        bool, typer.Option("--recursive/--no-recursive", help="Search recursively beneath the path.")
    ] = True,
    max_depth: Annotated[
        int | None,
        typer.Option("--max-depth", min=1, help="Maximum directory depth to traverse."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-e", help="Additional directory name to skip. Repeatable."),
    ] = None,
    skip_venvs: Annotated[
        bool,
        typer.Option("--skip-venv/--include-venv", help="Skip (or include) venv and .venv trees."),
    ] = True,
    measure: Annotated[
        bool, typer.Option("--size/--no-size", help="Measure files and bytes per target.")
    ] = True,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="List what would be removed without deleting it.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Delete without asking for confirmation.")
    ] = False,
    allow_root: Annotated[
        bool, typer.Option("--allow-root", help="Permit scanning the filesystem root.")
    ] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    """Remove __pycache__ directories under a path."""
    service = _service()
    with ErrorBoundary(console):
        targets = service.scan(
            path,
            recursive=recursive,
            max_depth=max_depth,
            exclude=set(exclude or ()),
            skip_venvs=skip_venvs,
            measure=measure,
            allow_root=allow_root,
        )

    if not targets:
        if as_json:
            console.json({"dry_run": dry_run, "removed": [], "failed": [], "freed_bytes": 0})
        else:
            console.text(f"No __pycache__ directories found under {path!r}.")
        raise typer.Exit(ExitCode.OK)

    if not dry_run and not yes:
        if not sys.stdin.isatty():
            console.error("Refusing to delete without --yes in a non-interactive session.")
            raise typer.Exit(2)
        noun = "directory" if len(targets) == 1 else "directories"
        if not typer.confirm(f"Delete {len(targets)} __pycache__ {noun}?", default=False):
            console.text("Aborted; nothing was deleted.")
            raise typer.Exit(ExitCode.OK)

    report = service.remove(targets, dry_run=dry_run)

    if as_json:
        console.json(report.to_dict())
    else:
        verb = "Would remove" if dry_run else "Removed"
        console.text(f"{verb} {len(report.removed)} cache directories.")
        for target in report.removed:
            detail = f" ({target.files} files, {format_bytes(target.bytes)})" if measure else ""
            console.print(Text(f"  - {target.path}{detail}"))
        for failure in report.failed:
            console.error(f"{failure.path}: {failure.error}")
        if not dry_run:
            console.text(f"Freed {format_bytes(report.freed_bytes)}.")

    raise typer.Exit(ExitCode.OK if report.ok else ExitCode.NO)


if __name__ == "__main__":
    app()
