# OptForge

Small developer CLI tools for inspecting listening ports, checking environment variables, monitoring disk usage, cleaning Python cache artifacts, controlling output volume, and clearing Windows toast notifications. Most tools are cross-platform; `killNotif` is Windows-only.

Built with Python, Typer, and Rich.

## Overview

OptForge is a lightweight command-line toolkit for developers who want fast answers about the local runtime environment.

It helps you:

- inspect active TCP listeners and identify the owning process
- check whether a port is free or already in use
- test a host/port connection from the terminal
- review environment variables and runtime context
- monitor disk space and storage pressure
- remove stale Python cache artifacts from local projects, without scanning `venv` or `.venv`
- get, set, mute, and adjust the default output volume
- clear Windows toast notifications, optionally for a single app (Windows 10/11 only)

## Why use OptForge?

Whether you're starting a local service, troubleshooting an app crash, checking for port collisions, or cleaning up a messy Python workspace, OptForge gives you quick terminal-based tools without opening a full IDE or browser.

Most tools are designed to be simple, fast, and cross-platform; `killNotif` is Windows-only.

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

### Volume control

- read and set the default output volume
- increase or decrease the volume by a custom step
- set 100% or 0% instantly
- mute, unmute, or toggle mute
- emit JSON or stay quiet for scripting
- works on Windows, macOS, and Linux

### Python cache cleanup

- remove `__pycache__` directories and stale Python bytecode files
- skip virtual environments (`venv` and `.venv`) instead of scanning them
- help keep workspaces clean without walking dependency trees

### Windows notification cleanup (Windows only)

- clear all toast notifications from the Windows Action Center
- clear notifications from a single app by AUMID
- emit JSON or stay quiet for scripting
- requires Windows 10/11 and Windows PowerShell 5.1+
- not available on macOS or Linux; the command exits with code `3` there

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
pycache-clean --help
vol --help
killNotif --help   # Windows 10/11 only
```

## Platform support

| Tool | Windows | macOS | Linux |
| --- | --- | --- | --- |
| `portcheck`, `envcheck`, `diskcheck`, `pycache-clean` | Yes | Yes | Yes |
| `vol` | Yes | Yes | Yes |
| `killNotif` | Windows 10/11 only | No | No |

`vol` uses the system mixer: Core Audio on Windows, `osascript` on macOS, and `pactl`/`wpctl`/`amixer` on Linux.

`killNotif` relies on the Windows Runtime toast notification APIs and Windows PowerShell 5.1, so it cannot run on macOS or Linux. The CLI reports a clear error and exits with code `3` instead of failing with a traceback.

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

### Control output volume

```bash
vol get
vol status
vol on 50
vol up 10
vol down 10
vol full
vol none
vol mute
vol unmute
vol toggle
```

`vol on <PERCENT>` sets an absolute level, while `vol up` and `vol down` change it relative to the current level (default step: `5`). Setting a level above `0` also unmutes the output.

Use `--json` for machine-readable output and `--quiet` to suppress output:

```bash
vol get --json
vol on 35 --json
vol toggle --json
```

### Clean Python cache files

`pycache-clean` searches a project for `__pycache__` directories and deletes them. Folders named `venv` or `.venv` are ignored so virtualenv bytecode is left alone and the scan stays fast. The legacy `pycacheClean` alias is also installed.

```bash
pycache-clean --dry-run
pycache-clean --recursive
pycache-clean --max-depth 2
```

### Clear Windows notifications

`killNotif` clears toast notifications from the Windows Action Center. It requires Windows 10/11 and Windows PowerShell 5.1+; it does not work on macOS or Linux.

```powershell
killNotif
killNotif --aumid "Microsoft.WindowsStore_8wekyb3d8bbwe!App"
killNotif --json
killNotif --quiet
```

Use `--aumid` to target one sender. `--json` prints `{"aumid": ..., "cleared": ...}`, and `--quiet` suppresses output. The command exits `0` on success, including when there was nothing to clear, and `3` when it cannot run.

## Project structure

```text
OptForge/
├── src/
│   └── optforge/
│       ├── core/
│       ├── diskcheck/
│       ├── envcheck/
│       ├── killNotif/
│       ├── portcheck/
│       ├── pycacheclean/
│       └── volume/
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
- pycaw for `vol` on Windows (installed automatically)
- `pactl`, `wpctl`, or `amixer` for `vol` on Linux
- Windows 10/11 and Windows PowerShell 5.1+ for `killNotif`

All other commands work on Windows, macOS, and Linux.

## Contributing

Contributions are welcome.

1. fork the repository
2. create a feature branch
3. make your changes
4. run the relevant checks
5. open a pull request

## License

MIT. See [LICENSE](LICENSE).

## Summary

OptForge is a practical toolkit for developers working on local environments, especially when they need fast answers about ports, runtime configuration, storage health, output volume, Python project clutter, and Windows notification noise.
