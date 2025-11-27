#!/usr/bin/env bash
set -euo pipefail

# PocketOption bot Phase 2 deployment script (runs on prod server via SSH)
# Usage: scripts/deploy_pocketoption_bot_phase2.sh [VERSION_TAG]
# Example: scripts/deploy_pocketoption_bot_phase2.sh vv20251127-pocketoption-bot-v1

VERSION_TAG="${1:-}"

# Set namespace and tag
export TB_DOCKER_NAMESPACE="${TB_DOCKER_NAMESPACE:-burhancanmaya}"
if [[ -n "${VERSION_TAG}" ]]; then
  export TRADEBOT_TAG="${VERSION_TAG}"
fi

echo "[deploy_pocketoption_bot_phase2] Deploying to prod server..."

# SSH into prod server and run deployment commands
ssh -i ~/.ssh/Btest.pem ubuntu@52.204.179.175 bash << EOF
set -euo pipefail

cd ~/tradebot

# Set namespace and tag from parent environment
export TB_DOCKER_NAMESPACE="${TB_DOCKER_NAMESPACE:-burhancanmaya}"
if [[ -n "${VERSION_TAG}" ]]; then
  export TRADEBOT_TAG="${VERSION_TAG}"
fi

echo "[deploy_pocketoption_bot_phase2] Pulling latest code from main..."
git pull origin main

echo "[deploy_pocketoption_bot_phase2] Pulling pocketoption-bot image..."
docker compose pull pocketoption-bot

echo "[deploy_pocketoption_bot_phase2] Restarting pocketoption-bot service..."
docker compose up -d pocketoption-bot

echo "[deploy_pocketoption_bot_phase2] Done. Current containers:"
docker compose ps pocketoption-bot
EOF

