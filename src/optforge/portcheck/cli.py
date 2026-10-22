"""portcheck: inspect listening ports, test whether a port is free, check connectivity.

This module is the command-line layer only: it parses arguments, calls
``optforge.portcheck.core`` and prints results. All real work lives in core.py.

Exit codes
    0  success, or the answer is "yes" (port free / process found / host reachable)
    1  the check ran fine but the answer is "no"
    2  invalid usage (raised by Typer)
    3  runtime error (permission denied, OS error)
"""
import dataclasses
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from enum import Enum, IntEnum
from typing import TYPE_CHECKING, Annotated, Any

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

if TYPE_CHECKING:
    from optforge.portcheck.core import Listener


class ExitCode(IntEnum):
    OK = 0
    NO = 1
    ERROR = 3


class SortKey(str, Enum):
    port = "port"
    pid = "pid"
    process = "process"
    address = "address"


class Until(str, Enum):
    free = "free"
    used = "used"


app = typer.Typer(
    name="portcheck",
    help="Inspect listening ports, find who owns them, and test connectivity.",
    epilog="Exit codes: 0 yes/ok | 1 no (in use, nothing found, unreachable) "
    "| 2 bad usage | 3 error",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()
err_console = Console(stderr=True)

# Reusable parameter definitions: one place to change wording or limits.
PortArg = Annotated[
    int,
    typer.Argument(
        min=1, max=65535, metavar="PORT", show_default=False,
        help="Port number (1-65535).",
    ),
]
HostOpt = Annotated[
    str, typer.Option("--host", "-H", help="Address used for the bind test.")
]
QuietOpt = Annotated[
    bool, typer.Option("--quiet", "-q", help="Print nothing; use the exit code only.")
]
JsonOpt = Annotated[
    bool, typer.Option("--json", help="Print machine-readable JSON.")
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _core() -> Any:
    """Import core lazily so --help and --version stay instant (psutil is slow)."""
    from optforge.portcheck import core

    return core


@contextmanager
def _guard() -> Iterator[None]:
    """Turn expected core errors into a clean message and exit code 3."""
    core = _core()
    try:
        yield
    except core.PermissionDenied as exc:
        err_console.print(f"[red]error:[/red] {escape(str(exc))}")
        err_console.print(
            "[dim]hint: run as Administrator (Windows) or with sudo (Linux/macOS).[/dim]"
        )
        raise typer.Exit(ExitCode.ERROR) from exc
    except core.PortCheckError as exc:
        err_console.print(f"[red]error:[/red] {escape(str(exc))}")
        raise typer.Exit(ExitCode.ERROR) from exc


def _emit_json(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2))


def _scope(address: str) -> str:
    """Who can reach a listener: this machine only, or the network."""
    if address in ("", "0.0.0.0", "::", "*"):
        return "all interfaces"
    if address == "::1" or address.startswith("127."):
        return "local only"
    return "specific"


def _as_dict(row: "Listener") -> dict[str, Any]:
    return {**dataclasses.asdict(row), "scope": _scope(row.address)}


def _hint_hidden(rows: "list[Listener]") -> None:
    if any(r.pid is None for r in rows):
        err_console.print(
            "[dim]Some process details are hidden. "
            "Run as Administrator / sudo to see them.[/dim]"
        )


def _listeners_table(rows: "list[Listener]", title: str | None) -> Table:
    table = Table(title=title, title_justify="left", header_style="bold")
    table.add_column("Port", justify="right", style="cyan", no_wrap=True)
    table.add_column("Address", no_wrap=True)
    table.add_column("Scope", no_wrap=True)
    table.add_column("PID", justify="right", no_wrap=True)
    table.add_column("Process")
    for r in rows:
        scope = _scope(r.address)
        colour = {"all interfaces": "yellow", "local only": "green"}.get(scope, "")
        table.add_row(
            str(r.port),
            r.address,
            f"[{colour}]{scope}[/{colour}]" if colour else scope,
            "-" if r.pid is None else str(r.pid),
            escape(r.process),
        )
    return table


def _owners(port: int) -> "list[Listener]":
    return [r for r in _core().get_listeners() if r.port == port]


def _probe(port: int, host: str) -> "tuple[bool, list[Listener]]":
    """Return (in_use, owners).

    Two independent signals are combined: the socket list (who listens) and a
    bind test (can we take it). Either one is enough to call the port in use,
    which keeps the answer right when process listing is blocked by permissions.
    """
    core = _core()
    try:
        owners = _owners(port)
    except core.PortCheckError:
        owners = []
    bindable = core.can_bind(port, host)
    return (bool(owners) or not bindable), owners


# --------------------------------------------------------------------------- #
# App-level options
# --------------------------------------------------------------------------- #
def _version_callback(value: bool) -> None:
    if value:
        from importlib.metadata import version  # lazy: only needed here

        typer.echo(f"portcheck (optforge {version('optforge')})")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version", "-V", callback=_version_callback, is_eager=True,
            help="Show the version and exit.",
        ),
    ] = None,
) -> None:
    pass


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
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
        typer.Option(
            "--process", "-p", metavar="TEXT",
            help="Only rows whose process name contains TEXT (case-insensitive).",
        ),
    ] = None,
    exposed: Annotated[
        bool,
        typer.Option("--exposed", help="Only ports reachable from other machines."),
    ] = False,
    as_json: JsonOpt = False,
) -> None:
    """List every listening TCP port with its owning process.

    [bold]Examples[/bold]
      portcheck list
      portcheck list -s process -n 10
      portcheck list --exposed
      portcheck list -p python --json
    """
    with _guard():
        rows = _core().get_listeners()

    if process:
        needle = process.lower()
        rows = [r for r in rows if needle in r.process.lower()]
    if exposed:
        rows = [r for r in rows if _scope(r.address) == "all interfaces"]

    keys = {
        SortKey.port: lambda r: r.port,
        SortKey.pid: lambda r: (r.pid is None, r.pid or 0),
        SortKey.process: lambda r: r.process.lower(),
        SortKey.address: lambda r: r.address,
    }
    rows = sorted(rows, key=keys[sort])
    total = len(rows)
    if limit is not None:
        rows = rows[:limit]

    if as_json:
        _emit_json([_as_dict(r) for r in rows])
        return
    if not rows:
        console.print("No listening TCP ports match.")
        return

    console.print(_listeners_table(rows, "Listening TCP ports"))
    if total > len(rows):
        console.print(f"[dim]Showing {len(rows)} of {total} (change with -n).[/dim]")
    _hint_hidden(rows)


@app.command()
def check(
    port: PortArg,
    host: HostOpt = "127.0.0.1",
    quiet: QuietOpt = False,
    as_json: JsonOpt = False,
) -> None:
    """Is PORT free? Exit code 0 if free, 1 if in use.

    [bold]Examples[/bold]
      portcheck check 8000
      portcheck check 8000 -q && uvicorn app:app --port 8000
    """
    with _guard():
        in_use, owners = _probe(port, host)

    if as_json:
        _emit_json(
            {"port": port, "host": host, "in_use": in_use,
             "owners": [_as_dict(o) for o in owners]}
        )
    elif not quiet:
        if in_use:
            console.print(f"[red]Port {port} is in use.[/red]")
            if owners:
                console.print(_listeners_table(owners, None))
                _hint_hidden(owners)
        else:
            console.print(f"[green]Port {port} is free[/green] on {escape(host)}.")
    raise typer.Exit(ExitCode.NO if in_use else ExitCode.OK)


@app.command()
def find(port: PortArg, as_json: JsonOpt = False) -> None:
    """Show which process is listening on PORT. Exit code 1 if nothing is.

    [bold]Example[/bold]
      portcheck find 5432
    """
    with _guard():
        owners = _owners(port)

    if as_json:
        _emit_json([_as_dict(o) for o in owners])
    elif owners:
        console.print(_listeners_table(owners, f"Port {port}"))
        _hint_hidden(owners)
    else:
        console.print(f"Nothing is listening on port {port}.")
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
    """Test whether HOST:PORT accepts a TCP connection. Exit code 1 if not.

    [bold]Examples[/bold]
      portcheck connect localhost 5432
      portcheck connect example.com 443 -t 5
    """
    with _guard():
        result = _core().can_connect(host, port, timeout)

    if as_json:
        _emit_json({"host": host, "port": port, **dataclasses.asdict(result)})
    elif not quiet:
        target = f"{escape(host)}:{port}"
        if result.ok:
            took = f" in {result.seconds * 1000:.0f} ms" if result.seconds else ""
            console.print(f"[green]Connected to {target}[/green]{took}.")
        else:
            console.print(
                f"[red]Could not connect to {target}[/red]: "
                f"{escape(result.error or 'unknown error')}"
            )
    raise typer.Exit(ExitCode.OK if result.ok else ExitCode.NO)


@app.command()
def wait(
    port: PortArg,
    until: Annotated[
        Until,
        typer.Option(
            "--until", "-u", case_sensitive=False,
            help="Wait until the port is in use or free.",
        ),
    ] = Until.used,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", min=0.1, help="Give up after N seconds.")
    ] = 30.0,
    interval: Annotated[
        float, typer.Option("--interval", "-i", min=0.05, help="Seconds between checks.")
    ] = 0.5,
    host: HostOpt = "127.0.0.1",
    quiet: QuietOpt = False,
) -> None:
    """Block until PORT is in use (server is up) or free. Exit code 1 on timeout.

    [bold]Examples[/bold]
      portcheck wait 8000 -t 60
      portcheck wait 8000 --until free
    """
    deadline = time.monotonic() + timeout
    reached = False
    spinner = (
        nullcontext()
        if quiet
        else console.status(f"Waiting for port {port} to be {until.value}...")
    )
    with _guard(), spinner:
        while True:
            in_use, _ = _probe(port, host)
            if in_use == (until is Until.used):
                reached = True
                break
            if time.monotonic() >= deadline:
                break
            time.sleep(interval)

    if not quiet:
        if reached:
            console.print(f"[green]Port {port} is {until.value}.[/green]")
        else:
            console.print(
                f"[red]Timed out after {timeout:g}s waiting for port {port} "
                f"to be {until.value}.[/red]"
            )
    raise typer.Exit(ExitCode.OK if reached else ExitCode.NO)


if __name__ == "__main__":
    app()