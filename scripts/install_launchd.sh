#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT_DIR/launchd/com.macaccess.api.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.macaccess.api.plist"

if [[ ! -f "$PLIST_SRC" ]]; then
  echo "Missing launchd template: $PLIST_SRC"
  exit 1
fi

if [[ ! -x "$ROOT_DIR/scripts/run_server.sh" ]]; then
  echo "Missing run script: $ROOT_DIR/scripts/run_server.sh"
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "Missing .env file. Running bootstrap to create it..."
  "$ROOT_DIR/scripts/bootstrap.sh"
fi

mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s#/ABSOLUTE/PATH/TO/Mac-Access-API-#$ROOT_DIR#g" "$PLIST_SRC" > "$PLIST_DST"

launchctl bootout "gui/$(id -u)"/com.macaccess.api >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)"/com.macaccess.api
launchctl kickstart -k "gui/$(id -u)"/com.macaccess.api

echo "Installed and started LaunchAgent: $PLIST_DST"
echo "Use 'launchctl print gui/$(id -u)/com.macaccess.api' to inspect status."
