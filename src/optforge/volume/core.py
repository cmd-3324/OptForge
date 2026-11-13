"""Output-volume control for the default audio device."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from importlib import import_module
from typing import Any, Protocol

from optforge.core.errors import InvalidInput, OperationFailed

MIN_VOLUME = 0
MAX_VOLUME = 100


class VolumeBackend(Protocol):
    """Platform-specific access to the default output volume."""

    name: str

    def get(self) -> int:
        """Return the current volume as a percentage."""
        ...

    def set(self, percent: int) -> None:
        """Set the volume to ``percent`` (0-100)."""
        ...

    def get_mute(self) -> bool:
        """Return whether the output is muted."""
        ...

    def set_mute(self, muted: bool) -> None:
        """Mute or unmute the output."""
        ...


class VolumeController:
    """Read and change the default output volume."""

    def __init__(self, backend: VolumeBackend | None = None) -> None:
        self._backend = backend or create_backend()

    @property
    def backend_name(self) -> str:
        return self._backend.name

    def get(self) -> int:
        return _clamp(self._backend.get())

    def set(self, percent: int) -> int:
        value = _validate(percent)
        self._backend.set(value)
        if value > 0:
            self._backend.set_mute(False)
        return value

    def full(self) -> int:
        return self.set(MAX_VOLUME)

    def none(self) -> int:
        return self.set(MIN_VOLUME)

    def up(self, step: int = 5) -> int:
        return self.set(min(MAX_VOLUME, self.get() + _validate_step(step)))

    def down(self, step: int = 5) -> int:
        return self.set(max(MIN_VOLUME, self.get() - _validate_step(step)))

    def is_muted(self) -> bool:
        return self._backend.get_mute()

    def mute(self) -> bool:
        self._backend.set_mute(True)
        return True

    def unmute(self) -> bool:
        self._backend.set_mute(False)
        return False

    def toggle_mute(self) -> bool:
        muted = not self._backend.get_mute()
        self._backend.set_mute(muted)
        return muted


def create_backend() -> VolumeBackend:
    if sys.platform == "win32":
        return WindowsVolumeBackend()
    if sys.platform == "darwin":
        return MacOSVolumeBackend()
    if sys.platform.startswith("linux"):
        return LinuxVolumeBackend()
    raise OperationFailed(f"volume control is not supported on {sys.platform!r}")


def _validate(percent: int) -> int:
    if isinstance(percent, bool) or not isinstance(percent, int):
        raise InvalidInput("volume must be a whole number between 0 and 100")
    if not MIN_VOLUME <= percent <= MAX_VOLUME:
        raise InvalidInput(f"volume must be between {MIN_VOLUME} and {MAX_VOLUME}")
    return percent


def _clamp(percent: int) -> int:
    return max(MIN_VOLUME, min(MAX_VOLUME, percent))


def _validate_step(step: int) -> int:
    if isinstance(step, bool) or not isinstance(step, int):
        raise InvalidInput("step must be a whole number between 1 and 100")
    if not 1 <= step <= MAX_VOLUME:
        raise InvalidInput(f"step must be between 1 and {MAX_VOLUME}")
    return step


def _run_command(command: list[str]) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    except FileNotFoundError as exc:
        raise OperationFailed(f"required command not found: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise OperationFailed(f"{command[0]} timed out") from exc
    except OSError as exc:
        raise OperationFailed(f"could not run {command[0]}: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise OperationFailed(detail or f"{command[0]} failed with exit code {result.returncode}")
    return result.stdout


def _parse_percent(output: str) -> int:
    match = re.search(r"(\d+)%", output)
    if match is None:
        raise OperationFailed(f"unexpected volume output: {output.strip()!r}")
    return int(match.group(1))


class WindowsVolumeBackend:
    name = "windows"

    def _endpoint(self) -> Any:
        try:
            module = import_module("pycaw.pycaw")
        except ImportError as exc:
            raise OperationFailed("Windows volume control requires pycaw. Install it with: uv sync") from exc

        audio_utilities = getattr(module, "AudioUtilities", None)
        if audio_utilities is None:
            raise OperationFailed("pycaw is missing AudioUtilities")

        try:
            device = audio_utilities.GetSpeakers()
        except Exception as exc:
            raise OperationFailed(f"could not open the default audio device: {exc}") from exc

        endpoint = getattr(device, "EndpointVolume", None)
        if endpoint is not None:
            return endpoint

        try:
            comtypes = import_module("comtypes")
            ctypes = import_module("ctypes")
            endpoint_type = module.IAudioEndpointVolume
            interface = device.Activate(endpoint_type._iid_, comtypes.CLSCTX_ALL, None)
            return ctypes.cast(interface, ctypes.POINTER(endpoint_type))
        except Exception as exc:
            raise OperationFailed(f"could not activate the audio endpoint: {exc}") from exc

    def get(self) -> int:
        endpoint = self._endpoint()
        try:
            return round(float(endpoint.GetMasterVolumeLevelScalar()) * 100)
        except Exception as exc:
            raise OperationFailed(f"could not read the master volume: {exc}") from exc

    def set(self, percent: int) -> None:
        endpoint = self._endpoint()
        try:
            endpoint.SetMasterVolumeLevelScalar(percent / 100.0, None)
        except Exception as exc:
            raise OperationFailed(f"could not set the master volume: {exc}") from exc

    def get_mute(self) -> bool:
        endpoint = self._endpoint()
        try:
            return bool(endpoint.GetMute())
        except Exception as exc:
            raise OperationFailed(f"could not read the mute state: {exc}") from exc

    def set_mute(self, muted: bool) -> None:
        endpoint = self._endpoint()
        try:
            endpoint.SetMute(1 if muted else 0, None)
        except Exception as exc:
            raise OperationFailed(f"could not set the mute state: {exc}") from exc


class MacOSVolumeBackend:
    name = "macos"

    def get(self) -> int:
        output = _run_command(["osascript", "-e", "output volume of (get volume settings)"])
        try:
            return int(output.strip())
        except ValueError as exc:
            raise OperationFailed(f"unexpected osascript output: {output.strip()!r}") from exc

    def set(self, percent: int) -> None:
        _run_command(["osascript", "-e", f"set volume output volume {percent}"])

    def get_mute(self) -> bool:
        output = _run_command(["osascript", "-e", "output muted of (get volume settings)"])
        return output.strip().lower() == "true"

    def set_mute(self, muted: bool) -> None:
        state = "true" if muted else "false"
        _run_command(["osascript", "-e", f"set volume output muted {state}"])


class LinuxVolumeBackend:
    name = "linux"

    def __init__(self) -> None:
        self._tool = _detect_linux_tool()

    def get(self) -> int:
        if self._tool == "pactl":
            return _parse_percent(_run_command(["pactl", "get-sink-volume", "@DEFAULT_SINK@"]))

        if self._tool == "wpctl":
            output = _run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
            match = re.search(r"([0-9]+(?:\.[0-9]+)?)", output)
            if match is None:
                raise OperationFailed(f"unexpected wpctl output: {output.strip()!r}")
            return round(float(match.group(1)) * 100)

        output = _run_command(["amixer", "get", "Master"])
        match = re.search(r"\[(\d+)%\]", output)
        if match is None:
            raise OperationFailed(f"unexpected amixer output: {output.strip()!r}")
        return int(match.group(1))

    def set(self, percent: int) -> None:
        if self._tool == "pactl":
            _run_command(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"])
        elif self._tool == "wpctl":
            _run_command(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{percent / 100:.2f}"])
        else:
            _run_command(["amixer", "sset", "Master", f"{percent}%"])

    def get_mute(self) -> bool:
        if self._tool == "pactl":
            output = _run_command(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
            return "yes" in output.lower()

        if self._tool == "wpctl":
            output = _run_command(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
            return "[muted]" in output.lower()

        output = _run_command(["amixer", "get", "Master"])
        return "[off]" in output.lower()

    def set_mute(self, muted: bool) -> None:
        if self._tool == "pactl":
            _run_command(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1" if muted else "0"])
        elif self._tool == "wpctl":
            _run_command(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if muted else "0"])
        else:
            _run_command(["amixer", "sset", "Master", "mute" if muted else "unmute"])


def _detect_linux_tool() -> str:
    for tool in ("pactl", "wpctl", "amixer"):
        if shutil.which(tool):
            return tool
    raise OperationFailed("no supported Linux volume tool found (install pactl, wpctl, or amixer)")
