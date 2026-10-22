"""Command-line interface for disk space checks."""

from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.table import Table

from optforge.diskcheck.core import get_disk_usage

app = typer.Typer(
    name="diskcheck",
    help="Inspect local disk usage and storage health.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


@app.command()
def check(path: str = ".") -> None:
    """Show disk usage for a directory or drive."""
    try:
        info = get_disk_usage(path)
    except OSError as exc:
        raise typer.BadParameter(f"Could not read disk usage for '{path}': {exc}") from exc

    table = Table(title=f"Disk usage: {info.path}")
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    table.add_row("Total", _format_bytes(info.total))
    table.add_row("Used", _format_bytes(info.used))
    table.add_row("Free", _format_bytes(info.free))
    table.add_row("Used %", f"{info.percent_used:.2f}%")

    console.print(table)


if __name__ == "__main__":
    app()
