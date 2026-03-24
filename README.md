# Mac Access API (Always-On macOS Control Service)

Secure remote control API for macOS with API key auth, schedule locks, kill switch, MCP stream, and launchd auto-start.

## Fastest setup (2 commands)

```bash
make bootstrap
make dev
```

That will:
- create `.venv`
- install dependencies
- generate `.env` from `.env.example`
- auto-generate a strong API key if still set to `change-me-now`
- start the API on `http://0.0.0.0:8787`

## Always-on setup (auto start after login)

```bash
make install-service
make status
```



## Where to send API messages

Use this base URL for all API calls:

- Local dev: `http://127.0.0.1:8787`
- LAN/remote: `http://<mac-ip-or-domain>:8787`

Include header on every request:

- `X-API-Key: <your key from .env>`

Interactive API docs are available at:

- `GET /docs` (Swagger UI)
- `GET /openapi.json` (OpenAPI spec)

Message-specific endpoints:

- `POST /api/v1/messages/notify` → show a macOS notification
- `POST /api/v1/messages/speak` → speak message audio through the Mac

## Required security baseline

- All endpoints require `X-API-Key`.
- Access windows are controlled by `MAC_ACCESS_SCHEDULE_*`.
- File API is constrained by `MAC_ACCESS_ALLOWED_PATHS`.
- Kill switch blocks all API calls until cleared.

## Core API capabilities

- Terminal, AppleScript, file read/write/list.
- Mac controls: lock, sleep, logout, restart, shutdown.
- Volume set/get, mute/unmute.
- Clipboard get/set.
- Open file/app/URL targets.
- Process list and process signal.
- Screenshot capture to allowed paths.
- Streamable MCP endpoint: `GET /mcp/stream`.
- Remote access recommendations: `GET /api/v1/remote-options`.

## Useful commands

```bash
# Run tests
make test

# Stop launchd service
make stop

# Clear emergency kill switch
make clean-kill
```

## Example requests

```bash
export KEY='<your-api-key>'

curl -s http://127.0.0.1:8787/health -H "X-API-Key: $KEY"

curl -s -X POST http://127.0.0.1:8787/api/v1/terminal \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"command":"whoami"}'

curl -s -X POST http://127.0.0.1:8787/api/v1/mac/volume \
  -H "X-API-Key: $KEY" -H 'Content-Type: application/json' \
  -d '{"level":50}'
```

## Endpoint summary

- `GET /health`
- `POST /api/v1/terminal`
- `POST /api/v1/applescript`
- `POST /api/v1/files/read`
- `POST /api/v1/files/write`
- `POST /api/v1/files/list`
- `POST /api/v1/mac/lock`
- `POST /api/v1/mac/sleep`
- `POST /api/v1/mac/logout`
- `POST /api/v1/mac/restart`
- `POST /api/v1/mac/shutdown`
- `POST /api/v1/mac/volume`
- `GET /api/v1/mac/volume`
- `POST /api/v1/mac/mute`
- `POST /api/v1/mac/unmute`
- `POST /api/v1/mac/open`
- `GET /api/v1/mac/processes`
- `POST /api/v1/mac/process/signal`
- `POST /api/v1/mac/screenshot`
- `GET /api/v1/mac/clipboard`
- `POST /api/v1/mac/clipboard`
- `POST /api/v1/kill`
- `POST /api/v1/kill/clear`
- `GET /mcp/stream`
- `GET /api/v1/remote-options`
