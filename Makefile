.PHONY: help install showp lint format typecheck test clean run

# Force PowerShell so pipes/Select-Object work as you expect
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -Command

PYTHON := .venv\Scripts\python.exe

help:
@Write-Host "Targets: install showp lint format typecheck test clean"

install:
	uv sync

showp:
	$(PYTHON) --version

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

# test: showp lint
# 	uv run pytest

run:
	$(PYTHON) -m optforge.cli



clean2:
	Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Write-Host "Done. Pycache Files are Gone."



clean:
	powershell -Command "Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"
	powershell -Command "Remove-Item -Recurse -Force .mypy_cache,.ruff_cache,.pytest_cache -ErrorAction SilentlyContinue"