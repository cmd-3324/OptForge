"""Deletion of discovered cache directories, with per-target failure reporting."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable, Iterable
from typing import Any

from optforge.pycacheclean.models import CacheTarget, CleanFailure, CleanReport

Remover = Callable[..., Any]

# ``shutil.rmtree`` reports per-file errors through ``onexc`` from 3.12 on;
# ``onerror`` is the spelling available on 3.11.
_HAS_ONEXC = sys.version_info >= (3, 12)


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
                exc: BaseException | tuple[type[BaseException], BaseException, Any],
                errors: list[str] = errors,
            ) -> None:
                # ``onexc`` passes the exception; ``onerror`` passes exc_info.
                detail = exc if isinstance(exc, BaseException) else exc[1]
                errors.append(f"{path}: {detail}")

            try:
                if _HAS_ONEXC:
                    self._remover(target.path, onexc=on_error)
                else:
                    self._remover(target.path, onerror=on_error)
            except OSError as exc:
                failed.append(CleanFailure(path=target.path, error=str(exc)))
                continue
            if errors:
                failed.append(CleanFailure(path=target.path, error="; ".join(errors)))
            else:
                removed.append(target)

        return CleanReport(dry_run=dry_run, removed=removed, failed=failed)
