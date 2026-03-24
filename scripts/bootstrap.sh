#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$ROOT_DIR"

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip
pip install -e '.[dev]'

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
fi

if ! grep -q '^MAC_ACCESS_API_KEY=' "$ROOT_DIR/.env"; then
  echo "MAC_ACCESS_API_KEY=$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)" >> "$ROOT_DIR/.env"
fi

if grep -q '^MAC_ACCESS_API_KEY=change-me-now$' "$ROOT_DIR/.env"; then
  NEW_KEY="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"
  sed -i.bak "s#^MAC_ACCESS_API_KEY=change-me-now#MAC_ACCESS_API_KEY=$NEW_KEY#" "$ROOT_DIR/.env"
  rm -f "$ROOT_DIR/.env.bak"
fi

echo "Bootstrap complete."
echo "Next steps:"
echo "  1) source .venv/bin/activate"
echo "  2) ./scripts/run_server.sh"
echo "  3) Optional always-on: ./scripts/install_launchd.sh"
