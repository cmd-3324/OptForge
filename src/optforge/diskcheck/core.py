"""Disk space inspection utilities."""

from __future__ import annotations

from dataclasses import dataclass
import os
import shutil


@dataclass(frozen=True, slots=True)
class DiskInfo:
    path: str
    total: int
    used: int
    free: int
    percent_used: float


def get_disk_usage(path: str = ".") -> DiskInfo:
    """Return disk usage statistics for the provided path."""
    total, used, free = shutil.disk_usage(path)
    percent_used = (used / total * 100.0) if total else 0.0
    return DiskInfo(
        path=os.path.abspath(path),
        total=int(total),
        used=int(used),
        free=int(free),
        percent_used=float(percent_used),
    )
