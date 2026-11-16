from __future__ import annotations

import socket
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

import psutil
import pytest

from optforge.core.errors import OperationFailed, PermissionDenied
from optforge.core.net import Endpoint
from optforge.portcheck import binder as binder_module
from optforge.portcheck.binder import PortBinder
from optforge.portcheck.connector import Connector, _attempt_budget, _reason
from optforge.portcheck.models import Listener, PortState, SortKey, scope_for
from optforge.portcheck.scanner import ListenerScanner
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


@pytest.fixture()
def unresolvable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every address resolution fail."""

    def fail(*_args: object, **_kwargs: object) -> list[object]:
        raise OperationFailed("no address of this family")

    monkeypatch.setattr(binder_module, "resolve_endpoints", fail)


def test_binder_rejects_unresolvable_explicit_host(unresolvable: None) -> None:
    with pytest.raises(OperationFailed):
        PortBinder().is_free(8000, "nope.invalid")


def test_binder_treats_missing_address_family_as_free(unresolvable: None) -> None:
    assert PortBinder().is_free(8000, "::") is True
    assert PortBinder().is_free_on_all_interfaces(8000) is True


def listening_socket() -> socket.socket:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    return server


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_connector_connects_to_a_real_listener() -> None:
    server = listening_socket()
    port = server.getsockname()[1]
    try:
        result = Connector().connect("127.0.0.1", port, 2.0)
    finally:
        server.close()

    assert result.ok is True
    assert result.endpoint == f"127.0.0.1:{port}"
    assert result.seconds is not None
    assert result.seconds >= 0.0


def test_connector_reports_a_closed_port_as_refused() -> None:
    server = listening_socket()
    port = server.getsockname()[1]
    server.close()

    result = Connector().connect("127.0.0.1", port, 0.5)
    assert result.ok is False
    # Windows can drop the loopback reset and report a timeout instead of a refusal.
    assert result.error in {"connection refused", "timed out"}


def test_connector_does_not_let_a_slow_endpoint_starve_the_next() -> None:
    server = listening_socket()
    good_port = server.getsockname()[1]
    # A closed loopback port blackholes the SYN on Windows, so this first
    # endpoint used to consume the whole budget and the second was never tried.
    endpoints = [
        Endpoint(socket.AF_INET, ("127.0.0.1", free_port())),
        Endpoint(socket.AF_INET, ("127.0.0.1", good_port)),
    ]
    try:
        result = Connector(resolver=lambda *_args: endpoints).connect("127.0.0.1", good_port, 1.0)
    finally:
        server.close()

    assert result.ok is True
    assert result.endpoint == f"127.0.0.1:{good_port}"


def test_connector_honours_the_deadline_between_endpoints() -> None:
    endpoints = [Endpoint(socket.AF_INET, ("127.0.0.1", 1)), Endpoint(socket.AF_INET, ("127.0.0.1", 2))]
    ticks = iter([0.0, 5.0])

    result = Connector(resolver=lambda *_args: endpoints, clock=lambda: next(ticks)).connect("127.0.0.1", 1, 2.0)
    assert result.ok is False
    assert result.error == "timed out after 2s"


def test_connector_reports_a_resolution_failure() -> None:
    def broken(*_args: object, **_kwargs: object) -> list[Endpoint]:
        raise OperationFailed("Could not resolve 'nope.invalid'")

    result = Connector(resolver=broken).connect("nope.invalid", 80, 1.0)
    assert result.ok is False
    assert result.error == "Could not resolve 'nope.invalid'"


def test_connector_reports_when_there_is_no_endpoint() -> None:
    result = Connector(resolver=lambda *_args: []).connect("example.invalid", 80, 1.0)
    assert result.ok is False
    assert result.error == "no endpoint accepted the connection"


@pytest.mark.parametrize(
    ("remaining", "endpoints_left", "expected"),
    [
        (2.0, 2, 1.0),
        (2.0, 4, 0.5),
        (2.0, 1, 2.0),
        (1.0, 100, 0.05),
        (0.04, 10, 0.04),
    ],
)
def test_attempt_budget_shares_the_remaining_deadline(remaining: float, endpoints_left: int, expected: float) -> None:
    assert _attempt_budget(remaining, endpoints_left) == pytest.approx(expected)


def test_connector_survives_an_unusable_endpoint() -> None:
    endpoints = [Endpoint(999_999, ("127.0.0.1", 80))]

    result = Connector(resolver=lambda *_args: endpoints).connect("127.0.0.1", 80, 1.0)
    assert result.ok is False
    assert result.error


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ConnectionRefusedError(111, "refused"), "connection refused"),
        (TimeoutError("slow"), "timed out"),
        (OSError(101, "unreachable"), "unreachable"),
        (OSError("plain message"), "plain message"),
    ],
)
def test_reason_maps_socket_errors(exc: OSError, expected: str) -> None:
    assert _reason(exc) == expected


class UnreadableScanner:
    def scan(self) -> list[Listener]:
        raise PermissionDenied("Run as Administrator (Windows) or with sudo (Linux/macOS).")


def test_check_answers_from_the_bind_probe_without_a_socket_table() -> None:
    service = PortService(scanner=UnreadableScanner(), binder=PortBinder())

    free = service.check(free_port(), "127.0.0.1")
    assert free.owners == []
    assert free.in_use is False

    server = listening_socket()
    try:
        busy = service.check(int(server.getsockname()[1]), "127.0.0.1")
    finally:
        server.close()
    assert busy.owners == []
    assert busy.in_use is True


def test_binder_reports_a_bound_port_as_busy() -> None:
    server = listening_socket()
    port = server.getsockname()[1]
    try:
        assert PortBinder().is_free(port, "127.0.0.1") is False
    finally:
        server.close()


def test_binder_reports_a_free_port_as_free() -> None:
    assert PortBinder().is_free(free_port(), "127.0.0.1") is True


class FakeResolver:
    def name(self, pid: int | None) -> str:
        return "-" if pid is None else f"pid-{pid}"


def connection(
    port: int,
    *,
    address: str = "0.0.0.0",
    pid: int | None = 1,
    status: str = "LISTEN",
    family: int = socket.AF_INET,
) -> SimpleNamespace:
    return SimpleNamespace(
        status=status,
        laddr=SimpleNamespace(ip=address, port=port),
        pid=pid,
        family=family,
    )


def test_scanner_filters_deduplicates_and_sorts() -> None:
    rows = [
        connection(9000, pid=3),
        connection(8000, address="127.0.0.1", pid=2),
        connection(8000, address="127.0.0.1", pid=2),
        connection(7000, status="ESTABLISHED", pid=4),
    ]
    scanner = ListenerScanner(provider=lambda **_kwargs: rows, resolver=FakeResolver())

    listeners = scanner.scan()
    assert [(row.port, row.address, row.pid) for row in listeners] == [
        (8000, "127.0.0.1", 2),
        (9000, "0.0.0.0", 3),
    ]
    assert listeners[1].process == "pid-3"
    assert listeners[1].family == "ipv4"
    assert listeners[1].scope == "all interfaces"


def test_scanner_falls_back_to_wildcard_addresses() -> None:
    rows = [
        connection(8080, address="", family=socket.AF_INET6),
        connection(8081, address=""),
    ]
    scanner = ListenerScanner(provider=lambda **_kwargs: rows, resolver=FakeResolver())

    listeners = scanner.scan()
    assert [(row.port, row.address, row.family) for row in listeners] == [
        (8080, "::", "ipv6"),
        (8081, "0.0.0.0", "ipv4"),
    ]


def test_scanner_skips_sockets_without_a_local_address() -> None:
    rows = [SimpleNamespace(status="LISTEN", laddr=None, pid=1, family=socket.AF_INET)]
    scanner = ListenerScanner(provider=lambda **_kwargs: rows, resolver=FakeResolver())

    assert scanner.scan() == []


def test_scanner_reports_an_unknown_owner_as_dash() -> None:
    rows = [connection(8000, pid=None)]
    scanner = ListenerScanner(provider=lambda **_kwargs: rows, resolver=FakeResolver())

    assert scanner.scan()[0].process == "-"


def test_scanner_maps_access_denied_to_permission_denied() -> None:
    def denied(**_kwargs: object) -> list[object]:
        raise psutil.AccessDenied(pid=1)

    with pytest.raises(PermissionDenied):
        ListenerScanner(provider=denied, resolver=FakeResolver()).scan()


def test_scanner_maps_os_errors_to_permission_denied() -> None:
    def broken(**_kwargs: object) -> list[object]:
        raise OSError("socket table unavailable")

    with pytest.raises(PermissionDenied):
        ListenerScanner(provider=broken, resolver=FakeResolver()).scan()


def test_scanner_asks_for_tcp_only_and_owners_filter_by_port() -> None:
    seen: list[dict[str, object]] = []
    rows = [connection(8000), connection(9000)]

    def provider(**kwargs: object) -> list[SimpleNamespace]:
        seen.append(kwargs)
        return rows

    scanner = ListenerScanner(provider=provider, resolver=FakeResolver())
    assert [row.port for row in scanner.owners(8000)] == [8000]
    assert seen[0] == {"kind": "tcp"}
