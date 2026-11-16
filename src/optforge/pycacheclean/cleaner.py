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

            def on_error(
                _func: Any,
                path: str,
                exc_info: tuple[type[BaseException], BaseException, Any],
                errors: list[str] = errors,
            ) -> None:
                errors.append(f"{path}: {exc_info[1]}")

            try:
                # ``onerror`` is deprecated in favour of ``onexc`` from 3.12 on,
                # but it is the only spelling that exists on 3.11. Switch when
                # the floor moves to 3.12.
                self._remover(target.path, onerror=on_error)
            except OSError as exc:
                failed.append(CleanFailure(path=target.path, error=str(exc)))
                continue
            if errors:
                failed.append(CleanFailure(path=target.path, error="; ".join(errors)))
            else:
                removed.append(target)

        return CleanReport(dry_run=dry_run, removed=removed, failed=failed)
