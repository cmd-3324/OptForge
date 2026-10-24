"""Environment variable CLI."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from optforge.envcheck.core import get_environment

app = typer.Typer(
    name="envcheck",
    help="Inspect environment variables and runtime configuration.",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def list_env(
    prefix: str | None = typer.Option(None, "--prefix", "-p", help="Only show variables starting with this prefix."),
    include_hidden: bool = typer.Option(True, "--include-hidden/--no-include-hidden", help="Include variables beginning with an underscore."),
    json_output: bool = typer.Option(False, "--json", help="Print JSON instead of a table."),
) -> None:
    """List environment variables."""
    entries = get_environment(prefix=prefix, include_hidden=include_hidden)
    if json_output:
        typer.echo("[")
        for index, entry in enumerate(entries):
            comma = "," if index < len(entries) - 1 else ""
            typer.echo(f'  {{"key": {entry.key!r}, "value": {entry.value!r}}}{comma}')
        typer.echo("]")
        return

    table = Table(title="Environment variables")
    table.add_column("Key", style="cyan", no_wrap=True)
    table.add_column("Value")

    for entry in entries:
        table.add_row(entry.key, entry.value)

    console.print(table)


if __name__ == "__main__":
    app()
