"""Bounded-timeout TCP connection attempts."""

from __future__ import annotations

import socket
import time
from collections.abc import Callable

from optforge.core.errors import OptForgeError
from optforge.core.net import resolve_endpoints_with_timeout
from optforge.portcheck.models import ConnectResult

Resolver = Callable[[str, int, float], list]


class Connector:
    """Connect to ``host:port`` while honouring one wall-clock deadline."""

    def __init__(
        self,
        resolver: Resolver = resolve_endpoints_with_timeout,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._resolver = resolver
        self._clock = clock

    def connect(self, host: str, port: int, timeout: float) -> ConnectResult:
        start = self._clock()
        try:
            endpoints = self._resolver(host, port, timeout)
        except OptForgeError as exc:
            return ConnectResult(ok=False, error=str(exc))

        last_error = "no endpoint accepted the connection"
        for endpoint in endpoints:
            remaining = timeout - (self._clock() - start)
            if remaining <= 0:
                last_error = f"timed out after {timeout:g}s"
                break
            try:
                with socket.socket(endpoint.family, socket.SOCK_STREAM) as sock:
                    sock.settimeout(remaining)
                    sock.connect(endpoint.sockaddr)
                return ConnectResult(
                    ok=True,
                    seconds=self._clock() - start,
                    endpoint=endpoint.label(),
                )
            except OSError as exc:
                last_error = _reason(exc)

        return ConnectResult(ok=False, error=last_error)


def _reason(exc: OSError) -> str:
    if isinstance(exc, ConnectionRefusedError):
        return "connection refused"
    if isinstance(exc, TimeoutError):
        return "timed out"
    return exc.strerror or str(exc)
