from __future__ import annotations

import pytest
from typer.testing import CliRunner

from optforge.core.errors import InvalidInput
from optforge.volume import cli as volume_cli
from optforge.volume.cli import app
from optforge.volume.core import MAX_VOLUME, MIN_VOLUME, VolumeController


class FakeBackend:
    name = "fake"

    def __init__(self, volume: int = 36, muted: bool = False) -> None:
        self.volume = volume
        self.muted = muted

    def get(self) -> int:
        return self.volume

    def set(self, percent: int) -> None:
        self.volume = percent

    def get_mute(self) -> bool:
        return self.muted

    def set_mute(self, muted: bool) -> None:
        self.muted = muted


@pytest.fixture()
def backend(monkeypatch: pytest.MonkeyPatch) -> FakeBackend:
    fake = FakeBackend()
    controller = VolumeController(fake)
    monkeypatch.setattr(volume_cli, "_controller", lambda: controller)
    return fake


runner = CliRunner()


def test_get_reports_volume_and_mute(backend: FakeBackend) -> None:
    result = runner.invoke(app, ["get"])
    assert result.exit_code == 0
    assert "36%" in result.stdout
    assert "muted" not in result.stdout

    backend.muted = True
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    assert '"volume": 36' in result.stdout
    assert '"muted": true' in result.stdout


def test_on_full_none(backend: FakeBackend) -> None:
    assert runner.invoke(app, ["on", "50"]).exit_code == 0
    assert backend.volume == 50

    assert runner.invoke(app, ["full"]).exit_code == 0
    assert backend.volume == MAX_VOLUME

    assert runner.invoke(app, ["none"]).exit_code == 0
    assert backend.volume == MIN_VOLUME


def test_up_down_and_clamping(backend: FakeBackend) -> None:
    backend.volume = 96
    assert runner.invoke(app, ["up"]).exit_code == 0
    assert backend.volume == MAX_VOLUME

    assert runner.invoke(app, ["up", "10"]).exit_code == 0
    assert backend.volume == MAX_VOLUME

    backend.volume = 4
    assert runner.invoke(app, ["down", "10"]).exit_code == 0
    assert backend.volume == MIN_VOLUME


def test_mute_commands(backend: FakeBackend) -> None:
    assert runner.invoke(app, ["mute"]).exit_code == 0
    assert backend.muted is True

    assert runner.invoke(app, ["unmute", "--json"]).exit_code == 0
    assert backend.muted is False

    assert runner.invoke(app, ["toggle"]).exit_code == 0
    assert backend.muted is True

    assert runner.invoke(app, ["toggle", "--json"]).exit_code == 0
    assert backend.muted is False


def test_setting_volume_unmutes(backend: FakeBackend) -> None:
    backend.muted = True
    assert runner.invoke(app, ["on", "25"]).exit_code == 0
    assert backend.muted is False


def test_invalid_values(backend: FakeBackend) -> None:
    assert runner.invoke(app, ["on", "101"]).exit_code == 2
    assert runner.invoke(app, ["up", "0"]).exit_code == 2

    with pytest.raises(InvalidInput):
        VolumeController(backend).set(101)

    with pytest.raises(InvalidInput):
        VolumeController(backend).up(0)
