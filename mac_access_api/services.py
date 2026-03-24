from __future__ import annotations

import os
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from mac_access_api.config import settings


def _ensure_allowed(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not any(str(path).startswith(str(root)) for root in settings.allowed_path_list):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Path '{path}' is outside configured allowed paths",
        )
    return path


def run_shell(command: str) -> dict:
    try:
        proc = subprocess.run(
            ["/bin/bash", "-lc", command],
            capture_output=True,
            text=True,
            timeout=settings.command_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="Command timed out") from exc

    return {
        "command": command,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def run_applescript(script: str) -> dict:
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=settings.command_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=408, detail="AppleScript timed out") from exc

    return {
        "script": script,
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def read_file(path: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is a directory, not a file")

    return {"path": str(resolved), "content": resolved.read_text(encoding="utf-8")}


def write_file(path: str, content: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {"path": str(resolved), "bytes_written": len(content.encode("utf-8"))}


def list_dir(path: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    for child in sorted(resolved.iterdir()):
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else None,
            }
        )
    return {"path": str(resolved), "entries": entries}


def trigger_kill_switch() -> dict:
    settings.kill_switch_path.write_text("KILLED\n", encoding="utf-8")
    return {"kill_switch": str(settings.kill_switch_path), "status": "armed"}


def check_kill_switch() -> None:
    if settings.kill_switch_path.exists():
        raise HTTPException(status_code=423, detail="Kill switch active")


def lock_screen() -> dict:
    command = (
        '/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession '
        '-suspend'
    )
    result = run_shell(command)
    result["action"] = "lock_screen"
    return result


def shutdown() -> dict:
    result = run_shell("sudo shutdown -h now")
    result["action"] = "shutdown"
    return result


def restart() -> dict:
    result = run_shell("sudo shutdown -r now")
    result["action"] = "restart"
    return result
