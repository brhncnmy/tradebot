#!/usr/bin/env bash
set -euo pipefail

# Simple Phase 1 release orchestrator:
# - Usage: scripts/release_phase1.sh <NEW_VERSION>
# - Example: scripts/release_phase1.sh 0.1.1

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <NEW_VERSION> (e.g. 0.1.1)" >&2
  exit 1
fi

NEW_VERSION="$1"

# Resolve repo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VERSION_FILE="${ROOT_DIR}/VERSION"

echo "[release_phase1] Setting VERSION to ${NEW_VERSION}..."
echo "${NEW_VERSION}" > "${VERSION_FILE}"

# Namespace and tag for this release
export TB_DOCKER_NAMESPACE="${TB_DOCKER_NAMESPACE:-burhancanmaya}"
export TRADEBOT_TAG="${TRADEBOT_TAG:-v${NEW_VERSION}}"

echo "[release_phase1] Using TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}"
echo "[release_phase1] Using TRADEBOT_TAG=${TRADEBOT_TAG}"

# 1) Run tests inside Docker
echo "[release_phase1] Running tests in Docker..."
chmod +x scripts/test_phase1_in_docker.sh
scripts/test_phase1_in_docker.sh

# 2) Build and push images (this will also update .env)
echo "[release_phase1] Building and pushing images..."
chmod +x scripts/build_and_push_docker.sh
scripts/build_and_push_docker.sh

# 3) Git add / commit / push
echo "[release_phase1] Committing and pushing changes to GitHub..."
git status
git add .
git commit -m "Release v${NEW_VERSION} (Phase 1 TradingView pipeline)"
git push origin main

echo "[release_phase1] Release v${NEW_VERSION} completed."
echo "[release_phase1] Server deploy hint: run scripts/deploy_phase1.sh on the server."





