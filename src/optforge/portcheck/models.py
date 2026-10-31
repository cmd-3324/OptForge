"""Value objects returned by the port inspection service."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PortState(str, Enum):
    """The two states a waiter can wait for."""

    free = "free"
    used = "used"


class SortKey(str, Enum):
    """Columns accepted by ``portcheck list --sort``."""

    port = "port"
    pid = "pid"
    process = "process"
    address = "address"


def scope_for(address: str) -> str:
    """Classify a bind address by how far it is reachable."""
    if address in ("", "0.0.0.0", "::", "*"):
        return "all interfaces"
    if address == "::1" or address.startswith("127."):
        return "local only"
    if address.startswith("169.254.") or address.lower().startswith("fe80"):
        return "link local"
    return "specific"


@dataclass(frozen=True, slots=True)
class Listener:
    """One listening TCP socket and, when the OS allows it, its owner."""

    port: int
    address: str
    family: str
    pid: int | None
    process: str

    @property
    def scope(self) -> str:
        return scope_for(self.address)

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "address": self.address,
            "family": self.family,
            "scope": self.scope,
            "pid": self.pid,
            "process": self.process,
        }


@dataclass(frozen=True, slots=True)
class ConnectResult:
    """Outcome of a single TCP connection attempt."""

    ok: bool
    seconds: float | None = None
    error: str | None = None
    endpoint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "seconds": self.seconds,
            "error": self.error,
            "endpoint": self.endpoint,
        }


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Answer to "is this port free?"."""

    port: int
    host: str
    in_use: bool
    bindable: bool
    owners: list[Listener] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "host": self.host,
            "in_use": self.in_use,
            "bindable": self.bindable,
            "owners": [owner.to_dict() for owner in self.owners],
        }


@dataclass(frozen=True, slots=True)
class WaitResult:
    """Outcome of polling until a port reaches the requested state."""

    port: int
    until: str
    reached: bool
    elapsed: float
    checks: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "until": self.until,
            "reached": self.reached,
            "elapsed": self.elapsed,
            "checks": self.checks,
        }
