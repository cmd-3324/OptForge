"""Cross-platform socket address resolution.

The standard library's ``socket.create_connection`` resolves names with an
unbounded DNS call, which silently ignores a caller-supplied timeout. OptForge
resolves addresses in a worker thread so the deadline is real, then connects to
each returned endpoint with the remaining time.
"""

from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from typing import Any

from optforge.core.errors import OperationFailed


@dataclass(frozen=True, slots=True)
class Endpoint:
    """One resolved socket address."""

    family: int
    sockaddr: tuple[Any, ...]

    @property
    def address(self) -> str:
        return str(self.sockaddr[0])

    @property
    def port(self) -> int:
        return int(self.sockaddr[1])

    @property
    def family_name(self) -> str:
        return "ipv6" if self.family == socket.AF_INET6 else "ipv4"

    def label(self) -> str:
        if self.family == socket.AF_INET6:
            return f"[{self.address}]:{self.port}"
        return f"{self.address}:{self.port}"


def resolve_endpoints(host: str, port: int, *, passive: bool = False) -> list[Endpoint]:
    """Resolve ``host``/``port`` to every usable TCP endpoint.

    Raises:
        OperationFailed: if the name cannot be resolved.
    """
    flags = socket.AI_PASSIVE if passive else 0
    try:
        infos = socket.getaddrinfo(
            host or None,
            port,
            type=socket.SOCK_STREAM,
            flags=flags,
        )
    except socket.gaierror as exc:
        reason = exc.strerror or str(exc)
        raise OperationFailed(f"Could not resolve {host!r}: {reason}") from exc

    endpoints: list[Endpoint] = []
    seen: set[tuple[int, tuple[Any, ...]]] = set()
    for family, _type, _proto, _canonname, sockaddr in infos:
        key = (family, sockaddr)
        if key in seen:
            continue
        seen.add(key)
        endpoints.append(Endpoint(family=family, sockaddr=sockaddr))
    if not endpoints:
        raise OperationFailed(f"Could not resolve {host!r} to any TCP address.")
    return endpoints


def resolve_endpoints_with_timeout(host: str, port: int, timeout: float) -> list[Endpoint]:
    """Resolve ``host`` while enforcing ``timeout`` on the DNS lookup."""
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="optforge-dns")
    future = executor.submit(resolve_endpoints, host, port)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError as exc:
        raise OperationFailed(
            f"Timed out after {timeout:g}s while resolving {host!r}."
        ) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
