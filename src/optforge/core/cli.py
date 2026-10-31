"""Shared CLI plumbing: exit codes and a consistent error boundary."""

from __future__ import annotations

from enum import IntEnum
from types import TracebackType
from typing import Self

import typer

from optforge.core.console import ConsoleIO
from optforge.core.errors import OptForgeError, PermissionDenied


class ExitCode(IntEnum):
    """Exit codes shared by every OptForge command.

    ``0`` and ``1`` answer a yes/no question; ``2`` is reserved by Typer for
    invalid usage; ``3`` means the check could not run.
    """

    OK = 0
    NO = 1
    ERROR = 3


class ErrorBoundary:
    """Convert expected exceptions into a clean message and exit code 3.

    Unexpected exceptions are re-raised untouched so they keep their traceback.
    """

    def __init__(self, console: ConsoleIO, *, permission_hint: str | None = None) -> None:
        self._console = console
        self._permission_hint = permission_hint

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if exc is None:
            return False
        if isinstance(exc, PermissionDenied):
            self._console.error(str(exc))
            if self._permission_hint:
                self._console.hint(self._permission_hint)
            raise typer.Exit(ExitCode.ERROR) from exc
        if isinstance(exc, OptForgeError):
            self._console.error(str(exc))
            raise typer.Exit(ExitCode.ERROR) from exc
        return False
