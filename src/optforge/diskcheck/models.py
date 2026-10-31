"""Value objects for disk inspection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DiskInfo:
    """Usage for one path or mounted volume."""

    path: str
    total: int
    used: int
    free: int
    percent_used: float

    @property
    def percent_free(self) -> float:
        return 100.0 - self.percent_used

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "total": self.total,
            "used": self.used,
            "free": self.free,
            "percent_used": round(self.percent_used, 2),
            "percent_free": round(self.percent_free, 2),
        }
