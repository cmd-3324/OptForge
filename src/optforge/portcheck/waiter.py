"""Deadline-driven polling for port state changes."""

from __future__ import annotations

import time
from collections.abc import Callable

from optforge.portcheck.models import WaitResult

Probe = Callable[[], bool]


class PortWaiter:
    """Poll a probe until it returns ``True`` or the deadline expires."""

    def __init__(
        self,
        port: int,
        until: str,
        probe: Probe,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._port = port
        self._until = until
        self._probe = probe
        self._clock = clock
        self._sleep = sleep

    def wait(self, timeout: float, interval: float) -> WaitResult:
        start = self._clock()
        deadline = start + timeout
        checks = 0
        while True:
            checks += 1
            if self._probe():
                return WaitResult(
                    port=self._port,
                    until=self._until,
                    reached=True,
                    elapsed=self._clock() - start,
                    checks=checks,
                )
            now = self._clock()
            if now >= deadline:
                return WaitResult(
                    port=self._port,
                    until=self._until,
                    reached=False,
                    elapsed=now - start,
                    checks=checks,
                )
            self._sleep(min(interval, max(0.0, deadline - now)))
