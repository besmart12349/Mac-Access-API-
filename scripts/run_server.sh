#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

exec python3 -m uvicorn mac_access_api.main:app --host "${MAC_ACCESS_HOST:-0.0.0.0}" --port "${MAC_ACCESS_PORT:-8787}"
