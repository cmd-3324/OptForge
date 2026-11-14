from __future__ import annotations

import json
from io import StringIO

from rich.console import Console

from optforge.core.console import ConsoleIO


def make_console() -> tuple[ConsoleIO, StringIO, StringIO]:
    out = StringIO()
    err = StringIO()
    console = ConsoleIO(
        out=Console(file=out, force_terminal=False, width=200),
        err=Console(file=err, force_terminal=False, width=200),
    )
    return console, out, err


def test_error_treats_markup_as_literal() -> None:
    console, _, err = make_console()
    console.error("Could not read C:\\tmp[/]")
    assert "[/]" in err.getvalue()


def test_success_treats_markup_as_literal() -> None:
    console, out, _ = make_console()
    console.success("connected to [host]")
    assert "[host]" in out.getvalue()


def test_hint_and_warning_go_to_stderr() -> None:
    console, out, err = make_console()
    console.hint("hint")
    console.warning("careful")
    assert out.getvalue() == ""
    assert "hint" in err.getvalue()
    assert "careful" in err.getvalue()


def test_json_is_parseable() -> None:
    console, out, _ = make_console()
    console.json({"ok": True, "items": {2, 1}})
    assert json.loads(out.getvalue()) == {"ok": True, "items": [1, 2]}
