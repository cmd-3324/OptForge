"""Cached process-name lookups for socket owners."""

from __future__ import annotations

from collections.abc import Callable

import psutil

_UNKNOWN = "-"


class ProcessNameResolver:
    """Resolve PIDs to names once, then serve from memory.

    A busy machine can have hundreds of listening sockets owned by a handful of
    processes. Looking each PID up on every scan is the difference between one
    system call and hundreds.
    """

    def __init__(self, factory: Callable[[int], psutil.Process] = psutil.Process) -> None:
        self._factory = factory
        self._cache: dict[int, str] = {}

    def name(self, pid: int | None) -> str:
        if pid is None:
            return _UNKNOWN
        cached = self._cache.get(pid)
        if cached is not None:
            return cached
        try:
            resolved = self._factory(pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            resolved = _UNKNOWN
        self._cache[pid] = resolved
        return resolved

    def clear(self) -> None:
        self._cache.clear()
