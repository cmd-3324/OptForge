"""``diskcheck``: inspect disk usage and warn on storage pressure."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.text import Text

from optforge.core.cli import ErrorBoundary, ExitCode
from optforge.core.console import ConsoleIO
from optforge.core.formatting import format_bytes, format_percent
from optforge.core.version import get_version
from optforge.diskcheck.models import DiskInfo
from optforge.diskcheck.service import DiskService

app = typer.Typer(
    name="diskcheck",
    help="Inspect disk usage and warn when storage pressure crosses a threshold.",
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = ConsoleIO()


def _service() -> DiskService:
    return DiskService()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"diskcheck (optforge {get_version()})")
        raise typer.Exit()


def _table(infos: list[DiskInfo], warn_at: float | None) -> None:
    table = console.table(
        "Disk usage",
        [
            ("Path", {"no_wrap": True}),
            ("Total", {"justify": "right"}),
            ("Used", {"justify": "right"}),
            ("Free", {"justify": "right"}),
            ("Used %", {"justify": "right"}),
        ],
    )
    for info in infos:
        pressure = warn_at is not None and info.percent_used >= warn_at
        percent = Text(format_percent(info.percent_used), style="red" if pressure else "")
        table.add_row(
            console.cell(info.path),
            format_bytes(info.total),
            format_bytes(info.used),
            format_bytes(info.free),
            percent,
        )
    console.print(table)


@app.callback(invoke_without_command=True)
def main(
    path: Annotated[str, typer.Argument(help="Directory or drive to inspect.")] = ".",
    all_volumes: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show every mounted volume instead of one path."),
    ] = False,
    warn_at: Annotated[
        float | None,
        typer.Option(
            "--warn-at",
            min=0.0,
            max=100.0,
            help="Exit 1 when used percent reaches this value.",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print machine-readable JSON."),
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
    """Show disk usage for a path or every mounted volume."""
    with ErrorBoundary(console):
        infos = _service().volumes() if all_volumes else [_service().usage(path)]

    if as_json:
        payload = [info.to_dict() for info in infos] if all_volumes else infos[0].to_dict()
        console.json(payload)
    else:
        _table(infos, warn_at)

    over_threshold = warn_at is not None and any(info.percent_used >= warn_at for info in infos)
    if over_threshold:
        if not as_json:
            console.warning(
                f"Storage pressure: at least one volume is at or above {warn_at:g}% used."
            )
        raise typer.Exit(ExitCode.NO)
    raise typer.Exit(ExitCode.OK)


if __name__ == "__main__":
    app()
