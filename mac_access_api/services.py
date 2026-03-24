from __future__ import annotations

import os
import signal
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


def clear_kill_switch() -> dict:
    if settings.kill_switch_path.exists():
        settings.kill_switch_path.unlink()
    return {"kill_switch": str(settings.kill_switch_path), "status": "cleared"}


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


def sleep_display() -> dict:
    result = run_applescript('tell application "System Events" to sleep')
    result["action"] = "sleep"
    return result


def shutdown() -> dict:
    result = run_shell("sudo shutdown -h now")
    result["action"] = "shutdown"
    return result


def restart() -> dict:
    result = run_shell("sudo shutdown -r now")
    result["action"] = "restart"
    return result


def logout_user() -> dict:
    result = run_applescript('tell application "System Events" to log out')
    result["action"] = "logout"
    return result


def set_volume(level: int) -> dict:
    result = run_applescript(f"set volume output volume {level}")
    result["action"] = "set_volume"
    result["level"] = level
    return result


def mute_audio() -> dict:
    result = run_applescript("set volume with output muted")
    result["action"] = "mute"
    return result


def unmute_audio() -> dict:
    result = run_applescript("set volume without output muted")
    result["action"] = "unmute"
    return result


def get_volume() -> dict:
    query = "output volume of (get volume settings)"
    result = run_applescript(f"return {query}")
    result["action"] = "get_volume"
    try:
        result["level"] = int(result["stdout"].strip())
    except ValueError:
        result["level"] = None
    return result


def set_clipboard(content: str) -> dict:
    escaped = content.replace('"', '\\"')
    result = run_applescript(f'set the clipboard to "{escaped}"')
    result["action"] = "set_clipboard"
    return result


def get_clipboard() -> dict:
    result = run_applescript("the clipboard")
    result["action"] = "get_clipboard"
    return result


def open_target(target: str) -> dict:
    result = run_shell(f'open "{target}"')
    result["action"] = "open"
    result["target"] = target
    return result


def list_processes() -> dict:
    result = run_shell("ps -ax -o pid=,comm=")
    processes = []
    for line in result["stdout"].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_str, _, command = stripped.partition(" ")
        if pid_str.isdigit():
            processes.append({"pid": int(pid_str), "command": command.strip()})
    return {"count": len(processes), "processes": processes}


def signal_process(pid: int, signal_name: str) -> dict:
    signal_name = signal_name.upper()
    signal_attr = f"SIG{signal_name}"
    if not hasattr(signal, signal_attr):
        raise HTTPException(status_code=400, detail=f"Unsupported signal '{signal_name}'")

    try:
        os.kill(pid, getattr(signal, signal_attr))
    except ProcessLookupError as exc:
        raise HTTPException(status_code=404, detail=f"PID {pid} not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=f"Permission denied for PID {pid}") from exc

    return {"pid": pid, "signal": signal_name, "status": "sent"}


def take_screenshot(path: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    resolved.parent.mkdir(parents=True, exist_ok=True)
    result = run_shell(f'screencapture -x "{resolved}"')
    result["action"] = "screenshot"
    result["path"] = str(resolved)
    return result
