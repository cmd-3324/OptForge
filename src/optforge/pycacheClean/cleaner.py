"""Deletion of discovered cache directories, with per-target failure reporting."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable
from typing import Any

from optforge.pycacheclean.models import CacheTarget, CleanFailure, CleanReport

Remover = Callable[..., Any]


class CacheCleaner:
    """Remove targets and report exactly what succeeded and what did not."""

    def __init__(self, remover: Remover = shutil.rmtree) -> None:
        self._remover = remover

    def clean(self, targets: Iterable[CacheTarget], *, dry_run: bool = False) -> CleanReport:
        removed: list[CacheTarget] = []
        failed: list[CleanFailure] = []

        for target in targets:
            if dry_run:
                removed.append(target)
                continue
            errors: list[str] = []

            def on_error(_func: Any, path: str, exc: BaseException) -> None:
                errors.append(f"{path}: {exc}")

            try:
                self._remover(target.path, onexc=on_error)
            except OSError as exc:
                failed.append(CleanFailure(path=target.path, error=str(exc)))
                continue
            if errors:
                failed.append(CleanFailure(path=target.path, error="; ".join(errors)))
            else:
                removed.append(target)

        return CleanReport(dry_run=dry_run, removed=removed, failed=failed)
