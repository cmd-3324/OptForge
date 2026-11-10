"""``killNotif``: clear Windows toast notifications.

Exit codes
    0  the command ran successfully (even when nothing needed clearing)
    2  invalid usage (raised by Typer)
    3  the operation could not run (wrong OS, missing helper, PowerShell error)
"""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from rich.text import Text

from optforge.core.cli import ErrorBoundary
from optforge.core.console import ConsoleIO
from optforge.core.errors import OperationFailed
from optforge.core.version import get_version

app = typer.Typer(
    name="killNotif",
    help="Clear Windows toast notifications, optionally for a single app.",
    epilog="Exit codes: 0 ok | 2 bad usage | 3 could not run",
    no_args_is_help=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = ConsoleIO()

AumidOpt = Annotated[
    str | None,
    typer.Option(
        "--aumid",
        "-a",
        metavar="AUMID",
        help="Only clear notifications from this AppUserModelID.",
    ),
]
QuietOpt = Annotated[
    bool, typer.Option("--quiet", "-q", help="Print nothing; use the exit code only.")
]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")]


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"killNotif (optforge {get_version()})")
        raise typer.Exit()


def _clear(aumid: str | None) -> int:
    """Import lazily so ``--help`` and ``--version`` stay fast."""
    from optforge.killNotif.core import clear_notifications

    return clear_notifications(aumid)


def _run(aumid: str | None) -> int:
    if sys.platform != "win32":
        raise OperationFailed("killNotif requires Windows 10/11 (WinRT toast history).")

    try:
        return _clear(aumid)
    except FileNotFoundError as exc:
        raise OperationFailed(f"{exc} Ensure PowerShell 5.1+ is installed.") from exc
    except RuntimeError as exc:
        raise OperationFailed(str(exc)) from exc
    except ValueError as exc:
        raise OperationFailed(f"unexpected helper output: {exc}") from exc


@app.command()
def main(
    aumid: AumidOpt = None,
    json_output: JsonOpt = False,
    quiet: QuietOpt = False,
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
    """Clear toast notifications from the Windows Action Center."""
    target = aumid.strip() if aumid else None

    with ErrorBoundary(console):
        cleared = _run(target)

    if quiet:
        return
    if json_output:
        console.json({"aumid": target, "cleared": cleared})
        return
    if cleared == 0:
        console.print(Text("No notifications to clear.", style="dim"))
    elif target:
        console.print(Text(f"Cleared {cleared} sender(s) matching {target}.", style="green"))
    else:
        console.print(Text(f"Cleared {cleared} sender(s).", style="green"))


if __name__ == "__main__":
    app()
