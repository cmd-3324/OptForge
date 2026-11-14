from __future__ import annotations

from types import SimpleNamespace

import pytest

from optforge.core.errors import OperationFailed
from optforge.diskcheck.service import DiskService


def test_usage_computes_percent() -> None:
    service = DiskService(usage=lambda _path: (1000, 250, 750))
    info = service.usage(".")
    assert info.total == 1000
    assert info.used == 250
    assert info.free == 750
    assert info.percent_used == 25.0
    assert info.percent_free == 75.0


def test_usage_of_empty_device_does_not_divide_by_zero() -> None:
    service = DiskService(usage=lambda _path: (0, 0, 0))
    assert service.usage(".").percent_used == 0.0


def test_usage_failure_is_wrapped() -> None:
    def broken(_path: str) -> tuple[int, int, int]:
        raise OSError("nope")

    with pytest.raises(OperationFailed):
        DiskService(usage=broken).usage(".")


def test_to_dict_rounds_percentages() -> None:
    service = DiskService(usage=lambda _path: (3, 1, 2))
    payload = service.usage(".").to_dict()
    assert payload["percent_used"] == 33.33
    assert payload["percent_free"] == 66.67


def test_volumes_skip_unreadable_mounts() -> None:
    partitions = [
        SimpleNamespace(mountpoint="/good"),
        SimpleNamespace(mountpoint="/bad"),
        SimpleNamespace(mountpoint=None),
    ]

    def usage(path: str) -> tuple[int, int, int]:
        if path == "/bad":
            raise OSError("denied")
        return (100, 40, 60)

    service = DiskService(usage=usage, partitions=lambda **_kwargs: partitions)
    volumes = service.volumes()
    assert [volume.path for volume in volumes] == [str(service.usage("/good").path)]
