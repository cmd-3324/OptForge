from __future__ import annotations

import psutil
import pytest

from optforge.core.processes import ProcessNameResolver


class FakeProcess:
    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name


def test_an_unknown_pid_is_reported_as_dash() -> None:
    resolver = ProcessNameResolver(factory=lambda _pid: FakeProcess("python"))
    assert resolver.name(None) == "-"


def test_each_pid_is_resolved_only_once() -> None:
    calls: list[int] = []

    def factory(pid: int) -> FakeProcess:
        calls.append(pid)
        return FakeProcess("python")

    resolver = ProcessNameResolver(factory=factory)
    assert resolver.name(1234) == "python"
    assert resolver.name(1234) == "python"
    assert calls == [1234]


def test_clear_drops_the_cache() -> None:
    calls: list[int] = []

    def factory(pid: int) -> FakeProcess:
        calls.append(pid)
        return FakeProcess("python")

    resolver = ProcessNameResolver(factory=factory)
    resolver.name(7)
    resolver.clear()
    resolver.name(7)
    assert calls == [7, 7]


@pytest.mark.parametrize(
    "error",
    [psutil.NoSuchProcess(pid=1), psutil.AccessDenied(pid=1), psutil.ZombieProcess(pid=1)],
)
def test_unreadable_processes_are_reported_as_dash(error: Exception) -> None:
    def factory(_pid: int) -> FakeProcess:
        raise error

    assert ProcessNameResolver(factory=factory).name(42) == "-"
