"""Output-volume control for the default audio device."""

from __future__ import annotations

from optforge.volume.core import MAX_VOLUME, MIN_VOLUME, VolumeBackend, VolumeController, create_backend

__all__ = ["MAX_VOLUME", "MIN_VOLUME", "VolumeBackend", "VolumeController", "create_backend"]
