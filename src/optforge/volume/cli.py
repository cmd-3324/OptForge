"""``vol``: get or set the default output volume.

Exit codes
    0  the volume was read or changed successfully
    2  invalid usage (raised by Typer)
    3  the volume could not be read or changed
"""

from __future__ import annotations

from typing import Annotated, Any

import typer
from rich.text import Text

from optforge.core.cli import ErrorBoundary
from optforge.core.console import ConsoleIO
from optforge.core.version import get_version
from optforge.volume.core import MAX_VOLUME, MIN_VOLUME, VolumeController

app = typer.Typer(
    name="vol",
    help="Get or set the default output volume.",
    epilog="Exit codes: 0 ok | 2 bad usage | 3 could not run",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = ConsoleIO()

LevelArg = Annotated[
    int,
    typer.Argument(
        min=MIN_VOLUME,
        max=MAX_VOLUME,
        metavar="PERCENT",
        show_default=False,
        help="Volume percentage (0-100).",
    ),
]
StepArg = Annotated[
    int,
    typer.Argument(
        min=1,
        max=MAX_VOLUME,
        metavar="STEP",
        show_default=True,
        help="Amount to change (1-100).",
    ),
]
QuietOpt = Annotated[bool, typer.Option("--quiet", "-q", help="Print nothing; use the exit code only.")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"vol (optforge {get_version()})")
        raise typer.Exit()


@app.callback()
def main(
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
    pass


def _controller() -> VolumeController:
    return VolumeController()


def _report(level: int, *, json_output: bool, quiet: bool, reading: bool, muted: bool = False) -> None:
    if quiet:
        return
    if json_output:
        payload: dict[str, Any] = {"volume": level}
        if reading:
            payload["muted"] = muted
        console.json(payload)
        return
    if reading:
        suffix = " (muted)" if muted else ""
        console.print(Text(f"Volume: {level}%{suffix}", style="cyan"))
    else:
        console.print(Text(f"Volume set to {level}%.", style="green"))


def _report_mute(muted: bool, *, json_output: bool, quiet: bool) -> None:
    if quiet:
        return
    if json_output:
        console.json({"muted": muted})
        return
    console.print(Text("Muted." if muted else "Unmuted.", style="green"))


def _show(*, json_output: bool, quiet: bool) -> None:
    with ErrorBoundary(console):
        controller = _controller()
        current = controller.get()
        muted = controller.is_muted()
    _report(current, json_output=json_output, quiet=quiet, reading=True, muted=muted)


@app.command("on")
def set_on(
    level: LevelArg,
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Set the output volume to a percentage (0-100)."""
    with ErrorBoundary(console):
        applied = _controller().set(level)
    _report(applied, json_output=json_output, quiet=quiet, reading=False)


@app.command("full")
def set_full(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Set the output volume to 100%."""
    with ErrorBoundary(console):
        applied = _controller().full()
    _report(applied, json_output=json_output, quiet=quiet, reading=False)


@app.command("none")
def set_none(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Set the output volume to 0%."""
    with ErrorBoundary(console):
        applied = _controller().none()
    _report(applied, json_output=json_output, quiet=quiet, reading=False)


@app.command("up")
def volume_up(
    step: StepArg = 5,
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Increase the output volume by STEP (default 5)."""
    with ErrorBoundary(console):
        applied = _controller().up(step)
    _report(applied, json_output=json_output, quiet=quiet, reading=False)


@app.command("down")
def volume_down(
    step: StepArg = 5,
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Decrease the output volume by STEP (default 5)."""
    with ErrorBoundary(console):
        applied = _controller().down(step)
    _report(applied, json_output=json_output, quiet=quiet, reading=False)


@app.command("mute")
def mute(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Mute the default output."""
    with ErrorBoundary(console):
        muted = _controller().mute()
    _report_mute(muted, json_output=json_output, quiet=quiet)


@app.command("unmute")
def unmute(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Unmute the default output."""
    with ErrorBoundary(console):
        muted = _controller().unmute()
    _report_mute(muted, json_output=json_output, quiet=quiet)


@app.command("toggle")
def toggle(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Toggle mute on the default output."""
    with ErrorBoundary(console):
        muted = _controller().toggle_mute()
    _report_mute(muted, json_output=json_output, quiet=quiet)


@app.command("get")
def get_volume(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Show the current output volume."""
    _show(json_output=json_output, quiet=quiet)


@app.command("status")
def status(
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
) -> None:
    """Show the current output volume (alias for get)."""
    _show(json_output=json_output, quiet=quiet)


if __name__ == "__main__":
    app()
