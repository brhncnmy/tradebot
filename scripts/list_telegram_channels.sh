#!/usr/bin/env bash
set -euo pipefail

# List all Telegram dialogs/channels for a configured account
# Usage: scripts/list_telegram_channels.sh [ACCOUNT_ID]
# Example: scripts/list_telegram_channels.sh ta01

ACCOUNT_ID="${1:-ta01}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export TELEGRAM_ACCOUNT_ID="${ACCOUNT_ID}"
export TELEGRAM_SESSION_DIR="/app/telegram/sessions"

# Ensure required environment variables are set
: "${TELEGRAM_API_ID:?TELEGRAM_API_ID must be set}"
: "${TELEGRAM_API_HASH:?TELEGRAM_API_HASH must be set}"

# Ensure session directory exists on host
SESSION_DIR="${HOME}/tradebot-data/telegram/sessions"
mkdir -p "${SESSION_DIR}"

echo "[list-channels] Listing Telegram dialogs/channels for account: ${ACCOUNT_ID}"
echo "[list-channels] Session file: ${SESSION_DIR}/session_${ACCOUNT_ID}.session"

# Use TRADEBOT_TAG if explicitly set, otherwise default to latest fix tag
# This allows override: TRADEBOT_TAG=xxx ./scripts/list_telegram_channels.sh ta01
if [[ -z "${TRADEBOT_TAG:-}" ]]; then
  export TRADEBOT_TAG="vv20251127-telegram-source-v2-fix"
fi

# Pull the correct image tag
echo "[list-channels] Pulling telegram-source image with tag: ${TRADEBOT_TAG}"
docker compose pull telegram-source

docker compose run --rm \
  -e TELEGRAM_API_ID="${TELEGRAM_API_ID}" \
  -e TELEGRAM_API_HASH="${TELEGRAM_API_HASH}" \
  -e TELEGRAM_ACCOUNT_ID="${TELEGRAM_ACCOUNT_ID}" \
  -e TELEGRAM_SESSION_DIR="${TELEGRAM_SESSION_DIR}" \
  -v "${SESSION_DIR}:${TELEGRAM_SESSION_DIR}" \
  telegram-source \
  python -m app.list_dialogs

