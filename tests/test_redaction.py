from __future__ import annotations

import pytest

from optforge.core.redaction import DEFAULT_MASK, SecretRedactor


@pytest.mark.parametrize(
    "key",
    ["API_KEY", "auth_token", "DB_PASSWORD", "PRIVATE_VALUE", "SESSION_ID", "CONNECTION_STRING"],
)
def test_sensitive_names_are_detected(key: str) -> None:
    assert SecretRedactor().is_sensitive(key)


@pytest.mark.parametrize("key", ["PATH", "HOME", "USERNAME", "PYTHONPATH"])
def test_regular_names_are_not_sensitive(key: str) -> None:
    assert not SecretRedactor().is_sensitive(key)


def test_redact_masks_only_sensitive_values() -> None:
    redactor = SecretRedactor()
    assert redactor.redact("API_KEY", "secret") == (DEFAULT_MASK, True)
    assert redactor.redact("HOME", "/home/dev") == ("/home/dev", False)


def test_custom_mask() -> None:
    redactor = SecretRedactor(mask="***")
    assert redactor.redact("TOKEN", "value") == ("***", True)
