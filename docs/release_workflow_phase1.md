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

### Environment file (.env)

The project uses a `.env` file in the repo root to provide non-secret deployment settings:

- `TB_DOCKER_NAMESPACE` – Docker registry namespace (for example `burhancanmaya`).
- `TRADEBOT_TAG` – Image tag to use in `docker-compose.yml` (for example `v0.1.0`).

The `scripts/build_and_push_docker.sh` release script automatically updates `.env` with the namespace and tag used for the release. The `.env` file is committed to git so that servers can simply `git pull` and use `docker compose` without manual `export` commands.

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

**1. Pull the latest code (which includes the updated `.env`):**

```bash
git pull origin main
```

**2. Pull and restart the Phase 1 services:**

```bash
docker compose pull tv-listener signal-orchestrator order-gateway
docker compose up -d tv-listener signal-orchestrator order-gateway
```

Docker Compose will automatically read `TB_DOCKER_NAMESPACE` and `TRADEBOT_TAG` from the `.env` file in the repo root. These values are updated during the release process and committed to git.

**Note:** If you need to override the values on a specific server, you can still `export` environment variables before running `docker compose`, but the default flow is `.env`-driven.

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

