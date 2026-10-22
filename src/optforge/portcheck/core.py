"""Port inspection logic: the part YOU write.

cli.py depends on exactly this interface. Keep the names, signatures and
return types; fill in the bodies. Do not import typer or rich here.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

import psutil


class PortCheckError(Exception):
    """Base class for expected, user-facing failures. Message must be readable."""


class PermissionDenied(PortCheckError):
    """The OS refused to list sockets (raise this when psutil.AccessDenied occurs)."""


@dataclass(frozen=True, slots=True)
class Listener:
    port: int
    address: str  # e.g. "127.0.0.1", "0.0.0.0", "::"
    pid: int | None  # None when the OS hides it
    process: str  # process name, or "-" when unknown


@dataclass(frozen=True, slots=True)
class ConnectResult:
    ok: bool
    seconds: float | None  # time taken, when ok
    error: str | None  # short reason, when not ok


def get_listeners() -> list[Listener]:
    """Every listening TCP socket on this machine.

    Hint: psutil.net_connections(kind="tcp"), keep status == psutil.CONN_LISTEN.
    Look up names with psutil.Process(pid).name() inside try/except psutil.Error.
    Convert psutil.AccessDenied into PermissionDenied.
    """
    try:
        connections = psutil.net_connections(kind="tcp")
    except psutil.AccessDenied as exc:
        raise PermissionDenied(str(exc)) from exc

    rows: list[Listener] = []
    seen: set[tuple[int, str, int | None, str]] = set()

    for conn in connections:
        if conn.status != psutil.CONN_LISTEN or conn.laddr is None:
            continue

        port = conn.laddr.port
        address = conn.laddr.ip or "0.0.0.0"
        pid = conn.pid

        process_name = "-"
        if pid is not None:
            try:
                process_name = psutil.Process(pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                process_name = "-"

        key = (port, address, pid, process_name)
        if key in seen:
            continue
        seen.add(key)
        rows.append(Listener(port=port, address=address, pid=pid, process=process_name))

    return rows


def can_bind(port: int, host: str) -> bool:
    """True if a TCP socket can bind to host:port right now.

    Hint: socket.socket(), bind((host, port)), return False on OSError, always
    close the socket. On Windows do NOT set SO_REUSEADDR (it lets two sockets
    share a port and would make a busy port look free).
    """
    try:
        family = socket.AF_INET6 if ":" in host else socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.bind((host, port))
        except OSError:
            return False
        else:
            return True
        finally:
            sock.close()
    except OSError:
        return False


def can_connect(host: str, port: int, timeout: float) -> ConnectResult:
    """Try a TCP connection to host:port.

    Hint: socket.create_connection((host, port), timeout=timeout), time it with
    time.perf_counter(), catch OSError and put a short reason in `error`.
    """
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return ConnectResult(
                ok=True,
                seconds=time.perf_counter() - start,
                error=None,
            )
    except OSError as exc:
        return ConnectResult(
            ok=False,
            seconds=None,
            error=str(exc),
        )
