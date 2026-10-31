"""A thin, markup-safe wrapper around Rich consoles.

Every value that comes from the operating system (process names, environment
variables, paths) is rendered through :class:`rich.text.Text` so a value such as
``[red]oops`` can never inject markup into the terminal.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from contextlib import AbstractContextManager
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.text import Text


class ConsoleIO:
    """Human output on stdout and diagnostics on stderr."""

    def __init__(
        self,
        out: Console | None = None,
        err: Console | None = None,
        *,
        force_terminal: bool | None = None,
    ) -> None:
        self.out = out or Console(force_terminal=force_terminal)
        self.err = err or Console(stderr=True, force_terminal=force_terminal)

    def print(self, *values: Any, **kwargs: Any) -> None:
        self.out.print(*values, **kwargs)

    def text(self, value: object) -> None:
        """Print a value verbatim, with no markup interpretation."""
        self.out.print(Text(str(value)))

    def success(self, message: str) -> None:
        self.out.print(f"[green]{message}[/green]")

    def warning(self, message: str) -> None:
        self.err.print(f"[yellow]{message}[/yellow]")

    def error(self, message: str) -> None:
        self.err.print(f"[red]error:[/red] {message}")

    def hint(self, message: str) -> None:
        self.err.print(f"[dim]{message}[/dim]")

    def json(self, data: Any) -> None:
        """Emit exact, machine-parseable JSON on stdout."""
        payload = json.dumps(data, indent=2, ensure_ascii=False, default=_json_default)
        self.out.print(payload, markup=False, highlight=False, soft_wrap=True)

    def table(self, title: str | None, columns: Sequence[tuple[str, dict[str, Any]]]) -> Table:
        table = Table(title=title, title_justify="left", header_style="bold")
        for header, options in columns:
            table.add_column(header, **options)
        return table

    @staticmethod
    def cell(value: object) -> Text:
        """Return a Rich cell that treats ``value`` as literal text."""
        return Text(str(value))

    def status(self, message: str) -> AbstractContextManager[Any]:
        return self.out.status(message)

    def render(self, *renderables: Iterable[Any] | Any) -> None:
        for renderable in renderables:
            self.out.print(renderable)


def _json_default(value: Any) -> Any:
    if isinstance(value, set | frozenset):
        return sorted(value)
    if hasattr(value, "__fspath__"):
        return str(value)
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
