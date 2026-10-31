"""Environment variable collection and redaction."""

from __future__ import annotations

import os
from collections.abc import Mapping

from optforge.core.redaction import SecretRedactor
from optforge.envcheck.models import EnvEntry

_QUOTE_TRIGGERS = frozenset(' \t\n#"\'')


class EnvironmentService:
    """Read ``os.environ`` and decide what is safe to display."""

    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        redactor: SecretRedactor | None = None,
    ) -> None:
        self._environ = environ if environ is not None else os.environ
        self._redactor = redactor or SecretRedactor()

    def entries(
        self,
        *,
        prefix: str | None = None,
        include_hidden: bool = True,
        redact: bool = True,
    ) -> list[EnvEntry]:
        """Return sorted entries, masking sensitive values by default."""
        needle = prefix.lower() if prefix else None
        entries: list[EnvEntry] = []
        for key in sorted(self._environ):
            if needle is not None and not key.lower().startswith(needle):
                continue
            if not include_hidden and key.startswith("_"):
                continue
            raw = self._environ[key]
            sensitive = self._redactor.is_sensitive(key)
            value = raw
            redacted = False
            if redact and sensitive:
                value, redacted = self._redactor.redact(key, raw)
            entries.append(
                EnvEntry(key=key, value=value, sensitive=sensitive, redacted=redacted)
            )
        return entries

    @staticmethod
    def to_dotenv(entries: list[EnvEntry]) -> str:
        """Render entries as a ``.env`` fragment."""
        return "\n".join(_dotenv_line(entry) for entry in entries)


def _dotenv_line(entry: EnvEntry) -> str:
    if not entry.value or not (set(entry.value) & _QUOTE_TRIGGERS):
        return f"{entry.key}={entry.value}"
    escaped = (
        entry.value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return f'{entry.key}="{escaped}"'
