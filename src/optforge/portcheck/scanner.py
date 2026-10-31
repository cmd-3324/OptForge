"""Listening-socket discovery built on psutil."""

from __future__ import annotations

import socket
from collections.abc import Callable, Iterable
from typing import Any

import psutil

from optforge.core.errors import PermissionDenied
from optforge.core.processes import ProcessNameResolver
from optforge.portcheck.models import Listener

ConnectionProvider = Callable[..., Iterable[Any]]


class ListenerScanner:
    """Turn the operating system's socket table into :class:`Listener` rows.

    The provider is injectable so the scanner can be tested without touching the
    real socket table.
    """

    def __init__(
        self,
        provider: ConnectionProvider = psutil.net_connections,
        resolver: ProcessNameResolver | None = None,
    ) -> None:
        self._provider = provider
        self._resolver = resolver or ProcessNameResolver()

    def scan(self) -> list[Listener]:
        """Return every listening TCP socket, de-duplicated and sorted by port."""
        try:
            connections = list(self._provider(kind="tcp"))
        except psutil.AccessDenied as exc:
            raise PermissionDenied(
                "The operating system denied access to the socket table."
            ) from exc
        except OSError as exc:
            raise PermissionDenied(f"Could not read the socket table: {exc}") from exc

        rows: list[Listener] = []
        seen: set[tuple[int, str, int | None]] = set()
        for connection in connections:
            if getattr(connection, "status", None) != psutil.CONN_LISTEN:
                continue
            local = getattr(connection, "laddr", None)
            if local is None:
                continue

            family = getattr(connection, "family", socket.AF_INET)
            port = int(local.port)
            address = str(getattr(local, "ip", "") or ("::" if family == socket.AF_INET6 else "0.0.0.0"))
            pid = getattr(connection, "pid", None)
            key = (port, address, pid)
            if key in seen:
                continue
            seen.add(key)

            rows.append(
                Listener(
                    port=port,
                    address=address,
                    family="ipv6" if family == socket.AF_INET6 else "ipv4",
                    pid=pid,
                    process=self._resolver.name(pid),
                )
            )

        rows.sort(key=lambda row: (row.port, row.address, row.pid or 0))
        return rows

    def owners(self, port: int) -> list[Listener]:
        return [row for row in self.scan() if row.port == port]
