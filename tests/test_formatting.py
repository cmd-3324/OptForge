from __future__ import annotations

from optforge.core.formatting import format_bytes, format_percent


def test_format_bytes_uses_binary_units() -> None:
    assert format_bytes(0) == "0.00 B"
    assert format_bytes(1023) == "1023.00 B"
    assert format_bytes(1024) == "1.00 KiB"
    assert format_bytes(1536) == "1.50 KiB"
    assert format_bytes(1024**3) == "1.00 GiB"


def test_format_bytes_handles_negative_and_large_values() -> None:
    assert format_bytes(-1536) == "-1.50 KiB"
    assert format_bytes(1024**6) == "1024.00 PiB"


def test_format_percent_respects_digits() -> None:
    assert format_percent(12.3456) == "12.35%"
    assert format_percent(12.3456, digits=1) == "12.3%"
