from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from optforge.portcheck.models import Listener, PortState, SortKey, scope_for
from optforge.portcheck.service import PortService
from optforge.portcheck.waiter import PortWaiter


class FakeScanner:
    def __init__(self, rows: Iterable[Listener]) -> None:
        self._rows = list(rows)

    def scan(self) -> list[Listener]:
        return list(self._rows)


def listener(port: int, process: str, address: str = "0.0.0.0", pid: int | None = 1) -> Listener:
    return Listener(port=port, address=address, family="ipv4", pid=pid, process=process)


def test_scope_classification() -> None:
    assert scope_for("0.0.0.0") == "all interfaces"
    assert scope_for("::") == "all interfaces"
    assert scope_for("127.0.0.1") == "local only"
    assert scope_for("::1") == "local only"
    assert scope_for("169.254.1.1") == "link local"
    assert scope_for("10.0.0.5") == "specific"


def test_query_filters_sorts_and_limits() -> None:
    rows = [
        listener(9000, "beta", pid=2),
        listener(8000, "alpha", pid=None),
        listener(7000, "alpha", address="127.0.0.1"),
    ]
    service = PortService(scanner=FakeScanner(rows))

    assert [row.port for row in service.query(sort=SortKey.port)] == [7000, 8000, 9000]
    assert [row.port for row in service.query(sort=SortKey.pid)] == [7000, 9000, 8000]
    assert [row.port for row in service.query(process="ALPHA")] == [7000, 8000]
    assert [row.port for row in service.query(exposed=True)] == [8000, 9000]
    assert [row.port for row in service.query(limit=1)] == [7000]


def test_find_returns_every_owner() -> None:
    rows = [listener(8000, "a"), listener(8000, "b", address="127.0.0.1"), listener(9000, "c")]
    service = PortService(scanner=FakeScanner(rows))
    assert [row.process for row in service.find(8000)] == ["a", "b"]


def test_waiter_returns_when_probe_succeeds() -> None:
    ticks = iter([0.0, 0.1, 0.2, 0.3])
    probes = iter([False, False, True])
    waiter = PortWaiter(8000, "used", lambda: next(probes), clock=lambda: next(ticks), sleep=lambda _s: None)
    result = waiter.wait(timeout=10.0, interval=0.1)
    assert result.reached is True
    assert result.checks == 3
    assert result.elapsed == 0.3


def test_waiter_times_out() -> None:
    ticks = iter([0.0, 0.1, 0.2])
    waiter = PortWaiter(8000, "free", lambda: False, clock=lambda: next(ticks), sleep=lambda _s: None)
    result = waiter.wait(timeout=0.2, interval=0.1)
    assert result.reached is False
    assert result.checks == 2


def test_models_serialize() -> None:
    row = listener(8000, "alpha")
    payload: dict[str, Any] = row.to_dict()
    assert payload["scope"] == "all interfaces"
    assert payload["pid"] == 1
    assert PortState.used.value == "used"
