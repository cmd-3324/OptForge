"""Key-based secret detection and redaction for environment inspection."""

from __future__ import annotations

import re

_SECRET_KEY = re.compile(
    r"(?:"
    r"KEY|TOKEN|SECRET|PASSWORD|PASSWD|PASSPHRASE|CREDENTIAL|PRIVATE|"
    r"AUTH|COOKIE|SESSION|SIGNATURE|CERT|DSN|DATABASE_URL|CONNECTION_STRING"
    r")",
    re.IGNORECASE,
)

DEFAULT_MASK = "<redacted>"


class SecretRedactor:
    """Decide whether an environment variable name is sensitive.

    Detection is deliberately name-based and conservative: it errs toward
    masking values that merely *look* like secrets, because a false positive is
    cheap and a leaked token is not.
    """

    def __init__(self, mask: str = DEFAULT_MASK, pattern: re.Pattern[str] = _SECRET_KEY) -> None:
        self._mask = mask
        self._pattern = pattern

    @property
    def mask(self) -> str:
        return self._mask

    def is_sensitive(self, key: str) -> bool:
        return bool(self._pattern.search(key))

    def redact(self, key: str, value: str) -> tuple[str, bool]:
        """Return ``(display_value, was_redacted)`` for ``key``/``value``."""
        if self.is_sensitive(key):
            return self._mask, True
        return value, False
