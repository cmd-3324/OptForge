"""Disk usage collection for a path or every mounted volume."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Iterable
from typing import Any

import psutil

from optforge.core.errors import OperationFailed, OptForgeError
from optforge.diskcheck.models import DiskInfo

UsageReader = Callable[[str], tuple[int, int, int]]
PartitionReader = Callable[..., Iterable[Any]]


class DiskService:
    """Read usage without crashing on one unreadable mount."""

    def __init__(
        self,
        usage: UsageReader = shutil.disk_usage,
        partitions: PartitionReader = psutil.disk_partitions,
    ) -> None:
        self._usage = usage
        self._partitions = partitions

    def usage(self, path: str = ".") -> DiskInfo:
        """Return usage for ``path``."""
        try:
            total, used, free = self._usage(path)
        except OSError as exc:
            raise OperationFailed(f"Could not read disk usage for {path!r}: {exc}") from exc
        percent_used = (used / total * 100.0) if total else 0.0
        return DiskInfo(
            path=os.path.abspath(path),
            total=int(total),
            used=int(used),
            free=int(free),
            percent_used=float(percent_used),
        )

    def volumes(self) -> list[DiskInfo]:
        """Return usage for every mounted partition that can be read."""
        results: list[DiskInfo] = []
        for partition in self._partitions(all=True):
            mountpoint = getattr(partition, "mountpoint", None)
            if not mountpoint:
                continue
            try:
                results.append(self.usage(mountpoint))
            except OptForgeError:
                continue
        return results
