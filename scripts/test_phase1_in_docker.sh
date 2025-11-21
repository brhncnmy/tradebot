#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[test_phase1_in_docker] Building Phase 1 service images..."
docker compose build tv-listener signal-orchestrator order-gateway

echo "[test_phase1_in_docker] Running pytest inside tv-listener container..."
docker compose run --rm tv-listener pytest

echo "[test_phase1_in_docker] Tests completed successfully inside Docker."

