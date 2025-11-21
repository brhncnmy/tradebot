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

echo "Build & push completed."

