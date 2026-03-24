# Mac Access API (Always-On macOS Control Service)

A production-ready FastAPI service intended to run continuously on macOS (via `launchd`) and expose secure remote control capabilities:

- Terminal command execution API.
- AppleScript execution API.
- File read/write/list APIs with configurable allowed path boundaries.
- Mac control APIs (lock/restart/shutdown).
- Dedicated kill-switch endpoint.
- Customizable schedule-based access control.
- Mandatory API key auth.
- MCP streamable HTTP endpoint (`/mcp/stream`) for heartbeat/capability streaming.
- Additional external/remote connectivity options surfaced by API (`/api/v1/remote-options`).

## Security model (baseline)

This app enforces:

1. `X-API-Key` header on every endpoint.
2. Time-based access windows (`MAC_ACCESS_SCHEDULE_*`).
3. File-system boundary restrictions (`MAC_ACCESS_ALLOWED_PATHS`).
4. Kill switch file (`MAC_ACCESS_KILL_SWITCH_FILE`) that instantly blocks all calls.

Recommended hardening for Internet exposure:

- Put behind Tailscale, Cloudflare Tunnel, or WireGuard.
- Add mTLS/reverse proxy auth and IP allow-listing.
- Keep service under least-privileged user.
- Rotate API keys and monitor logs.

## 1) Install

```bash
cd /path/to/Mac-Access-API-
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# edit .env and set MAC_ACCESS_API_KEY
```

## 2) Run manually

```bash
source .venv/bin/activate
./scripts/run_server.sh
```

## 3) Run always-on at boot/login (launchd)

```bash
./scripts/install_launchd.sh
launchctl list | grep com.macaccess.api
```

This installs `~/Library/LaunchAgents/com.macaccess.api.plist` with `RunAtLoad` + `KeepAlive`.

## 4) API examples

Set key:

```bash
export KEY='your-long-random-key'
```

Health:

```bash
curl -s http://127.0.0.1:8787/health -H "X-API-Key: $KEY"
```

Terminal:

```bash
curl -s http://127.0.0.1:8787/api/v1/terminal \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"command":"whoami"}'
```

AppleScript:

```bash
curl -s http://127.0.0.1:8787/api/v1/applescript \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"script":"return short user name of (system info)"}'
```

List files:

```bash
curl -s http://127.0.0.1:8787/api/v1/files/list \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"path":"/tmp"}'
```

MCP streamable endpoint:

```bash
curl -N http://127.0.0.1:8787/mcp/stream -H "X-API-Key: $KEY"
```

Kill switch:

```bash
curl -s -X POST http://127.0.0.1:8787/api/v1/kill -H "X-API-Key: $KEY"
```

Clear kill switch locally:

```bash
rm -f ~/.mac_access_api.kill
```

## Endpoint summary

- `GET /health`
- `POST /api/v1/terminal`
- `POST /api/v1/applescript`
- `POST /api/v1/files/read`
- `POST /api/v1/files/write`
- `POST /api/v1/files/list`
- `POST /api/v1/mac/lock`
- `POST /api/v1/mac/restart`
- `POST /api/v1/mac/shutdown`
- `POST /api/v1/kill`
- `GET /mcp/stream`
- `GET /api/v1/remote-options`

## Important permissions

For Mac control and AppleScript features, ensure the host account has appropriate macOS Privacy & Security permissions (Accessibility / Automation / Full Disk Access, as required by your use case).
