"""Value objects for environment inspection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class OutputFormat(str, Enum):
    """Supported ``envcheck`` output formats."""

    table = "table"
    json = "json"
    dotenv = "dotenv"


@dataclass(frozen=True, slots=True)
class EnvEntry:
    """One environment variable, optionally redacted."""

    key: str
    value: str
    sensitive: bool = False
    redacted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "sensitive": self.sensitive,
            "redacted": self.redacted,
        }
