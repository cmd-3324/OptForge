import subprocess
from pathlib import Path

JOB = Path(__file__).with_name("job.ps1")


def clear_notifications(aumid: str | None = None) -> int:
    """Clear all notifications (or one sender's). Returns senders cleared."""
    if not JOB.exists():
        raise FileNotFoundError(f"helper script missing: {JOB}")

    cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-File", str(JOB),
    ]
    if aumid:
        cmd += ["-Aumid", aumid]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout).strip() or "job.ps1 failed")

    out = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else "0"
    return int(out)