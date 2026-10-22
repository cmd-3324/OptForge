# OptForge

Small cross-platform developer CLI tools for inspecting listening ports, checking environment variables, monitoring disk usage, and cleaning Python cache artifacts.

Built with Python, Typer, and Rich.

## Overview

OptForge is a lightweight command-line toolkit for developers who want fast answers about the local runtime environment.

It helps you:

- inspect active TCP listeners and identify the owning process
- check whether a port is free or already in use
- test a host/port connection from the terminal
- review environment variables and runtime context
- monitor disk space and storage pressure
- remove stale Python cache artifacts from local projects

## Why use OptForge?

Whether you're starting a local service, troubleshooting an app crash, checking for port collisions, or cleaning up a messy Python workspace, OptForge gives you quick terminal-based tools without opening a full IDE or browser.

It is designed to be simple, fast, and cross-platform.

## Features

### Port inspection

- list all listening TCP ports
- show the process associated with each port
- detect whether a port is free or in use
- test connectivity to a host and port
- wait until a port reaches the desired state

### Environment checks

- inspect environment variables and runtime context
- useful for debugging app configuration issues
- helpful for local setup and deployment verification

### Disk monitoring

- inspect filesystem usage and storage conditions
- identify when available disk space is running low
- support local development diagnostics

### Python cache cleanup

- remove `__pycache__` directories and stale Python bytecode files
- help keep workspaces clean and reduce clutter
- useful for large repositories or repeated development cycles

## Installation

### Install with pipx

The recommended installation method is pipx:

```bash
pipx install git+https://github.com/cmd-3324/OptForge.git
```

If you are working from a local clone:

```bash
cd OptForge
pipx install --editable .
```

### Install with pip

```bash
git clone https://github.com/cmd-3324/OptForge.git
cd OptForge
python -m pip install .
```

### Download the latest Windows executable

You can download the latest Windows `.exe` release directly from GitHub Releases:

```text
https://github.com/cmd-3324/OptForge/releases/latest
```

This is useful if you want to run OptForge without installing Python dependencies manually.

## Quick start

After installation, the package exposes the following commands:

```bash
portcheck --help
envcheck --help
diskcheck --help
pycacheClean --help
```

## Usage examples

### Check ports

```bash
portcheck list
portcheck list --sort process
portcheck check 8000
portcheck find 5432
portcheck connect localhost 5432
portcheck wait 8000 --until free --timeout 60
```

### Inspect the environment

```bash
envcheck
```

### Check disk usage

```bash
diskcheck
```

### Clean Python cache files

```bash
pycacheClean --recursive
pycacheClean --depth 2
```

## Project structure

```text
OptForge/
├── src/
│   └── optforge/
│       ├── diskcheck/
│       ├── envcheck/
│       ├── portcheck/
│       └── pycacheClean/
├── Makefile
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
└── .python-version
```

## Development

The repository uses Python packaging and a modern CLI setup.

Common commands:

```bash
make install
make lint
make format
make test
```

## Requirements

- Python 3.13+
- Typer
- Rich
- psutil

## Contributing

Contributions are welcome.

1. fork the repository
2. create a feature branch
3. make your changes
4. run the relevant checks
5. open a pull request

## License

This project does not currently declare a license in the repository metadata. If you plan to distribute or publish it more broadly, consider adding an open-source license such as MIT or Apache 2.0.

## Summary

OptForge is a practical toolkit for developers working on local environments, especially when they need fast answers about ports, runtime configuration, storage health, and Python project clutter.
