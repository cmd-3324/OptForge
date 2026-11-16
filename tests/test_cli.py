from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from optforge.cli import app as dispatcher
from optforge.core.version import get_version
from optforge.diskcheck.cli import app as diskcheck_app
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


def test_diskcheck_options_after_positional(tmp_path: Path) -> None:
    result = runner.invoke(diskcheck_app, [str(tmp_path), "--json"])
    assert result.exit_code == 0
