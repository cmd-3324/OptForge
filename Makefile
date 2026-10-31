.PHONY: help install lint format typecheck test check build clean

UV ?= uv

help:
	@echo "OptForge targets"
	@echo "  install    Sync the virtual environment (uv sync --all-extras)"
	@echo "  lint       Run ruff"
	@echo "  format     Format with ruff"
	@echo "  typecheck  Run mypy"
	@echo "  test       Run pytest"
	@echo "  check      lint + typecheck + test"
	@echo "  build      Build sdist and wheel"
	@echo "  clean      Remove caches and build artifacts"

install:
	$(UV) sync --all-extras

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

typecheck:
	$(UV) run mypy src

test:
	$(UV) run pytest

check: lint typecheck test

build:
	$(UV) build

clean:
	$(UV) run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; [shutil.rmtree(p, ignore_errors=True) for p in ('.mypy_cache', '.ruff_cache', '.pytest_cache', 'dist', 'build')]"
