#!/usr/bin/env bash
set -euo pipefail

# Phase 1 deployment script (to be run on the server)
# Usage: scripts/deploy_phase1.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[deploy_phase1] Pulling latest code from main..."
git pull origin main

echo "[deploy_phase1] Pulling Phase 1 service images..."
docker compose pull tv-listener signal-orchestrator order-gateway

echo "[deploy_phase1] Restarting Phase 1 services..."
docker compose up -d tv-listener signal-orchestrator order-gateway

echo "[deploy_phase1] Done. Current containers:"
docker compose ps

