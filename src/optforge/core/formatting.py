"""Small, dependency-free formatting helpers shared by the CLIs."""

from __future__ import annotations

_BINARY_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")


def format_bytes(value: int | float) -> str:
    """Render a byte count using binary units (1024-based).

    >>> format_bytes(1536)
    '1.50 KiB'
    """
    size = float(value)
    unit = _BINARY_UNITS[0]
    for candidate in _BINARY_UNITS:
        unit = candidate
        if abs(size) < 1024.0 or candidate == _BINARY_UNITS[-1]:
            break
        size /= 1024.0
    return f"{size:.2f} {unit}"


def format_percent(value: float, *, digits: int = 2) -> str:
    """Render a percentage with a fixed number of decimal places."""
    return f"{value:.{digits}f}%"
