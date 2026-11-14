from __future__ import annotations

from optforge.envcheck.service import EnvironmentService


def test_entries_are_sorted_and_filtered() -> None:
    service = EnvironmentService({"B": "2", "A": "1", "PREFIX_ONE": "x"})
    assert [entry.key for entry in service.entries()] == ["A", "B", "PREFIX_ONE"]
    assert [entry.key for entry in service.entries(prefix="prefix")] == ["PREFIX_ONE"]


def test_hidden_entries_can_be_excluded() -> None:
    service = EnvironmentService({"A": "1", "_PRIVATE": "2"})
    assert [entry.key for entry in service.entries(include_hidden=False)] == ["A"]


def test_sensitive_values_are_redacted_by_default() -> None:
    service = EnvironmentService({"API_TOKEN": "secret", "HOME": "/tmp"})
    entries = {entry.key: entry for entry in service.entries()}
    assert entries["API_TOKEN"].value == "<redacted>"
    assert entries["API_TOKEN"].redacted is True
    assert entries["HOME"].value == "/tmp"
    assert entries["HOME"].redacted is False


def test_show_secrets_path_keeps_raw_values() -> None:
    service = EnvironmentService({"API_TOKEN": "secret"})
    entries = service.entries(redact=False)
    assert entries[0].value == "secret"
    assert entries[0].redacted is False


def test_dotenv_quotes_and_escapes_values() -> None:
    service = EnvironmentService({})
    entries = service.entries()
    assert entries == []

    from optforge.envcheck.models import EnvEntry

    rendered = service.to_dotenv(
        [
            EnvEntry(key="PLAIN", value="abc"),
            EnvEntry(key="SPACED", value="a b"),
            EnvEntry(key="QUOTED", value='a"b'),
        ]
    )
    assert "PLAIN=abc" in rendered
    assert 'SPACED="a b"' in rendered
    assert 'QUOTED="a\\"b"' in rendered
