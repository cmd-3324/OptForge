"""Environment inspection utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EnvEntry:
    key: str
    value: str


def get_environment(prefix: str | None = None, include_hidden: bool = True) -> list[EnvEntry]:
    """Return a sorted list of environment variables."""
    entries: list[EnvEntry] = []
    for key, value in sorted(os.environ.items()):
        if prefix is not None and not key.lower().startswith(prefix.lower()):
            continue
        if not include_hidden and key.startswith("_"):
            continue
        entries.append(EnvEntry(key=key, value=value))
    return entries
