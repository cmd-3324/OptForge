"""Facade for scanning and cleaning Python cache directories."""

from __future__ import annotations

import os
from pathlib import Path

from optforge.core.errors import InvalidInput, NotFound
from optforge.pycacheclean.cleaner import CacheCleaner
from optforge.pycacheclean.models import CacheTarget, CleanReport
from optforge.pycacheclean.scanner import CacheScanner


class CacheService:
    """Resolve a root, scan it, then delete or preview the matches."""

    def __init__(self, scanner: CacheScanner | None = None, cleaner: CacheCleaner | None = None) -> None:
        self._scanner = scanner or CacheScanner()
        self._cleaner = cleaner or CacheCleaner()

    def scan(
        self,
        root: str | os.PathLike[str] = ".",
        *,
        recursive: bool = True,
        max_depth: int | None = None,
        exclude: set[str] | None = None,
        skip_venvs: bool = True,
        measure: bool = True,
        allow_root: bool = False,
    ) -> list[CacheTarget]:
        path = self._validate_root(root, allow_root=allow_root)
        return self._scanner.scan(
            path,
            recursive=recursive,
            max_depth=max_depth,
            exclude=exclude,
            measure=measure,
            skip_venvs=skip_venvs,
        )

    def remove(self, targets: list[CacheTarget], *, dry_run: bool = False) -> CleanReport:
        return self._cleaner.clean(targets, dry_run=dry_run)

    def clean(
        self,
        root: str | os.PathLike[str] = ".",
        *,
        recursive: bool = True,
        max_depth: int | None = None,
        exclude: set[str] | None = None,
        skip_venvs: bool = True,
        measure: bool = True,
        dry_run: bool = False,
        allow_root: bool = False,
    ) -> CleanReport:
        targets = self.scan(
            root,
            recursive=recursive,
            max_depth=max_depth,
            exclude=exclude,
            skip_venvs=skip_venvs,
            measure=measure,
            allow_root=allow_root,
        )
        return self.remove(targets, dry_run=dry_run)

    @staticmethod
    def _validate_root(root: str | os.PathLike[str], *, allow_root: bool) -> Path:
        path = Path(root).expanduser()
        if not path.exists():
            raise NotFound(f"Path does not exist: {path}")
        if not path.is_dir():
            raise InvalidInput(f"Not a directory: {path}")
        if not allow_root and path.resolve() == Path(path.anchor):
            raise InvalidInput(
                f"Refusing to scan the filesystem root {path}. Pass --allow-root if you mean it."
            )
        return path
