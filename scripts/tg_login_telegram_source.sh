#!/usr/bin/env bash
set -euo pipefail

# Interactive Telegram login helper for telegram-source service
# Usage: scripts/tg_login_telegram_source.sh [ACCOUNT_ID]
# Example: scripts/tg_login_telegram_source.sh ta01

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

echo "[tg-login] Starting interactive Telegram login for account: ${ACCOUNT_ID}"
echo "[tg-login] Session will be saved to: ${SESSION_DIR}/session_${ACCOUNT_ID}.session"

# Use TRADEBOT_TAG if explicitly set, otherwise default to latest fix tag
# This allows override: TRADEBOT_TAG=xxx ./scripts/tg_login_telegram_source.sh ta01
if [[ -z "${TRADEBOT_TAG:-}" ]]; then
  TRADEBOT_TAG="vv20251127-telegram-source-v2-fix"
fi

# Export TRADEBOT_TAG so docker compose uses it (overrides .env file)
export TRADEBOT_TAG

# Pull the correct image tag
echo "[tg-login] Pulling telegram-source image with tag: ${TRADEBOT_TAG}"
docker compose pull telegram-source

docker compose run --rm -it \
  -e TELEGRAM_API_ID="${TELEGRAM_API_ID}" \
  -e TELEGRAM_API_HASH="${TELEGRAM_API_HASH}" \
  -e TELEGRAM_ACCOUNT_ID="${TELEGRAM_ACCOUNT_ID}" \
  -e TELEGRAM_SESSION_DIR="${TELEGRAM_SESSION_DIR}" \
  -v "${SESSION_DIR}:${TELEGRAM_SESSION_DIR}" \
  telegram-source \
  python -m app.tg_login

echo "[tg-login] Login completed. Session file: ${SESSION_DIR}/session_${ACCOUNT_ID}.session"

