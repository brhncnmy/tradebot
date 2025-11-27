#!/usr/bin/env bash
set -euo pipefail

# PocketOption Phase 2 release orchestrator:
# - Usage: scripts/release_pocketoption_phase2.sh <VERSION_TAG>
# - Example: scripts/release_pocketoption_phase2.sh vv20240115-1200-pocket-tg-source

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <VERSION_TAG> (e.g. vv20240115-1200-pocket-tg-source)" >&2
  exit 1
fi

VERSION_TAG="$1"

# Resolve repo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Namespace and tag for this release
export TB_DOCKER_NAMESPACE="${TB_DOCKER_NAMESPACE:-burhancanmaya}"
export TRADEBOT_TAG="${VERSION_TAG}"

echo "[release_pocketoption_phase2] Using TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}"
echo "[release_pocketoption_phase2] Using TRADEBOT_TAG=${TRADEBOT_TAG}"

# 1) Run tests
echo "[release_pocketoption_phase2] Running tests..."
export PYTHONPATH="${ROOT_DIR}"
pytest telegram/telegram-source/tests -q

# 2) Build and push telegram-source image using buildx
IMAGE_BASE="${TB_DOCKER_NAMESPACE}/telegram-source"
IMAGE_TAG="${IMAGE_BASE}:${TRADEBOT_TAG}"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD)"
else
  GIT_SHA="nogit"
fi

IMAGE_TAG_SHA="${IMAGE_BASE}:${TRADEBOT_TAG}-${GIT_SHA}"

echo "[release_pocketoption_phase2] Building and pushing ${IMAGE_TAG} and ${IMAGE_TAG_SHA} for linux/amd64..."

# Ensure a buildx builder is available
if ! docker buildx ls | grep -q 'tradebot-builder'; then
  docker buildx create --name tradebot-builder --use >/dev/null 2>&1 || docker buildx use default >/dev/null 2>&1 || true
else
  docker buildx use tradebot-builder >/dev/null 2>&1 || true
fi

docker buildx build \
  --platform linux/amd64 \
  -f docker/telegram-source.Dockerfile \
  -t "${IMAGE_TAG}" \
  -t "${IMAGE_TAG_SHA}" \
  --push \
  "${ROOT_DIR}"

echo "[release_pocketoption_phase2] Release ${VERSION_TAG} completed."
echo "[release_pocketoption_phase2] Server deploy hint: run scripts/deploy_pocketoption_phase2.sh ${VERSION_TAG} on the server."

