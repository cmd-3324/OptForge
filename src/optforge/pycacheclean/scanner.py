"""Discovery of ``__pycache__`` directories with venv and symlink safety."""

from __future__ import annotations

import os
from pathlib import Path

from optforge.pycacheclean.models import CacheTarget

_CACHE_DIR = "__pycache__"
_VENV_DIRS = frozenset({"venv", ".venv", "env", ".env"})
_DEFAULT_SKIP = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "node_modules",
        "site-packages",
    }
)


class CacheScanner:
    """Walk a tree and return every cache directory worth removing.

    The scanner never follows symlinks, never descends into a cache directory,
    and skips virtualenvs by default so a cleanup does not destroy a project's
    installed dependencies.
    """

    def __init__(self, skip: set[str] | None = None, *, skip_venvs: bool = True) -> None:
        self._extra_skip = {name.lower() for name in (skip or set())}
        self._skip_venvs = skip_venvs

    def scan(
        self,
        root: str | os.PathLike[str],
        *,
        recursive: bool = True,
        max_depth: int | None = None,
        exclude: set[str] | None = None,
        measure: bool = True,
        skip_venvs: bool | None = None,
    ) -> list[CacheTarget]:
        """Return matching cache directories under ``root``."""
        root_path = Path(root).expanduser()
        skip = self._build_skip(exclude, skip_venvs)
        if not recursive:
            candidate = root_path / _CACHE_DIR
            return [self._target(candidate, measure)] if candidate.is_dir() else []

        targets: list[CacheTarget] = []
        stack: list[tuple[str, int]] = [(os.fspath(root_path), 0)]
        while stack:
            current, depth = stack.pop()
            try:
                entries = list(os.scandir(current))
            except OSError:
                continue
            for entry in entries:
                try:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    continue
                name = entry.name
                if name.lower() in skip:
                    continue
                child_depth = depth + 1
                if name == _CACHE_DIR:
                    if max_depth is None or child_depth <= max_depth:
                        targets.append(self._target(Path(entry.path), measure))
                    continue
                if max_depth is not None and child_depth >= max_depth:
                    continue
                stack.append((entry.path, child_depth))

        return sorted(targets, key=lambda target: str(target.path))

    def _build_skip(self, exclude: set[str] | None, skip_venvs: bool | None) -> set[str]:
        skip = set(self._extra_skip) | _DEFAULT_SKIP
        include_venvs = self._skip_venvs if skip_venvs is None else skip_venvs
        if include_venvs:
            skip |= _VENV_DIRS
        else:
            skip -= _VENV_DIRS
        skip |= {name.lower() for name in (exclude or set())}
        return skip

    @staticmethod
    def _target(path: Path, measure: bool) -> CacheTarget:
        if not measure:
            return CacheTarget(path=path)
        files, size = _measure(path)
        return CacheTarget(path=path, files=files, bytes=size)


def _measure(path: Path) -> tuple[int, int]:
    files = 0
    size = 0
    stack = [os.fspath(path)]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(entry.path)
                elif entry.is_file(follow_symlinks=False):
                    files += 1
                    size += entry.stat(follow_symlinks=False).st_size
            except OSError:
                continue
    return files, size
