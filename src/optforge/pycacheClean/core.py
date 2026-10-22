"""Utility functions for cleaning Python cache folders."""

from __future__ import annotations

import os
from pathlib import Path


def find_cache_dirs(
    root: str | os.PathLike[str],
    *,
    recursive: bool = True,
    max_depth: int | None = None,
    exclude: set[str] | None = None,
) -> list[Path]:
    """Return all __pycache__ directories beneath a root."""
    root_path = Path(root)
    exclude = exclude or set()
    matches: list[Path] = []

    if not root_path.exists():
        return matches

    if recursive:
        iterator = root_path.rglob("__pycache__")
    else:
        iterator = root_path.glob("__pycache__")

    for path in iterator:
        if not path.is_dir():
            continue
        if any(part in exclude for part in path.parts):
            continue
        if max_depth is not None:
            relative_to_root = path.relative_to(root_path)
            if len(relative_to_root.parts) > max_depth:
                continue
        matches.append(path)

    return sorted({p.resolve() for p in matches}, key=lambda p: str(p))


def clean_pycache(
    root: str | os.PathLike[str] = ".",
    *,
    recursive: bool = True,
    max_depth: int | None = None,
    exclude: set[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Delete __pycache__ directories found under a root."""
    cleaned: list[str] = []
    for path in find_cache_dirs(root, recursive=recursive, max_depth=max_depth, exclude=exclude):
        if dry_run:
            cleaned.append(str(path))
            continue
        try:
            for child in sorted(path.iterdir(), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    if child.name == "__pycache__":
                        continue
                    for nested in clean_pycache(child, recursive=True, max_depth=max_depth, exclude=exclude, dry_run=False):
                        pass
            path.rmdir()
            cleaned.append(str(path))
        except OSError:
            continue
    return cleaned
