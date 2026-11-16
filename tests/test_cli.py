from __future__ import annotations

import json
import socket
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from optforge.cli import app as dispatcher
from optforge.core.version import get_version
from optforge.diskcheck.cli import app as diskcheck_app
from optforge.envcheck.cli import app as envcheck_app
from optforge.killNotif import cli as killnotif_cli
from optforge.portcheck.cli import app as portcheck_app
from optforge.pycacheclean.cli import app as pycache_app

runner = CliRunner()


def test_dispatcher_version() -> None:
    result = runner.invoke(dispatcher, ["--version"])
    assert result.exit_code == 0
    assert get_version() in result.stdout


def test_dispatcher_exposes_killnotif() -> None:
    result = runner.invoke(dispatcher, ["killNotif", "--help"])
    assert result.exit_code == 0
    assert "notifications" in result.stdout.lower()


def test_pycache_options_after_positional(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    result = runner.invoke(pycache_app, [str(tmp_path), "--dry-run", "--json"])
    assert result.exit_code == 0
    assert (tmp_path / "__pycache__").exists()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_portcheck_help() -> None:
    result = runner.invoke(portcheck_app, ["--help"])
    assert result.exit_code == 0
    assert "portcheck" in result.output.lower()


def test_portcheck_version() -> None:
    result = runner.invoke(portcheck_app, ["--version"])
    assert result.exit_code == 0
    assert get_version() in result.output


def test_portcheck_check_answers_yes_for_a_free_port() -> None:
    result = runner.invoke(portcheck_app, ["check", str(_free_port()), "-H", "127.0.0.1"])
    assert result.exit_code == 0


def test_portcheck_check_answers_no_for_a_busy_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = str(server.getsockname()[1])
        assert runner.invoke(portcheck_app, ["check", port, "--expect", "used", "-H", "127.0.0.1"]).exit_code == 0
        assert runner.invoke(portcheck_app, ["check", port, "--expect", "free", "-H", "127.0.0.1"]).exit_code == 1


def test_portcheck_find_answers_no_for_a_free_port() -> None:
    assert runner.invoke(portcheck_app, ["find", str(_free_port())]).exit_code == 1


def test_portcheck_rejects_an_out_of_range_port() -> None:
    assert runner.invoke(portcheck_app, ["check", "70000"]).exit_code == 2


def test_portcheck_requires_a_port() -> None:
    assert runner.invoke(portcheck_app, ["check"]).exit_code == 2


def test_killnotif_help() -> None:
    result = runner.invoke(killnotif_cli.app, ["--help"])
    assert result.exit_code == 0
    assert "notifications" in result.output.lower()


def test_killnotif_clears_and_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(killnotif_cli, "_clear", lambda _aumid: 2)

    result = runner.invoke(killnotif_cli.app, [])
    assert result.exit_code == 0
    assert "Cleared 2 sender(s)" in result.output


def test_killnotif_reports_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(killnotif_cli, "_clear", lambda _aumid: 2)

    result = runner.invoke(killnotif_cli.app, ["--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["cleared"] == 2


def test_killnotif_is_quiet_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(killnotif_cli, "_clear", lambda _aumid: 0)

    result = runner.invoke(killnotif_cli.app, ["--quiet"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_killnotif_refuses_on_other_platforms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert runner.invoke(killnotif_cli.app, []).exit_code == 3


def test_killnotif_rejects_unknown_options() -> None:
    assert runner.invoke(killnotif_cli.app, ["--nope"]).exit_code == 2


def test_envcheck_help() -> None:
    result = runner.invoke(envcheck_app, ["--help"])
    assert result.exit_code == 0
    assert "environment" in result.output.lower()


def test_envcheck_redacts_secrets_in_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTFORGE_SMOKE_VISIBLE", "hello")
    monkeypatch.setenv("OPTFORGE_SMOKE_TOKEN", "s3cret")

    result = runner.invoke(envcheck_app, ["--prefix", "OPTFORGE_SMOKE", "--json"])
    assert result.exit_code == 0
    entries = {entry["key"]: entry for entry in json.loads(result.output)}
    assert entries["OPTFORGE_SMOKE_VISIBLE"]["value"] == "hello"
    assert entries["OPTFORGE_SMOKE_TOKEN"]["value"] == "<redacted>"
    assert entries["OPTFORGE_SMOKE_TOKEN"]["redacted"] is True


def test_envcheck_dotenv_format(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPTFORGE_SMOKE_VISIBLE", "hello")

    result = runner.invoke(envcheck_app, ["--prefix", "OPTFORGE_SMOKE_VISIBLE", "--format", "dotenv"])
    assert result.exit_code == 0
    assert "OPTFORGE_SMOKE_VISIBLE=hello" in result.output


def test_envcheck_rejects_an_unknown_format() -> None:
    assert runner.invoke(envcheck_app, ["--format", "yaml"]).exit_code == 2


def test_pycache_help() -> None:
    assert runner.invoke(pycache_app, ["--help"]).exit_code == 0


def test_pycache_deletes_with_yes(tmp_path: Path) -> None:
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)

    result = runner.invoke(pycache_app, [str(tmp_path), "--yes", "--json"])
    assert result.exit_code == 0
    assert len(json.loads(result.output)["removed"]) == 1
    assert not (tmp_path / "pkg" / "__pycache__").exists()


def test_pycache_refuses_to_delete_without_a_terminal(tmp_path: Path) -> None:
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)

    result = runner.invoke(pycache_app, [str(tmp_path)])
    assert result.exit_code == 2
    assert (tmp_path / "pkg" / "__pycache__").exists()


def test_pycache_reports_nothing_found_as_json(tmp_path: Path) -> None:
    result = runner.invoke(pycache_app, [str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["removed"] == []


def test_pycache_rejects_a_bad_depth(tmp_path: Path) -> None:
    assert runner.invoke(pycache_app, [str(tmp_path), "--max-depth", "0"]).exit_code == 2


def test_diskcheck_options_after_positional(tmp_path: Path) -> None:
    result = runner.invoke(diskcheck_app, [str(tmp_path), "--json"])
    assert result.exit_code == 0
