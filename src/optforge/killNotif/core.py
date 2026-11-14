"""Run the bundled PowerShell helper that clears Windows toast history."""

from __future__ import annotations

import subprocess
from pathlib import Path

JOB = Path(__file__).with_name("job.ps1")
POWERSHELL_TIMEOUT_SECONDS = 30


def clear_notifications(aumid: str | None = None) -> int:
    """Clear all notifications (or one sender's). Returns senders cleared."""
    if not JOB.exists():
        raise FileNotFoundError(f"helper script missing: {JOB}")

    cmd = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "RemoteSigned",
        "-File",
        str(JOB),
    ]
    if aumid:
        cmd += ["-Aumid", aumid]

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=POWERSHELL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"PowerShell timed out after {POWERSHELL_TIMEOUT_SECONDS}s.") from exc

    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout).strip() or "job.ps1 failed")

    out = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else "0"
    return int(out)
