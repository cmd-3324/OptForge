"""High-level port operations composed from the focused components."""

from __future__ import annotations

from optforge.portcheck.binder import PortBinder
from optforge.portcheck.connector import Connector
from optforge.portcheck.models import (
    CheckResult,
    ConnectResult,
    Listener,
    PortState,
    SortKey,
    WaitResult,
)
from optforge.portcheck.scanner import ListenerScanner
from optforge.portcheck.waiter import PortWaiter

DEFAULT_HOST = "127.0.0.1"


class PortService:
    """Facade used by the CLI and by library consumers."""

    def __init__(
        self,
        scanner: ListenerScanner | None = None,
        binder: PortBinder | None = None,
        connector: Connector | None = None,
    ) -> None:
        self._scanner = scanner or ListenerScanner()
        self._binder = binder or PortBinder()
        self._connector = connector or Connector()

    def listeners(self) -> list[Listener]:
        """Every listening TCP socket on the machine."""
        return self._scanner.scan()

    def query(
        self,
        *,
        sort: SortKey = SortKey.port,
        limit: int | None = None,
        process: str | None = None,
        exposed: bool = False,
    ) -> list[Listener]:
        """Return listeners filtered and ordered for display."""
        rows = self._scanner.scan()
        if process:
            needle = process.lower()
            rows = [row for row in rows if needle in row.process.lower()]
        if exposed:
            rows = [row for row in rows if row.scope == "all interfaces"]
        rows.sort(key=_sort_key(sort))
        if limit is not None:
            rows = rows[:limit]
        return rows

    def find(self, port: int) -> list[Listener]:
        """Every listener bound to ``port``."""
        return [row for row in self._scanner.scan() if row.port == port]

    def check(self, port: int, host: str = DEFAULT_HOST) -> CheckResult:
        """Answer whether ``port`` is free, using owners plus a bind probe."""
        owners = self.find(port)
        bindable = self._binder.is_free(port, host)
        return CheckResult(
            port=port,
            host=host,
            in_use=bool(owners) or not bindable,
            bindable=bindable,
            owners=owners,
        )

    def connect(self, host: str, port: int, timeout: float) -> ConnectResult:
        """Attempt a TCP connection with a real deadline."""
        return self._connector.connect(host, port, timeout)

    def wait(
        self,
        port: int,
        until: PortState,
        *,
        timeout: float,
        interval: float,
        host: str = DEFAULT_HOST,
    ) -> WaitResult:
        """Poll until the port is ``used`` or ``free``.

        The probes are deliberately cheap: a TCP connect for ``used`` and a
        pair of wildcard bind probes for ``free``. Neither walks the socket
        table, so a long wait stays cheap.
        """
        state = PortState(until)
        if state is PortState.used:
            probe_timeout = min(max(interval * 2.0, 0.2), 1.0)
            probe = lambda: self._connector.connect(host, port, probe_timeout).ok  # noqa: E731
        else:
            probe = lambda: self._binder.is_free_on_all_interfaces(port)  # noqa: E731
        return PortWaiter(port, state.value, probe).wait(timeout, interval)


def _sort_key(sort: SortKey) -> object:
    keys = {
        SortKey.port: lambda row: (row.port, row.address),
        SortKey.pid: lambda row: (row.pid is None, row.pid or 0, row.port),
        SortKey.process: lambda row: (row.process.lower(), row.port),
        SortKey.address: lambda row: (row.address, row.port),
    }
    return keys[sort]
