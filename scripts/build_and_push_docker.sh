#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

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

build_and_push() {
  local service_name="$1"
  local dockerfile="$2"

  local image="${TB_DOCKER_NAMESPACE}/${service_name}"

  echo "Building image: ${image}:${TAG}"
  docker build \
    -f "${dockerfile}" \
    -t "${image}:${TAG}" \
    -t "${image}:${TAG}-${GIT_SHA}" \
    "$ROOT_DIR"

  echo "Pushing image: ${image}:${TAG}"
  docker push "${image}:${TAG}"

  echo "Pushing image: ${image}:${TAG}-${GIT_SHA}"
  docker push "${image}:${TAG}-${GIT_SHA}"
}

build_and_push "tv-listener" "docker/tv-listener.Dockerfile"
build_and_push "signal-orchestrator" "docker/signal-orchestrator.Dockerfile"
build_and_push "order-gateway" "docker/order-gateway.Dockerfile"

# Only update .env after all images are successfully built and pushed
# This ensures .env always matches the actual deployed image tags
update_env_file

echo "Build & push completed."

