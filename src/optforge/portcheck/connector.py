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
        remaining_endpoints = len(endpoints)
        for endpoint in endpoints:
            remaining = timeout - (self._clock() - start)
            if remaining <= 0:
                last_error = f"timed out after {timeout:g}s"
                break
            attempt = _attempt_budget(remaining, remaining_endpoints)
            remaining_endpoints -= 1
            try:
                with socket.socket(endpoint.family, socket.SOCK_STREAM) as sock:
                    sock.settimeout(attempt)
                    sock.connect(endpoint.sockaddr)
                return ConnectResult(
                    ok=True,
                    seconds=self._clock() - start,
                    endpoint=endpoint.label(),
                )
            except OSError as exc:
                last_error = _reason(exc)

        return ConnectResult(ok=False, error=last_error)


_MIN_ATTEMPT_SECONDS = 0.05


def _attempt_budget(remaining: float, endpoints_left: int) -> float:
    """Share the remaining deadline between the endpoints still to be tried.

    Handing the whole remaining budget to one attempt lets a single blackholed
    address (a dropped SYN, or a host that resets silently) consume the deadline,
    so later endpoints are never contacted. Each attempt instead gets its fair
    share, with a small floor so a long endpoint list cannot shrink every attempt
    to nothing.
    """
    if endpoints_left <= 1:
        return remaining
    share = remaining / endpoints_left
    return max(share, min(remaining, _MIN_ATTEMPT_SECONDS))


def _reason(exc: OSError) -> str:
    if isinstance(exc, ConnectionRefusedError):
        return "connection refused"
    if isinstance(exc, TimeoutError):
        return "timed out"
    return exc.strerror or str(exc)
