from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from fastapi import HTTPException, status

from mac_access_api.config import settings


def _ensure_allowed(path: Path) -> Path:
    """Resolve and validate path is within allowed roots. Blocks symlink escapes."""
    resolved = path.expanduser().resolve()
    if not any(str(resolved).startswith(str(root)) for root in settings.allowed_path_list):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Path is outside configured allowed paths",
        )
    return resolved


def _check_command_blocklist(command: str) -> None:
    """Reject commands matching dangerous patterns."""
    lower = command.lower()
    for pattern in settings.command_blocklist_list:
        if pattern.lower() in lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Command blocked by security policy",
            )


def run_shell(command: str) -> dict:
    _check_command_blocklist(command)
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
    size = resolved.stat().st_size
    if size > settings.max_file_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size} bytes). Max is {settings.max_file_bytes} bytes.",
        )
    return {"path": str(resolved), "content": resolved.read_text(encoding="utf-8"), "size": size}


def write_file(path: str, content: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    encoded = content.encode("utf-8")
    if len(encoded) > settings.max_file_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Content too large ({len(encoded)} bytes). Max is {settings.max_file_bytes} bytes.",
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    return {"path": str(resolved), "bytes_written": len(encoded)}


def delete_file(path: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Path not found")
    if resolved.is_dir():
        shutil.rmtree(resolved)
        return {"path": str(resolved), "deleted": "directory"}
    resolved.unlink()
    return {"path": str(resolved), "deleted": "file"}


def move_file(src: str, dst: str) -> dict:
    src_resolved = _ensure_allowed(Path(src))
    dst_resolved = _ensure_allowed(Path(dst))
    if not src_resolved.exists():
        raise HTTPException(status_code=404, detail="Source path not found")
    shutil.move(str(src_resolved), str(dst_resolved))
    return {"src": str(src_resolved), "dst": str(dst_resolved), "status": "moved"}


def list_dir(path: str) -> dict:
    resolved = _ensure_allowed(Path(path))
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    entries = []
    for child in sorted(resolved.iterdir()):
        try:
            is_link = child.is_symlink()
            is_dir = child.is_dir()
            size = child.stat(follow_symlinks=False).st_size if child.is_file() else None
        except OSError:
            continue
        entries.append({
            "name": child.name,
            "path": str(child),
            "is_dir": is_dir,
            "is_symlink": is_link,
            "size": size,
        })
    return {"path": str(resolved), "entries": entries, "count": len(entries)}


def trigger_kill_switch() -> dict:
    settings.kill_switch_path.write_text("KILLED\n", encoding="utf-8")
    return {"kill_switch": str(settings.kill_switch_path), "status": "armed"}


def reset_kill_switch() -> dict:
    if settings.kill_switch_path.exists():
        settings.kill_switch_path.unlink()
        return {"kill_switch": str(settings.kill_switch_path), "status": "disarmed"}
    return {"kill_switch": str(settings.kill_switch_path), "status": "was_not_armed"}


def check_kill_switch() -> None:
    if settings.kill_switch_path.exists():
        raise HTTPException(status_code=423, detail="Kill switch active — POST /api/v1/kill/reset to disarm")


def lock_screen() -> dict:
    result = run_shell(
        '/System/Library/CoreServices/Menu\\ Extras/User.menu/Contents/Resources/CGSession -suspend'
    )
    result["action"] = "lock_screen"
    return result


def sleep_display() -> dict:
    result = run_shell("pmset displaysleepnow")
    result["action"] = "sleep_display"
    return result


def shutdown() -> dict:
    result = run_shell("osascript -e 'tell app \"System Events\" to shut down'")
    result["action"] = "shutdown"
    return result


def restart() -> dict:
    result = run_shell("osascript -e 'tell app \"System Events\" to restart'")
    result["action"] = "restart"
    return result


def get_system_info() -> dict:
    hostname = run_shell("hostname")["stdout"].strip()
    uptime = run_shell("uptime")["stdout"].strip()
    macos_ver = run_shell("sw_vers -productVersion")["stdout"].strip()
    cpu = run_shell("sysctl -n machdep.cpu.brand_string")["stdout"].strip()
    mem = run_shell("sysctl -n hw.memsize")["stdout"].strip()
    disk = run_shell("df -h /")["stdout"].strip()
    return {
        "hostname": hostname,
        "macos_version": macos_ver,
        "cpu": cpu,
        "memory_bytes": int(mem) if mem.isdigit() else mem,
        "uptime": uptime,
        "disk": disk,
    }


def get_running_processes() -> dict:
    result = run_shell("ps aux")
    lines = result["stdout"].strip().splitlines()
    processes = []
    for line in lines[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            processes.append({
                "user": parts[0], "pid": parts[1], "cpu": parts[2],
                "mem": parts[3], "command": parts[10],
            })
    return {"count": len(processes), "processes": processes}


def send_notification(title: str, message: str, sound: bool = True) -> dict:
    sound_str = 'with sound name "default"' if sound else ""
    script = f'display notification "{message}" with title "{title}" {sound_str}'
    return run_applescript(script)


def get_clipboard() -> dict:
    result = run_shell("pbpaste")
    return {"content": result["stdout"]}


def set_clipboard(text: str) -> dict:
    proc = subprocess.run(
        ["pbcopy"],
        input=text,
        capture_output=True,
        text=True,
        timeout=5,
    )
    return {"status": "ok" if proc.returncode == 0 else "error", "bytes": len(text.encode())}


def set_volume(level: int) -> dict:
    script = f"set volume output volume {level}"
    return run_applescript(script)


def get_volume() -> dict:
    script = "output volume of (get volume settings)"
    result = run_applescript(script)
    return {"volume": result["stdout"].strip()}


def launch_app(app_name: str) -> dict:
    script = f'tell application "{app_name}" to activate'
    return run_applescript(script)


def quit_app(app_name: str) -> dict:
    script = f'tell application "{app_name}" to quit'
    return run_applescript(script)


def get_wifi_info() -> dict:
    result = run_shell(
        "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I"
    )
    info: dict = {}
    for line in result["stdout"].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            info[k.strip()] = v.strip()
    return {"wifi": info}


def get_battery_info() -> dict:
    result = run_shell("pmset -g batt")
    return {"battery": result["stdout"].strip()}
