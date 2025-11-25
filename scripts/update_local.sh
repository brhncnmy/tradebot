#!/usr/bin/env bash
set -euo pipefail

# Update local script: automatically handles Docker image build/push and git commit/push
# Usage: scripts/update_local.sh [COMMIT_MESSAGE]
#
# If VERSION file changed or release is needed, it will:
# - Build and push Docker images using the current VERSION
# - Update .env file
# - Commit and push all changes
#
# If only code changes exist (no VERSION change), it will:
# - Commit and push code changes only

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMMIT_MESSAGE="${1:-Update local changes}"

# Check if VERSION file exists
if [[ ! -f VERSION ]]; then
  echo "[update_local] VERSION file not found. Creating with 0.1.0..."
  echo "0.1.0" > VERSION
fi

CURRENT_VERSION="$(cat VERSION | tr -d '[:space:]')"

# Check git status
GIT_STATUS="$(git status --porcelain)"
HAS_CHANGES=false
VERSION_CHANGED=false

if [[ -n "$GIT_STATUS" ]]; then
  HAS_CHANGES=true
  
  # Check if VERSION file is modified
  if echo "$GIT_STATUS" | grep -q "^ M VERSION\|^M  VERSION\|^MM VERSION"; then
    VERSION_CHANGED=true
  fi
fi

# If VERSION changed or we need a release, run full release process
if [[ "$VERSION_CHANGED" == "true" ]]; then
  echo "[update_local] VERSION file changed. Running full release process..."
  echo "[update_local] Current VERSION: ${CURRENT_VERSION}"
  
  # Set namespace (default to burhancanmaya)
  export TB_DOCKER_NAMESPACE="${TB_DOCKER_NAMESPACE:-burhancanmaya}"
  export TRADEBOT_TAG="${TRADEBOT_TAG:-v${CURRENT_VERSION}}"
  
  echo "[update_local] Using TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}"
  echo "[update_local] Using TRADEBOT_TAG=${TRADEBOT_TAG}"
  
  # Run tests
  echo "[update_local] Running tests in Docker..."
  chmod +x scripts/test_phase1_in_docker.sh
  scripts/test_phase1_in_docker.sh
  
  # Build and push images (this will also update .env)
  echo "[update_local] Building and pushing images..."
  chmod +x scripts/build_and_push_docker.sh
  scripts/build_and_push_docker.sh
  
  # Commit and push
  echo "[update_local] Committing and pushing changes..."
  git add .
  git commit -m "Release v${CURRENT_VERSION} (Phase 1 TradingView pipeline)"
  git push origin main
  
  echo "[update_local] Release v${CURRENT_VERSION} completed."
  echo "[update_local] Server deploy hint: run scripts/deploy_phase1.sh on the server."
  
elif [[ "$HAS_CHANGES" == "true" ]]; then
  # Only code changes, no VERSION change - just commit and push
  echo "[update_local] Only code changes detected (no VERSION change). Committing and pushing..."
  git add .
  git commit -m "${COMMIT_MESSAGE}"
  git push origin main
  
  echo "[update_local] Changes committed and pushed."
  
else
  echo "[update_local] No changes detected. Nothing to commit."
  exit 0
fi



