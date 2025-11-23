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
update_env_file() {
  local env_file="${ROOT_DIR}/.env"
  echo "Updating ${env_file} with TB_DOCKER_NAMESPACE and TRADEBOT_TAG..."

  # Create a temp file to avoid partially written env
  local tmp_env_file="${env_file}.tmp"

  # If .env exists, strip existing TB_DOCKER_NAMESPACE and TRADEBOT_TAG lines
  if [[ -f "${env_file}" ]]; then
    grep -vE '^(TB_DOCKER_NAMESPACE|TRADEBOT_TAG)=' "${env_file}" > "${tmp_env_file}" || true
  else
    : > "${tmp_env_file}"
  fi

  # Append the canonical namespace and tag for this release
  {
    echo "TB_DOCKER_NAMESPACE=${TB_DOCKER_NAMESPACE}"
    echo "TRADEBOT_TAG=${TAG}"
  } >> "${tmp_env_file}"

  mv "${tmp_env_file}" "${env_file}"
  echo "Updated ${env_file} with namespace=${TB_DOCKER_NAMESPACE} and tag=${TAG}"
}

# Build and push images for linux/amd64 using buildx
SERVICES=("tv-listener" "signal-orchestrator" "order-gateway")

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

