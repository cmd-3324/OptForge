from __future__ import annotations

from optforge import __version__
from optforge.core.version import get_version


def test_source_version_is_exposed() -> None:
    assert __version__ == "0.3.0"


def test_get_version_falls_back_for_unknown_distribution() -> None:
    assert get_version("optforge-definitely-not-installed") == "0.3.0"
