#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Ensure a buildx builder is available
if ! docker buildx ls | grep -q 'tradebot-builder'; then
  docker buildx create --name tradebot-builder --use >/dev/null 2>&1 || docker buildx use default >/dev/null 2>&1 || true
else
  docker buildx use tradebot-builder >/dev/null 2>&1 || true
fi

if [[ ! -f VERSION ]]; then
  echo "VERSION file not found in repo root" >&2
  exit 1
fi

VERSION="$(cat VERSION | tr -d '[:space:]')"
if [[ -z "$VERSION" ]]; then
  echo "VERSION file is empty" >&2
  exit 1
fi

BASE_TAG="v${VERSION}"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_SHA="$(git rev-parse --short HEAD)"
else
  GIT_SHA="nogit"
fi

TAG="${TRADEBOT_TAG:-${BASE_TAG}}"

: "${TB_DOCKER_NAMESPACE:?TB_DOCKER_NAMESPACE must be set (e.g. Docker Hub username or organization)}"

echo "Using namespace: ${TB_DOCKER_NAMESPACE}"
echo "Using tag: ${TAG} (base: ${BASE_TAG}, git: ${GIT_SHA})"

# Helper function to update .env file (called only after successful build/push)
# Only updates TRADEBOT_TAG in-place, preserving all other lines
update_env_file() {
  local env_file="${ROOT_DIR}/.env"
  echo "Updating ${env_file} with TB_DOCKER_NAMESPACE and TRADEBOT_TAG..."

  # If .env does not exist, create it
  if [[ ! -f "${env_file}" ]]; then
    {
      echo "TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}"
      echo "TRADEBOT_TAG=${TAG}"
    } > "${env_file}"
    echo "Created ${env_file} with namespace=${TB_DOCKER_NAMESPACE} and tag=${TAG}"
    return 0
  fi

  # Update TRADEBOT_TAG line in-place if it exists, otherwise append
  if grep -q '^TRADEBOT_TAG=' "${env_file}"; then
    # Replace existing TRADEBOT_TAG line
    if [[ "$(uname)" == "Darwin" ]]; then
      # macOS sed requires -i '' for in-place editing
      sed -i '' "s|^TRADEBOT_TAG=.*|TRADEBOT_TAG=${TAG}|" "${env_file}"
    else
      # Linux sed
      sed -i "s|^TRADEBOT_TAG=.*|TRADEBOT_TAG=${TAG}|" "${env_file}"
    fi
  else
    # Append TRADEBOT_TAG if it doesn't exist
    echo "TRADEBOT_TAG=${TAG}" >> "${env_file}"
  fi

  # Update TB_DOCKER_NAMESPACE line in-place if it exists, otherwise append
  if grep -q '^TB_DOCKER_NAMESPACE=' "${env_file}"; then
    # Replace existing TB_DOCKER_NAMESPACE line
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^TB_DOCKER_NAMESPACE=.*|TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}|" "${env_file}"
    else
      sed -i "s|^TB_DOCKER_NAMESPACE=.*|TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}|" "${env_file}"
    fi
  else
    # Append TB_DOCKER_NAMESPACE if it doesn't exist
    echo "TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}" >> "${env_file}"
  fi

  echo "Updated ${env_file} with namespace=${TB_DOCKER_NAMESPACE} and tag=${TAG}"
}

# Build and push images for linux/amd64 using buildx
SERVICES=("tv-listener" "signal-orchestrator" "order-gateway" "nginx-proxy")

for SERVICE in "${SERVICES[@]}"; do
  DOCKERFILE="docker/${SERVICE}.Dockerfile"
  IMAGE_BASE="${TB_DOCKER_NAMESPACE}/${SERVICE}"
  IMAGE_TAG_MAIN="${IMAGE_BASE}:${TAG}"
  IMAGE_TAG_SHA="${IMAGE_BASE}:${TAG}-${GIT_SHA}"

  echo "[build_and_push] Building and pushing ${IMAGE_TAG_MAIN} and ${IMAGE_TAG_SHA} for linux/amd64..."

  docker buildx build \
    --platform linux/amd64 \
    -f "${DOCKERFILE}" \
    -t "${IMAGE_TAG_MAIN}" \
    -t "${IMAGE_TAG_SHA}" \
    --push \
    "${ROOT_DIR}"
done

# Only update .env after all images are successfully built and pushed
# This ensures .env always matches the actual deployed image tags
update_env_file

echo "Build & push completed."

