from __future__ import annotations

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
        # The package passes ``onexc`` on 3.12+ and ``onerror`` on 3.11.
        callback = kwargs.get("onexc", kwargs.get("onerror"))
        assert callable(callback)
        callback(None, str(target), OSError("partial"))

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
