from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from optforge.killNotif import core


def test_clear_notifications_returns_last_line(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="warning\n3\n", stderr="")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    assert core.clear_notifications("app") == 3
    assert "-Aumid" in captured["cmd"]
    assert captured["kwargs"]["timeout"] == core.POWERSHELL_TIMEOUT_SECONDS


def test_clear_notifications_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="boom"):
        core.clear_notifications()


def test_clear_notifications_raises_on_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(cmd="powershell", timeout=1)

    monkeypatch.setattr(core.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="timed out"):
        core.clear_notifications()


def test_missing_helper_script_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
    monkeypatch.setattr(core, "JOB", core.Path(tmp_path) / "job.ps1")
    with pytest.raises(FileNotFoundError):
        core.clear_notifications()
