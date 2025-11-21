# Phase 1 Release Workflow

This document describes how to build, tag, push, and deploy Docker images for the Phase 1 TradingView pipeline:

- `tv-listener`
- `signal-orchestrator`
- `order-gateway`

## 1. Versioning

The project uses a simple VERSION file in the repo root:

- `VERSION` contains a semantic-like version, for example:

  ```text
  0.1.0
  ```

Image tags are derived as:

- Base tag: `v<VERSION>` (e.g. `v0.1.0`)
- Extended tag: `v<VERSION>-<short_git_sha>` (e.g. `v0.1.0-a1b2c3d`)

At runtime, the effective tag is controlled by the `TRADEBOT_TAG` environment variable. If `TRADEBOT_TAG` is not set, it defaults to `v<VERSION>`.

## 2. Docker Image Naming

Phase 1 uses one image per service:

- `tv-listener`
- `signal-orchestrator`
- `order-gateway`

Images are published under a registry namespace defined by the `TB_DOCKER_NAMESPACE` environment variable. The final image names are:

- `${TB_DOCKER_NAMESPACE}/tv-listener:<TAG>`
- `${TB_DOCKER_NAMESPACE}/signal-orchestrator:<TAG>`
- `${TB_DOCKER_NAMESPACE}/order-gateway:<TAG>`

Examples:

**Docker Hub namespace:**

```text
TB_DOCKER_NAMESPACE=bcanmaya
```

**Images:**

- `bcanmaya/tv-listener:v0.1.0`
- `bcanmaya/signal-orchestrator:v0.1.0`
- `bcanmaya/order-gateway:v0.1.0`

## 3. Build & Push Images (local machine)

From the repo root:

**Make sure tests pass (inside Docker):**

```bash
./scripts/test_phase1_in_docker.sh
```

This script builds the Phase 1 service images and runs `pytest` inside the `tv-listener` container, which uses a Python 3.10+ runtime and the same dependencies as the services. This avoids issues with differing host Python versions.

**Set the Docker registry namespace:**

```bash
export TB_DOCKER_NAMESPACE="your-dockerhub-username-or-org"
```

**Optionally override the image tag (defaults to v<VERSION>):**

```bash
export TRADEBOT_TAG="v0.1.0"
```

**Ensure the build script is executable:**

```bash
chmod +x scripts/build_and_push_docker.sh
```

**Build and push images:**

```bash
./scripts/build_and_push_docker.sh
```

This will:

- Read `VERSION`.
- Compute a base tag (`v<VERSION>`) and a short git SHA.
- Build images for:
  - `tv-listener`
  - `signal-orchestrator`
  - `order-gateway`
- Tag each image with:
  - `${TB_DOCKER_NAMESPACE}/<service>:${TRADEBOT_TAG}`
  - `${TB_DOCKER_NAMESPACE}/<service>:${TRADEBOT_TAG}-<gitsha}`
- Push both tags to the registry.

## 4. Server Deployment (Docker Compose)

On the target server:

**Ensure the repository (or at least docker-compose.yml) is present.**

**Set the same namespace and tag used during the build:**

```bash
export TB_DOCKER_NAMESPACE="your-dockerhub-username-or-org"
export TRADEBOT_TAG="v0.1.0"
```

**Pull the images:**

```bash
docker compose pull tv-listener signal-orchestrator order-gateway
```

**Start or restart the Phase 1 services:**

```bash
docker compose up -d tv-listener signal-orchestrator order-gateway
```

The docker-compose file uses the `image: "${TB_DOCKER_NAMESPACE:-tradebot-local}/<service>:${TRADEBOT_TAG:-dev}"` pattern, so these environment variables determine which images are pulled and run.

## 5. Git Commit & Push

It is recommended to commit code changes before or together with a release.

**Typical workflow from the repo root:**

```bash
git status
git add .
git commit -m "Phase 1: TradingView DRY_RUN pipeline release v0.1.0"
git push origin main
```

You can bump the `VERSION` file (for example from `0.1.0` to `0.1.1`) as part of the changes when preparing a new release.

**Always ensure that:**

- Tests pass (run `./scripts/test_phase1_in_docker.sh`).
- Images are built and pushed with the new tag.
- The same tag is used on the server via `TRADEBOT_TAG`.

