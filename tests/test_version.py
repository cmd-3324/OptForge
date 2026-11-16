from __future__ import annotations

import re

from optforge import __all__, __version__
from optforge.core.version import get_version


def test_source_version_is_exposed() -> None:
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert "__version__" in __all__


def test_get_version_falls_back_for_unknown_distribution() -> None:
    assert get_version("optforge-definitely-not-installed") == __version__
