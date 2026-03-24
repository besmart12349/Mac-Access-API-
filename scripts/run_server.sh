#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -d "$ROOT_DIR/.venv" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
else
  echo "Missing .env. Run ./scripts/bootstrap.sh first."
  exit 1
fi

if [[ -z "${MAC_ACCESS_API_KEY:-}" ]]; then
  echo "MAC_ACCESS_API_KEY is not set. Run ./scripts/bootstrap.sh first."
  exit 1
fi

# uvicorn availability check (common typo: 'unicorn')
if ! python - <<'PY' >/dev/null 2>&1
import importlib.util
raise SystemExit(0 if importlib.util.find_spec("uvicorn") else 1)
PY
then
  echo "Missing dependency: uvicorn. Run ./scripts/bootstrap.sh (or pip install -e '.[dev]')."
  exit 1
fi

exec python -m uvicorn mac_access_api.main:app --host "${MAC_ACCESS_HOST:-0.0.0.0}" --port "${MAC_ACCESS_PORT:-8787}"
