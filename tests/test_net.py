from __future__ import annotations

import socket

import pytest

from optforge.core import net
from optforge.core.errors import OperationFailed
from optforge.core.net import Endpoint


def test_endpoint_labels() -> None:
    assert Endpoint(socket.AF_INET, ("127.0.0.1", 80)).label() == "127.0.0.1:80"
    assert Endpoint(socket.AF_INET6, ("::1", 80, 0, 0)).label() == "[::1]:80"
    assert Endpoint(socket.AF_INET, ("127.0.0.1", 80)).family_name == "ipv4"
    assert Endpoint(socket.AF_INET6, ("::1", 80, 0, 0)).family_name == "ipv6"


def test_resolve_endpoints_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    infos = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80)),
    ]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: infos)
    endpoints = net.resolve_endpoints("localhost", 80)
    assert len(endpoints) == 1
    assert endpoints[0].address == "127.0.0.1"


def test_resolve_endpoints_reports_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: object, **_kwargs: object) -> list[object]:
        raise socket.gaierror(-2, "bad name")

    monkeypatch.setattr(socket, "getaddrinfo", broken)
    with pytest.raises(OperationFailed, match="Could not resolve"):
        net.resolve_endpoints("nope.invalid", 80)


def test_resolve_with_timeout_propagates_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    endpoint = Endpoint(socket.AF_INET, ("127.0.0.1", 80))
    monkeypatch.setattr(net, "resolve_endpoints", lambda _host, _port: [endpoint])
    assert net.resolve_endpoints_with_timeout("localhost", 80, 1.0) == [endpoint]


def test_resolve_with_timeout_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_host: str, _port: int) -> list[Endpoint]:
        raise OperationFailed("bad")

    monkeypatch.setattr(net, "resolve_endpoints", broken)
    with pytest.raises(OperationFailed, match="bad"):
        net.resolve_endpoints_with_timeout("localhost", 80, 1.0)
