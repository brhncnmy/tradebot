#!/usr/bin/env bash
set -euo pipefail

# Debug tool to parse the last 10 messages from PocketOption channel
# Usage: scripts/debug_pocketoption_recent.sh [ACCOUNT_ID]
# Example: scripts/debug_pocketoption_recent.sh ta01

ACCOUNT_ID="${1:-ta01}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export TELEGRAM_ACCOUNT_ID="${ACCOUNT_ID}"
export TELEGRAM_SESSION_DIR="/app/telegram/sessions"

# Ensure required environment variables are set
: "${TELEGRAM_API_ID:?TELEGRAM_API_ID must be set}"
: "${TELEGRAM_API_HASH:?TELEGRAM_API_HASH must be set}"
: "${TELEGRAM_POCKETOPTION_CHANNEL_ID:?TELEGRAM_POCKETOPTION_CHANNEL_ID must be set}"

# Ensure session directory exists on host
SESSION_DIR="${HOME}/tradebot-data/telegram/sessions"
mkdir -p "${SESSION_DIR}"

# Use TRADEBOT_TAG if explicitly set via command line, otherwise default to latest fix tag
# Note: We unset first to override any value from .env file
if [[ -z "${TRADEBOT_TAG:-}" ]] || [[ "${TRADEBOT_TAG}" == "vv20251126-2146-85b1b92" ]]; then
  unset TRADEBOT_TAG
  export TRADEBOT_TAG="vv20251127-telegram-source-v4-fix2"
else
  export TRADEBOT_TAG
fi

echo "[debug-recent] Parsing last 10 messages from PocketOption channel for account: ${ACCOUNT_ID}"
echo "[debug-recent] Channel ID: ${TELEGRAM_POCKETOPTION_CHANNEL_ID}"
echo "[debug-recent] Session file: ${SESSION_DIR}/session_${ACCOUNT_ID}.session"

# Pull the correct image tag
echo "[debug-recent] Pulling telegram-source image with tag: ${TRADEBOT_TAG}"
docker compose pull telegram-source

docker compose run --rm \
  -e TELEGRAM_API_ID="${TELEGRAM_API_ID}" \
  -e TELEGRAM_API_HASH="${TELEGRAM_API_HASH}" \
  -e TELEGRAM_ACCOUNT_ID="${TELEGRAM_ACCOUNT_ID}" \
  -e TELEGRAM_POCKETOPTION_CHANNEL_ID="${TELEGRAM_POCKETOPTION_CHANNEL_ID}" \
  -e TELEGRAM_SESSION_DIR="${TELEGRAM_SESSION_DIR}" \
  -v "${SESSION_DIR}:${TELEGRAM_SESSION_DIR}" \
  telegram-source \
  python -m app.debug_recent

