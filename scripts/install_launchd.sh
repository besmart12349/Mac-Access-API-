#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT_DIR/launchd/com.macaccess.api.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.macaccess.api.plist"

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  echo "Missing .env file. Copy .env.example to .env and configure API key first."
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s#/ABSOLUTE/PATH/TO/Mac-Access-API-#$ROOT_DIR#g" "$PLIST_SRC" > "$PLIST_DST"

launchctl unload "$PLIST_DST" >/dev/null 2>&1 || true
launchctl load "$PLIST_DST"

echo "Installed and loaded LaunchAgent: $PLIST_DST"
echo "Use 'launchctl list | grep com.macaccess.api' to verify."
