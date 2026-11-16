from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from optforge.core.errors import InvalidInput, OperationFailed
from optforge.volume import cli as volume_cli
from optforge.volume import core as volume_core
from optforge.volume.cli import app
from optforge.volume.core import (
    MAX_VOLUME,
    MIN_VOLUME,
    LinuxVolumeBackend,
    MacOSVolumeBackend,
    VolumeController,
    WindowsVolumeBackend,
    _clamp,
    _detect_linux_tool,
    _parse_percent,
    _validate,
    _validate_step,
)


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


def _stub_command(
    monkeypatch: pytest.MonkeyPatch, *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> list[list[str]]:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(volume_core.subprocess, "run", fake_run)
    return calls


def _linux(tool: str) -> LinuxVolumeBackend:
    backend = LinuxVolumeBackend.__new__(LinuxVolumeBackend)
    backend._tool = tool
    return backend


def test_controller_clamps_what_the_backend_reports() -> None:
    assert VolumeController(FakeBackend(volume=150)).get() == MAX_VOLUME
    assert VolumeController(FakeBackend(volume=-4)).get() == MIN_VOLUME
    assert VolumeController(FakeBackend(volume=42)).backend_name == "fake"


def test_setting_zero_does_not_unmute() -> None:
    backend = FakeBackend(muted=True)
    assert VolumeController(backend).set(0) == 0
    assert backend.muted is True


def test_mute_helpers_report_the_new_state() -> None:
    controller = VolumeController(FakeBackend(muted=False))
    assert controller.is_muted() is False
    assert controller.mute() is True
    assert controller.unmute() is False
    assert controller.toggle_mute() is True
    assert controller.toggle_mute() is False


def test_controller_builds_a_backend_when_none_is_given(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(volume_core, "create_backend", lambda: FakeBackend(volume=7))
    assert VolumeController().get() == 7


@pytest.mark.parametrize("value", [True, False, 101, -1, 1.5, "50", None])
def test_validate_rejects_non_percentages(value: object) -> None:
    with pytest.raises(InvalidInput):
        _validate(value)


def test_validate_accepts_the_full_range() -> None:
    assert _validate(0) == 0
    assert _validate(100) == 100


def test_validate_step_bounds() -> None:
    assert _validate_step(1) == 1
    assert _validate_step(100) == 100
    for value in (0, 101, True, "5"):
        with pytest.raises(InvalidInput):
            _validate_step(value)


def test_clamp_bounds() -> None:
    assert _clamp(-1) == MIN_VOLUME
    assert _clamp(101) == MAX_VOLUME
    assert _clamp(50) == 50


def test_parse_percent_reads_the_first_percentage() -> None:
    assert _parse_percent("Volume: front-left: 32768 /  50% / -18.06 dB") == 50
    with pytest.raises(OperationFailed, match="unexpected volume output"):
        _parse_percent("no number here")


def test_run_command_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_command(monkeypatch, stdout="42\n")
    assert volume_core._run_command(["tool"]) == "42\n"
    assert calls == [["tool"]]


def test_run_command_reports_a_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise FileNotFoundError

    monkeypatch.setattr(volume_core.subprocess, "run", fake_run)
    with pytest.raises(OperationFailed, match="required command not found: osascript"):
        volume_core._run_command(["osascript"])


def test_run_command_reports_a_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(cmd="pactl", timeout=10)

    monkeypatch.setattr(volume_core.subprocess, "run", fake_run)
    with pytest.raises(OperationFailed, match="pactl timed out"):
        volume_core._run_command(["pactl"])


def test_run_command_reports_an_os_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> SimpleNamespace:
        raise OSError("cannot execute")

    monkeypatch.setattr(volume_core.subprocess, "run", fake_run)
    with pytest.raises(OperationFailed, match="could not run amixer"):
        volume_core._run_command(["amixer"])


def test_run_command_surfaces_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_command(monkeypatch, stderr="boom\n", returncode=2)
    with pytest.raises(OperationFailed, match="boom"):
        volume_core._run_command(["tool"])


def test_run_command_falls_back_to_stdout_then_the_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_command(monkeypatch, stdout="out", returncode=2)
    with pytest.raises(OperationFailed, match="out"):
        volume_core._run_command(["tool"])

    _stub_command(monkeypatch, returncode=7)
    with pytest.raises(OperationFailed, match="exit code 7"):
        volume_core._run_command(["tool"])


def test_create_backend_follows_the_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(volume_core.sys, "platform", "win32")
    assert isinstance(volume_core.create_backend(), WindowsVolumeBackend)

    monkeypatch.setattr(volume_core.sys, "platform", "darwin")
    assert isinstance(volume_core.create_backend(), MacOSVolumeBackend)

    monkeypatch.setattr(volume_core.sys, "platform", "linux")
    monkeypatch.setattr(volume_core, "_detect_linux_tool", lambda: "pactl")
    assert isinstance(volume_core.create_backend(), LinuxVolumeBackend)

    monkeypatch.setattr(volume_core.sys, "platform", "plan9")
    with pytest.raises(OperationFailed, match="not supported"):
        volume_core.create_backend()


def test_detect_linux_tool_prefers_pactl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(volume_core.shutil, "which", lambda name: f"/usr/bin/{name}")
    assert _detect_linux_tool() == "pactl"

    monkeypatch.setattr(volume_core.shutil, "which", lambda name: None if name == "pactl" else f"/usr/bin/{name}")
    assert _detect_linux_tool() == "wpctl"

    monkeypatch.setattr(volume_core.shutil, "which", lambda _name: None)
    with pytest.raises(OperationFailed, match="no supported Linux volume tool"):
        _detect_linux_tool()


def test_linux_pactl_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_command(monkeypatch, stdout="Volume: front-left: 32768 /  50%")
    backend = _linux("pactl")
    assert backend.get() == 50

    backend.set(40)
    backend.set_mute(True)
    backend.set_mute(False)
    assert ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "40%"] in calls
    assert ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"] in calls
    assert ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"] in calls

    _stub_command(monkeypatch, stdout="Mute: yes\n")
    assert _linux("pactl").get_mute() is True


def test_linux_wpctl_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_command(monkeypatch, stdout="Volume: 0.45 [muted]\n")
    backend = _linux("wpctl")
    assert backend.get() == 45
    assert backend.get_mute() is True

    backend.set(30)
    backend.set_mute(False)
    assert ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "0.30"] in calls
    assert ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"] in calls


def test_linux_amixer_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_command(monkeypatch, stdout="Front Left: Playback 40 [50%] [on]\n")
    backend = _linux("amixer")
    assert backend.get() == 50
    assert backend.get_mute() is False

    backend.set(20)
    backend.set_mute(True)
    assert ["amixer", "sset", "Master", "20%"] in calls
    assert ["amixer", "sset", "Master", "mute"] in calls


def test_linux_tool_parse_failures_are_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_command(monkeypatch, stdout="nothing useful")
    with pytest.raises(OperationFailed, match="unexpected wpctl output"):
        _linux("wpctl").get()
    with pytest.raises(OperationFailed, match="unexpected amixer output"):
        _linux("amixer").get()


def test_macos_backend_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_command(monkeypatch, stdout="55\n")
    backend = MacOSVolumeBackend()
    assert backend.get() == 55

    backend.set(20)
    backend.set_mute(True)
    assert ["osascript", "-e", "set volume output volume 20"] in calls
    assert ["osascript", "-e", "set volume output muted true"] in calls

    _stub_command(monkeypatch, stdout="true\n")
    assert backend.get_mute() is True
    _stub_command(monkeypatch, stdout="false\n")
    assert backend.get_mute() is False


def test_macos_backend_rejects_unexpected_output(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_command(monkeypatch, stdout="loud\n")
    with pytest.raises(OperationFailed, match="unexpected osascript output"):
        MacOSVolumeBackend().get()


class FakeEndpoint:
    def __init__(self) -> None:
        self.scalar = 0.36
        self.muted = False

    def GetMasterVolumeLevelScalar(self) -> float:
        return self.scalar

    def SetMasterVolumeLevelScalar(self, scalar: float, _context: object) -> None:
        self.scalar = scalar

    def GetMute(self) -> int:
        return 1 if self.muted else 0

    def SetMute(self, value: int, _context: object) -> None:
        self.muted = bool(value)


def test_windows_backend_round_trip() -> None:
    endpoint = FakeEndpoint()
    backend = WindowsVolumeBackend()
    backend._endpoint = lambda: endpoint

    assert backend.name == "windows"
    assert backend.get() == 36
    backend.set(50)
    assert endpoint.scalar == 0.5
    assert backend.get_mute() is False
    backend.set_mute(True)
    assert backend.get_mute() is True


def test_windows_backend_wraps_endpoint_errors() -> None:
    class Broken:
        def GetMasterVolumeLevelScalar(self) -> float:
            raise RuntimeError("no device")

        def SetMasterVolumeLevelScalar(self, *_args: object) -> None:
            raise RuntimeError("no device")

        def GetMute(self) -> int:
            raise RuntimeError("no device")

        def SetMute(self, *_args: object) -> None:
            raise RuntimeError("no device")

    backend = WindowsVolumeBackend()
    backend._endpoint = lambda: Broken()

    for call, message in (
        (backend.get, "could not read the master volume"),
        (lambda: backend.set(10), "could not set the master volume"),
        (backend.get_mute, "could not read the mute state"),
        (lambda: backend.set_mute(True), "could not set the mute state"),
    ):
        with pytest.raises(OperationFailed, match=message):
            call()


def test_windows_backend_requires_pycaw(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_import(name: str) -> object:
        raise ImportError(name)

    monkeypatch.setattr(volume_core, "import_module", fake_import)
    with pytest.raises(OperationFailed, match="requires pycaw"):
        WindowsVolumeBackend().get()


def test_windows_backend_rejects_a_partial_pycaw(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(volume_core, "import_module", lambda _name: SimpleNamespace())
    with pytest.raises(OperationFailed, match="missing AudioUtilities"):
        WindowsVolumeBackend().get()


def test_windows_backend_reports_a_speaker_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> object:
        raise RuntimeError("no speakers")

    module = SimpleNamespace(AudioUtilities=SimpleNamespace(GetSpeakers=boom))
    monkeypatch.setattr(volume_core, "import_module", lambda _name: module)
    with pytest.raises(OperationFailed, match="could not open the default audio device"):
        WindowsVolumeBackend().get()


def test_windows_backend_activates_the_endpoint_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    class EndpointType:
        _iid_ = "iid"

    class Device:
        EndpointVolume = None

        def Activate(self, *_args: object) -> str:
            return "raw-interface"

    module = SimpleNamespace(
        AudioUtilities=SimpleNamespace(GetSpeakers=lambda: Device()),
        IAudioEndpointVolume=EndpointType,
    )
    fakes = {
        "pycaw.pycaw": module,
        "comtypes": SimpleNamespace(CLSCTX_ALL=1),
        "ctypes": SimpleNamespace(POINTER=lambda kind: ("pointer", kind), cast=lambda _value, _kind: "endpoint"),
    }
    monkeypatch.setattr(volume_core, "import_module", lambda name: fakes[name])
    assert WindowsVolumeBackend()._endpoint() == "endpoint"
