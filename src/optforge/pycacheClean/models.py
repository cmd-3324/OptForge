"""Value objects for Python cache cleanup."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CacheTarget:
    """A ``__pycache__`` directory discovered by the scanner."""

    path: Path
    files: int = 0
    bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "files": self.files, "bytes": self.bytes}


@dataclass(frozen=True, slots=True)
class CleanFailure:
    """A target that could not be removed."""

    path: Path
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": str(self.path), "error": self.error}


@dataclass(frozen=True, slots=True)
class CleanReport:
    """What a cleanup run did (or would do)."""

    dry_run: bool
    removed: list[CacheTarget] = field(default_factory=list)
    failed: list[CleanFailure] = field(default_factory=list)

    @property
    def freed_bytes(self) -> int:
        return sum(target.bytes for target in self.removed)

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "removed": [target.to_dict() for target in self.removed],
            "failed": [failure.to_dict() for failure in self.failed],
            "freed_bytes": self.freed_bytes,
        }
