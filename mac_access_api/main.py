from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.responses import StreamingResponse

from mac_access_api.config import settings
from mac_access_api.models import (
    AppleScriptRequest,
    ClipboardRequest,
    DirListRequest,
    FileReadRequest,
    FileWriteRequest,
    OpenRequest,
    ProcessSignalRequest,
    ScreenCaptureRequest,
    TerminalRequest,
    VolumeRequest,
)
from mac_access_api.scheduler import enforce_schedule
from mac_access_api.security import verify_api_key
from mac_access_api import services

app = FastAPI(title="Mac Access API", version="0.2.0")


@app.middleware("http")
async def guardrails(request, call_next):
    if request.url.path != "/api/v1/kill/clear":
        services.check_kill_switch()
    enforce_schedule()
    return await call_next(request)


@app.get("/health", dependencies=[Depends(verify_api_key)])
def health() -> dict:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schedule": {
            "enabled": settings.schedule_enabled,
            "start_hour": settings.schedule_start_hour,
            "end_hour": settings.schedule_end_hour,
            "timezone": settings.schedule_timezone,
        },
    }


@app.post("/api/v1/terminal", dependencies=[Depends(verify_api_key)])
def terminal(payload: TerminalRequest) -> dict:
    return services.run_shell(payload.command)


@app.post("/api/v1/applescript", dependencies=[Depends(verify_api_key)])
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


@app.post("/api/v1/mac/lock", dependencies=[Depends(verify_api_key)])
def mac_lock() -> dict:
    return services.lock_screen()


@app.post("/api/v1/mac/sleep", dependencies=[Depends(verify_api_key)])
def mac_sleep() -> dict:
    return services.sleep_display()


@app.post("/api/v1/mac/logout", dependencies=[Depends(verify_api_key)])
def mac_logout() -> dict:
    return services.logout_user()


@app.post("/api/v1/mac/restart", dependencies=[Depends(verify_api_key)])
def mac_restart() -> dict:
    return services.restart()


@app.post("/api/v1/mac/shutdown", dependencies=[Depends(verify_api_key)])
def mac_shutdown() -> dict:
    return services.shutdown()


@app.post("/api/v1/mac/volume", dependencies=[Depends(verify_api_key)])
def mac_set_volume(payload: VolumeRequest) -> dict:
    return services.set_volume(payload.level)


@app.get("/api/v1/mac/volume", dependencies=[Depends(verify_api_key)])
def mac_get_volume() -> dict:
    return services.get_volume()


@app.post("/api/v1/mac/mute", dependencies=[Depends(verify_api_key)])
def mac_mute() -> dict:
    return services.mute_audio()


@app.post("/api/v1/mac/unmute", dependencies=[Depends(verify_api_key)])
def mac_unmute() -> dict:
    return services.unmute_audio()


@app.post("/api/v1/mac/open", dependencies=[Depends(verify_api_key)])
def mac_open(payload: OpenRequest) -> dict:
    return services.open_target(payload.target)


@app.get("/api/v1/mac/processes", dependencies=[Depends(verify_api_key)])
def mac_processes() -> dict:
    return services.list_processes()


@app.post("/api/v1/mac/process/signal", dependencies=[Depends(verify_api_key)])
def mac_signal_process(payload: ProcessSignalRequest) -> dict:
    return services.signal_process(payload.pid, payload.signal)


@app.post("/api/v1/mac/screenshot", dependencies=[Depends(verify_api_key)])
def mac_screenshot(payload: ScreenCaptureRequest) -> dict:
    return services.take_screenshot(payload.path)


@app.get("/api/v1/mac/clipboard", dependencies=[Depends(verify_api_key)])
def mac_clipboard_get() -> dict:
    return services.get_clipboard()


@app.post("/api/v1/mac/clipboard", dependencies=[Depends(verify_api_key)])
def mac_clipboard_set(payload: ClipboardRequest) -> dict:
    return services.set_clipboard(payload.content)


@app.post("/api/v1/kill", dependencies=[Depends(verify_api_key)])
def kill() -> dict:
    return services.trigger_kill_switch()


@app.post("/api/v1/kill/clear", dependencies=[Depends(verify_api_key)])
def clear_kill() -> dict:
    return services.clear_kill_switch()


async def _mcp_event_stream() -> AsyncGenerator[bytes, None]:
    # Minimal streamable HTTP endpoint aligned with MCP-over-SSE style transports.
    while True:
        payload = {
            "type": "mcp_heartbeat",
            "service": "mac-access-api",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capabilities": [
                "terminal",
                "applescript",
                "files",
                "mac_control",
                "kill_switch",
                "clipboard",
                "process_signals",
                "screenshots",
            ],
        }
        yield f"event: message\ndata: {payload}\n\n".encode("utf-8")
        import asyncio

        await asyncio.sleep(5)


@app.get("/mcp/stream", dependencies=[Depends(verify_api_key)])
def mcp_stream() -> StreamingResponse:
    return StreamingResponse(_mcp_event_stream(), media_type="text/event-stream")


@app.get("/api/v1/remote-options", dependencies=[Depends(verify_api_key)])
def remote_options() -> dict:
    return {
        "recommended": [
            {
                "name": "Tailscale",
                "purpose": "Zero-trust private mesh access across networks",
            },
            {
                "name": "Cloudflare Tunnel",
                "purpose": "Public URL with mTLS/WAF and no inbound port exposure",
            },
            {
                "name": "WireGuard + reverse proxy",
                "purpose": "Self-hosted encrypted remote access",
            },
            {
                "name": "SSH reverse tunnel",
                "purpose": "Lightweight fallback path when VPN agents are unavailable",
            },
        ],
        "notes": "Keep API key secret; add mTLS or IP allow-listing in front of this API for production.",
    }
