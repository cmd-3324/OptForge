"""``envcheck``: inspect environment variables without leaking secrets."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.text import Text

from optforge.core.cli import ErrorBoundary
from optforge.core.console import ConsoleIO
from optforge.core.version import get_version
from optforge.envcheck.models import EnvEntry, OutputFormat
from optforge.envcheck.service import EnvironmentService

app = typer.Typer(
    name="envcheck",
    help="Inspect environment variables and runtime configuration. Secrets are redacted by default.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = ConsoleIO()


def _service() -> EnvironmentService:
    return EnvironmentService()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"envcheck (optforge {get_version()})")
        raise typer.Exit()


def _render_table(entries: list[EnvEntry]) -> None:
    table = console.table(
        "Environment variables",
        [("Key", {"style": "cyan", "no_wrap": True}), ("Value", {})],
    )
    for entry in entries:
        value = Text(entry.value, style="yellow" if entry.redacted else "")
        table.add_row(console.cell(entry.key), value)
    console.print(table)
    if any(entry.redacted for entry in entries):
        console.hint("Sensitive values are masked. Pass --show-secrets to reveal them.")


@app.callback(invoke_without_command=True)
def main(
    prefix: Annotated[
        str | None,
        typer.Option("--prefix", "-p", help="Only show variables starting with this prefix."),
    ] = None,
    include_hidden: Annotated[
        bool,
        typer.Option(
            "--include-hidden/--no-include-hidden",
            help="Include variables whose names begin with an underscore.",
        ),
    ] = True,
    show_secrets: Annotated[
        bool,
        typer.Option("--show-secrets", help="Reveal values that look sensitive."),
    ] = False,
    output: Annotated[
        OutputFormat,
        typer.Option("--format", "-f", case_sensitive=False, help="Output format."),
    ] = OutputFormat.table,
    as_json: Annotated[
        bool, typer.Option("--json", help="Alias for --format json.")
    ] = False,
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
    """List environment variables, redacting secrets by default."""
    with ErrorBoundary(console):
        entries = _service().entries(
            prefix=prefix,
            include_hidden=include_hidden,
            redact=not show_secrets,
        )

    chosen = OutputFormat.json if as_json else output
    if chosen is OutputFormat.json:
        console.json([entry.to_dict() for entry in entries])
    elif chosen is OutputFormat.dotenv:
        console.text(_service().to_dotenv(entries))
    else:
        _render_table(entries)


if __name__ == "__main__":
    app()
