from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from mac_access_api.config import settings
from mac_access_api.models import (
    AppLaunchRequest,
    AppleScriptRequest,
    ClipboardWriteRequest,
    DirListRequest,
    FileDeleteRequest,
    FileMoveRequest,
    FileReadRequest,
    FileWriteRequest,
    KillSwitchResetRequest,
    NotificationRequest,
    TerminalRequest,
    VolumeRequest,
)
from mac_access_api.scheduler import enforce_schedule
from mac_access_api.security import verify_api_key
from mac_access_api import services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("mac_access_api")

app = FastAPI(
    title="Mac Access API",
    version="0.2.0",
    description="Secure macOS remote control API with MCP streamable HTTP support.",
)


@app.middleware("http")
async def guardrails(request: Request, call_next):
    if request.url.path not in ("/health", "/docs", "/openapi.json", "/redoc"):
        services.check_kill_switch()
        enforce_schedule()
    logger.info("%s %s from %s", request.method, request.url.path,
                request.client.host if request.client else "unknown")
    response = await call_next(request)
    return response


@app.get("/health", summary="Health check — no API key required")
def health() -> dict:
    kill_active = settings.kill_switch_path.exists()
    return {
        "status": "ok",
        "version": "0.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kill_switch_active": kill_active,
        "schedule": {
            "enabled": settings.schedule_enabled,
            "start_hour": settings.schedule_start_hour,
            "end_hour": settings.schedule_end_hour,
            "timezone": settings.schedule_timezone,
        },
    }


@app.post("/api/v1/terminal", dependencies=[Depends(verify_api_key)], summary="Run a shell command")
def terminal(payload: TerminalRequest) -> dict:
    return services.run_shell(payload.command)


@app.post("/api/v1/applescript", dependencies=[Depends(verify_api_key)], summary="Run an AppleScript")
def applescript(payload: AppleScriptRequest) -> dict:
    return services.run_applescript(payload.script)


@app.post("/api/v1/files/read", dependencies=[Depends(verify_api_key)])
def files_read(payload: FileReadRequest) -> dict:
    return services.read_file(payload.path)


@app.post("/api/v1/files/write", dependencies=[Depends(verify_api_key)])
def files_write(payload: FileWriteRequest) -> dict:
    return services.write_file(payload.path, payload.content)


@app.post("/api/v1/files/list", dependencies=[Depends(verify_api_key)])
def files_list(payload: DirListRequest) -> dict:
    return services.list_dir(payload.path)


@app.post("/api/v1/files/delete", dependencies=[Depends(verify_api_key)], summary="Delete a file or directory")
def files_delete(payload: FileDeleteRequest) -> dict:
    return services.delete_file(payload.path)


@app.post("/api/v1/files/move", dependencies=[Depends(verify_api_key)], summary="Move or rename a file/directory")
def files_move(payload: FileMoveRequest) -> dict:
    return services.move_file(payload.src, payload.dst)


@app.post("/api/v1/mac/lock", dependencies=[Depends(verify_api_key)])
def mac_lock() -> dict:
    return services.lock_screen()


@app.post("/api/v1/mac/sleep-display", dependencies=[Depends(verify_api_key)], summary="Sleep display without locking")
def mac_sleep_display() -> dict:
    return services.sleep_display()


@app.post("/api/v1/mac/restart", dependencies=[Depends(verify_api_key)])
def mac_restart() -> dict:
    return services.restart()


@app.post("/api/v1/mac/shutdown", dependencies=[Depends(verify_api_key)])
def mac_shutdown() -> dict:
    return services.shutdown()


@app.get("/api/v1/system/info", dependencies=[Depends(verify_api_key)], summary="System info: hostname, OS, CPU, RAM, disk")
def system_info() -> dict:
    return services.get_system_info()


@app.get("/api/v1/system/processes", dependencies=[Depends(verify_api_key)], summary="List running processes")
def system_processes() -> dict:
    return services.get_running_processes()


@app.get("/api/v1/system/battery", dependencies=[Depends(verify_api_key)], summary="Battery status")
def system_battery() -> dict:
    return services.get_battery_info()


@app.get("/api/v1/system/wifi", dependencies=[Depends(verify_api_key)], summary="Wi-Fi connection info")
def system_wifi() -> dict:
    return services.get_wifi_info()


@app.get("/api/v1/clipboard", dependencies=[Depends(verify_api_key)], summary="Read clipboard")
def clipboard_get() -> dict:
    return services.get_clipboard()


@app.post("/api/v1/clipboard", dependencies=[Depends(verify_api_key)], summary="Write to clipboard")
def clipboard_set(payload: ClipboardWriteRequest) -> dict:
    return services.set_clipboard(payload.text)


@app.get("/api/v1/audio/volume", dependencies=[Depends(verify_api_key)], summary="Get output volume")
def audio_volume_get() -> dict:
    return services.get_volume()


@app.post("/api/v1/audio/volume", dependencies=[Depends(verify_api_key)], summary="Set output volume (0-100)")
def audio_volume_set(payload: VolumeRequest) -> dict:
    return services.set_volume(payload.level)


@app.post("/api/v1/notify", dependencies=[Depends(verify_api_key)], summary="Send macOS notification banner")
def notify(payload: NotificationRequest) -> dict:
    return services.send_notification(payload.title, payload.message, payload.sound)


@app.post("/api/v1/app/launch", dependencies=[Depends(verify_api_key)], summary="Launch app by name")
def app_launch(payload: AppLaunchRequest) -> dict:
    return services.launch_app(payload.app_name)


@app.post("/api/v1/app/quit", dependencies=[Depends(verify_api_key)], summary="Quit app by name")
def app_quit(payload: AppLaunchRequest) -> dict:
    return services.quit_app(payload.app_name)


@app.post("/api/v1/kill", dependencies=[Depends(verify_api_key)], summary="Arm kill switch")
def kill() -> dict:
    return services.trigger_kill_switch()


@app.post("/api/v1/kill/reset", dependencies=[Depends(verify_api_key)], summary="Disarm kill switch")
def kill_reset(payload: KillSwitchResetRequest) -> dict:
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true to reset")
    return services.reset_kill_switch()


async def _mcp_event_stream() -> AsyncGenerator[bytes, None]:
    while True:
        payload = json.dumps({
            "type": "mcp_heartbeat",
            "service": "mac-access-api",
            "version": "0.2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": [
                "terminal", "applescript", "files", "mac_control",
                "kill_switch", "system_info", "clipboard", "audio",
                "notifications", "app_control",
            ],
        })
        yield f"event: message\ndata: {payload}\n\n".encode("utf-8")
        await asyncio.sleep(5)


@app.get("/mcp/stream", dependencies=[Depends(verify_api_key)], summary="MCP-over-SSE heartbeat stream")
def mcp_stream() -> StreamingResponse:
    return StreamingResponse(_mcp_event_stream(), media_type="text/event-stream")


@app.get("/api/v1/remote-options", dependencies=[Depends(verify_api_key)])
def remote_options() -> dict:
    return {
        "recommended": [
            {"name": "Tailscale", "purpose": "Zero-trust private mesh access across networks"},
            {"name": "Cloudflare Tunnel", "purpose": "Public URL with mTLS/WAF and no inbound port exposure"},
            {"name": "WireGuard + reverse proxy", "purpose": "Self-hosted encrypted remote access"},
        ],
        "notes": "Keep API key secret; add mTLS or IP allow-listing in front of this API for production.",
    }
