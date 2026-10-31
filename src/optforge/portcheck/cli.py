"""``portcheck``: inspect listening ports, test bindability, check connectivity.

Exit codes
    0  the answer is yes (free / found / connected / reached)
    1  the answer is no (in use / missing / unreachable / timed out)
    2  invalid usage (raised by Typer)
    3  the check could not run (permission denied, OS error)
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Annotated, Any

import typer
from rich.text import Text

from optforge.core.cli import ErrorBoundary, ExitCode
from optforge.core.console import ConsoleIO
from optforge.core.version import get_version
from optforge.portcheck.models import Listener, PortState, SortKey
from optforge.portcheck.service import DEFAULT_HOST, PortService

app = typer.Typer(
    name="portcheck",
    help="Inspect listening ports, find their owners, and test connectivity.",
    epilog="Exit codes: 0 yes/ok | 1 no | 2 bad usage | 3 could not run",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = ConsoleIO()
_PERMISSION_HINT = "Run as Administrator (Windows) or with sudo (Linux/macOS)."

PortArg = Annotated[
    int,
    typer.Argument(min=1, max=65535, metavar="PORT", show_default=False, help="Port number (1-65535)."),
]
HostOpt = Annotated[str, typer.Option("--host", "-H", help="Address used for bind and connect probes.")]
QuietOpt = Annotated[bool, typer.Option("--quiet", "-q", help="Print nothing; use the exit code only.")]
JsonOpt = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")]


def _service() -> PortService:
    """Construct the service lazily so ``--help`` and ``--version`` stay instant."""
    return PortService()


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"portcheck (optforge {get_version()})")
        raise typer.Exit()


@contextmanager
def _guard() -> Iterator[None]:
    with ErrorBoundary(console, permission_hint=_PERMISSION_HINT):
        yield


def _scope_text(scope: str) -> Text:
    style = {"all interfaces": "yellow", "local only": "green"}.get(scope, "")
    return Text(scope, style=style)


def _table(rows: list[Listener], title: str | None) -> Any:
    table = console.table(
        title,
        [
            ("Port", {"justify": "right", "style": "cyan", "no_wrap": True}),
            ("Address", {"no_wrap": True}),
            ("Scope", {"no_wrap": True}),
            ("PID", {"justify": "right", "no_wrap": True}),
            ("Process", {}),
        ],
    )
    for row in rows:
        table.add_row(
            str(row.port),
            console.cell(row.address),
            _scope_text(row.scope),
            "-" if row.pid is None else str(row.pid),
            console.cell(row.process),
        )
    return table


def _hint_hidden(rows: list[Listener]) -> None:
    if any(row.pid is None for row in rows):
        console.hint("Some process details are hidden. Run as Administrator / sudo to see them.")


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


@app.command("list")
def list_ports(
    sort: Annotated[
        SortKey,
        typer.Option("--sort", "-s", case_sensitive=False, help="Column to sort by."),
    ] = SortKey.port,
    limit: Annotated[
        int | None, typer.Option("--limit", "-n", min=1, help="Show at most N rows.")
    ] = None,
    process: Annotated[
        str | None,
        typer.Option("--process", "-p", metavar="TEXT", help="Only rows whose process name contains TEXT."),
    ] = None,
    exposed: Annotated[
        bool, typer.Option("--exposed", help="Only ports reachable from other machines.")
    ] = False,
    as_json: JsonOpt = False,
) -> None:
    """List listening TCP ports."""
    with _guard():
        rows = _service().query(sort=sort, limit=limit, process=process, exposed=exposed)

    if as_json:
        console.json([row.to_dict() for row in rows])
        return
    if not rows:
        console.text("No listening TCP ports match.")
        return

    console.print(_table(rows, "Listening TCP ports"))
    _hint_hidden(rows)


@app.command()
def check(
    port: PortArg,
    host: HostOpt = DEFAULT_HOST,
    quiet: QuietOpt = False,
    as_json: JsonOpt = False,
    expect: Annotated[
        PortState,
        typer.Option("--expect", case_sensitive=False, help="Exit 0 only if the port matches this state."),
    ] = PortState.free,
) -> None:
    """Check whether a port is free or in use."""
    with _guard():
        result = _service().check(port, host)

    if as_json:
        console.json(result.to_dict())
    elif not quiet:
        if result.in_use:
            console.success(f"Port {port} is in use.")
            if result.owners:
                console.print(_table(result.owners, None))
                _hint_hidden(result.owners)
        else:
            console.success(f"Port {port} is free on {host}.")

    matched = result.in_use if expect is PortState.used else not result.in_use
    raise typer.Exit(ExitCode.OK if matched else ExitCode.NO)


@app.command()
def find(port: PortArg, as_json: JsonOpt = False) -> None:
    """Show the process listening on a port."""
    with _guard():
        owners = _service().find(port)

    if as_json:
        console.json([owner.to_dict() for owner in owners])
    elif owners:
        console.print(_table(owners, f"Port {port}"))
        _hint_hidden(owners)
    else:
        console.text(f"Nothing is listening on port {port}.")
    raise typer.Exit(ExitCode.OK if owners else ExitCode.NO)


@app.command()
def connect(
    host: Annotated[str, typer.Argument(metavar="HOST", help="Hostname or IP address.")],
    port: PortArg,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", min=0.1, help="Seconds to wait.")
    ] = 3.0,
    quiet: QuietOpt = False,
    as_json: JsonOpt = False,
) -> None:
    """Test a TCP connection to a host and port."""
    with _guard():
        result = _service().connect(host, port, timeout)

    if as_json:
        console.json({"host": host, "port": port, **result.to_dict()})
    elif not quiet:
        target = f"{host}:{port}"
        if result.ok:
            took = f" in {result.seconds * 1000:.0f} ms" if result.seconds is not None else ""
            console.success(f"Connected to {target}{took}.")
        else:
            console.error(f"Could not connect to {target}: {result.error or 'unknown error'}")
    raise typer.Exit(ExitCode.OK if result.ok else ExitCode.NO)


@app.command()
def wait(
    port: PortArg,
    until: Annotated[
        PortState,
        typer.Option("--until", "-u", case_sensitive=False, help="Wait until the port is in use or free."),
    ] = PortState.used,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", min=0.1, help="Give up after N seconds.")
    ] = 30.0,
    interval: Annotated[
        float, typer.Option("--interval", "-i", min=0.05, help="Seconds between checks.")
    ] = 0.5,
    host: HostOpt = DEFAULT_HOST,
    quiet: QuietOpt = False,
    as_json: JsonOpt = False,
) -> None:
    """Wait until a port is in use or free."""
    spinner = nullcontext() if quiet or as_json else console.status(f"Waiting for port {port} to be {until.value}...")
    with _guard(), spinner:
        result = _service().wait(port, until, timeout=timeout, interval=interval, host=host)

    if as_json:
        console.json(result.to_dict())
    elif not quiet:
        if result.reached:
            console.success(f"Port {port} is {until.value}.")
        else:
            console.error(f"Timed out after {timeout:g}s waiting for port {port} to be {until.value}.")
    raise typer.Exit(ExitCode.OK if result.reached else ExitCode.NO)


if __name__ == "__main__":
    app()
