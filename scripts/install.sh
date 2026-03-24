#!/usr/bin/env bash
# Mac Access API — One-shot installer
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

echo "═══════════════════════════════════════"
echo "  Mac Access API — Installer v0.2.0"
echo "═══════════════════════════════════════"

# 1. Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.11+ first."
  exit 1
fi
PY_VERSION=$(python3 -c "import sys; print(sys.version_info >= (3,11))")
if [[ "$PY_VERSION" != "True" ]]; then
  echo "ERROR: Python 3.11+ required."
  exit 1
fi

# 2. Create venv if not present
if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  echo "→ Creating virtual environment..."
  python3 -m venv "$ROOT_DIR/.venv"
fi
source "$ROOT_DIR/.venv/bin/activate"

# 3. Install dependencies
echo "→ Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"

# 4. Set up .env
if [[ ! -f "$ROOT_DIR/.env" ]]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  GENERATED_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  sed -i '' "s/change-me-now/$GENERATED_KEY/" "$ROOT_DIR/.env"
  echo "→ Generated new API key and saved to .env"
  echo "  API Key: $GENERATED_KEY"
  echo "  ⚠️  Save this key — it will not be shown again."
else
  echo "→ .env already exists, skipping key generation."
fi

# 5. Install LaunchAgent (optional)
read -r -p "Install as LaunchAgent (auto-start on login)? [y/N] " INSTALL_LAUNCH
if [[ "$INSTALL_LAUNCH" =~ ^[Yy]$ ]]; then
  bash "$ROOT_DIR/scripts/install_launchd.sh"
fi

echo ""
echo "✅ Installation complete!"
echo "   Start manually:  bash scripts/run_server.sh"
echo "   Health check:    curl http://127.0.0.1:8787/health"
echo "   API Docs:        http://127.0.0.1:8787/docs"
