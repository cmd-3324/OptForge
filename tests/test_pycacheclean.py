from __future__ import annotations

import os
from pathlib import Path

import pytest

from optforge.core.errors import InvalidInput, NotFound
from optforge.pycacheclean.cleaner import CacheCleaner
from optforge.pycacheclean.models import CacheTarget
from optforge.pycacheclean.scanner import CacheScanner
from optforge.pycacheclean.service import CacheService


def build_tree(root: Path) -> None:
    (root / "pkg" / "__pycache__").mkdir(parents=True)
    (root / "pkg" / "__pycache__" / "a.pyc").write_bytes(b"abc")
    (root / "pkg" / "sub" / "__pycache__").mkdir(parents=True)
    (root / ".venv" / "lib" / "__pycache__").mkdir(parents=True)
    (root / "node_modules" / "__pycache__").mkdir(parents=True)


def test_scanner_finds_nested_caches_and_skips_venvs(tmp_path: Path) -> None:
    build_tree(tmp_path)
    found = CacheScanner().scan(tmp_path, measure=True)
    names = {target.path.relative_to(tmp_path).as_posix() for target in found}
    assert names == {"pkg/__pycache__", "pkg/sub/__pycache__"}
    first = next(target for target in found if target.path.name == "__pycache__")
    assert first.files >= 1
    assert first.bytes >= 3


def test_scanner_can_include_venvs(tmp_path: Path) -> None:
    build_tree(tmp_path)
    found = CacheScanner().scan(tmp_path, skip_venvs=False)
    names = {target.path.relative_to(tmp_path).as_posix() for target in found}
    assert ".venv/lib/__pycache__" in names


def test_scanner_respects_depth_and_exclude(tmp_path: Path) -> None:
    build_tree(tmp_path)
    shallow = CacheScanner().scan(tmp_path, max_depth=2)
    assert {target.path.relative_to(tmp_path).as_posix() for target in shallow} == {"pkg/__pycache__"}

    excluded = CacheScanner().scan(tmp_path, exclude={"pkg"})
    assert excluded == []


def test_scanner_non_recursive_only_checks_direct_child(tmp_path: Path) -> None:
    build_tree(tmp_path)
    assert CacheScanner().scan(tmp_path, recursive=False) == []
    (tmp_path / "__pycache__").mkdir()
    assert len(CacheScanner().scan(tmp_path, recursive=False)) == 1


def test_cleaner_dry_run_does_not_delete(tmp_path: Path) -> None:
    target = tmp_path / "__pycache__"
    target.mkdir()
    report = CacheCleaner().clean([CacheTarget(path=target)], dry_run=True)
    assert report.dry_run is True
    assert report.ok is True
    assert target.exists()


def test_cleaner_reports_failures(tmp_path: Path) -> None:
    target = tmp_path / "__pycache__"
    target.mkdir()

    def broken(_path: Path, **_kwargs: object) -> None:
        raise OSError("locked")

    report = CacheCleaner(remover=broken).clean([CacheTarget(path=target)])
    assert report.ok is False
    assert report.failed[0].error == "locked"


def test_cleaner_reports_partial_errors(tmp_path: Path) -> None:
    target = tmp_path / "__pycache__"
    target.mkdir()

    def partial(_path: Path, **kwargs: object) -> None:
        callback = kwargs["onerror"]
        assert callable(callback)
        callback(None, str(target), (OSError, OSError("partial"), None))

    report = CacheCleaner(remover=partial).clean([CacheTarget(path=target)])
    assert report.ok is False
    assert "partial" in report.failed[0].error


def test_service_validates_paths(tmp_path: Path) -> None:
    service = CacheService()
    with pytest.raises(NotFound):
        service.scan(tmp_path / "missing")

    file_path = tmp_path / "file.txt"
    file_path.write_text("x")
    with pytest.raises(InvalidInput):
        service.scan(file_path)


def test_service_clean_dry_run(tmp_path: Path) -> None:
    build_tree(tmp_path)
    report = CacheService().clean(tmp_path, dry_run=True)
    assert report.dry_run is True
    assert len(report.removed) == 2
    assert (tmp_path / "pkg" / "__pycache__").exists()


def test_scanner_measures_nested_files_and_bytes(tmp_path: Path) -> None:
    cache = tmp_path / "pkg" / "__pycache__"
    (cache / "deep").mkdir(parents=True)
    (cache / "a.pyc").write_bytes(b"12345")
    (cache / "deep" / "b.pyc").write_bytes(b"67")

    [target] = CacheScanner().scan(tmp_path)
    assert target.files == 2
    assert target.bytes == 7


def test_scanner_can_skip_measuring(tmp_path: Path) -> None:
    cache = tmp_path / "pkg" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "a.pyc").write_bytes(b"x")

    [target] = CacheScanner().scan(tmp_path, measure=False)
    assert target.files == 0
    assert target.bytes == 0


def test_scanner_does_not_descend_into_a_cache_directory(tmp_path: Path) -> None:
    nested = tmp_path / "pkg" / "__pycache__" / "nested" / "__pycache__"
    nested.mkdir(parents=True)

    found = CacheScanner().scan(tmp_path)
    assert [target.path.relative_to(tmp_path).as_posix() for target in found] == ["pkg/__pycache__"]


def test_scanner_returns_targets_sorted_by_path(tmp_path: Path) -> None:
    for name in ("z", "a", "m"):
        (tmp_path / name / "__pycache__").mkdir(parents=True)

    assert [target.path.parent.name for target in CacheScanner().scan(tmp_path)] == ["a", "m", "z"]


def test_scanner_skips_every_venv_name_by_default(tmp_path: Path) -> None:
    for name in ("venv", ".venv", "env", ".env"):
        (tmp_path / name / "lib" / "__pycache__").mkdir(parents=True)

    assert CacheScanner().scan(tmp_path) == []


def test_scanner_can_walk_a_virtualenv(tmp_path: Path) -> None:
    (tmp_path / "env" / "lib" / "__pycache__").mkdir(parents=True)

    found = CacheScanner().scan(tmp_path, skip_venvs=False)
    assert [target.path.parent.parent.name for target in found] == ["env"]


def test_scanner_skips_noise_directories(tmp_path: Path) -> None:
    for name in (".git", "node_modules", "site-packages", ".pytest_cache"):
        (tmp_path / name / "__pycache__").mkdir(parents=True)

    assert CacheScanner().scan(tmp_path) == []


def test_scanner_constructor_skip_is_case_insensitive(tmp_path: Path) -> None:
    (tmp_path / "build" / "__pycache__").mkdir(parents=True)
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)

    found = CacheScanner(skip={"BUILD"}).scan(tmp_path)
    assert [target.path.parent.name for target in found] == ["pkg"]


def test_scanner_max_depth_one_only_looks_at_direct_children(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)

    found = CacheScanner().scan(tmp_path, max_depth=1)
    assert {target.path.relative_to(tmp_path).as_posix() for target in found} == {"__pycache__"}


def test_scanner_non_recursive_ignores_a_file_named_like_a_cache(tmp_path: Path) -> None:
    (tmp_path / "__pycache__").write_text("not a directory", encoding="utf-8")

    assert CacheScanner().scan(tmp_path, recursive=False) == []


def test_scanner_skips_a_symlinked_cache_directory(tmp_path: Path) -> None:
    target = tmp_path / "outside" / "__pycache__"
    target.mkdir(parents=True)
    root = tmp_path / "root"
    root.mkdir()
    try:
        (root / "__pycache__").symlink_to(target, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are unavailable on this platform")

    assert CacheScanner().scan(root) == []


def test_scanner_survives_an_unreadable_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)
    real_scandir = os.scandir

    def guarded(path: str | os.PathLike[str]) -> object:
        if Path(path).name == "pkg":
            raise PermissionError("denied")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", guarded)
    assert CacheScanner().scan(tmp_path) == []


def test_scanner_reports_zero_size_when_the_cache_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cache = tmp_path / "pkg" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "a.pyc").write_bytes(b"abcd")
    blocked = os.path.abspath(cache)
    real_scandir = os.scandir

    def guarded(path: str | os.PathLike[str]) -> object:
        if os.path.abspath(path) == blocked:
            raise PermissionError("denied")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", guarded)
    [target] = CacheScanner().scan(tmp_path)
    assert target.files == 0
    assert target.bytes == 0
