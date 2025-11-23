# Phase 1 Release Workflow

This document describes how to build, tag, push, and deploy Docker images for the Phase 1 TradingView pipeline:

- `nginx-proxy` (reverse proxy on port 80)
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

- `nginx-proxy` (reverse proxy on port 80)
- `tv-listener`
- `signal-orchestrator`
- `order-gateway`

Images are published under a registry namespace defined by the `TB_DOCKER_NAMESPACE` environment variable. The final image names are:

- `${TB_DOCKER_NAMESPACE}/nginx-proxy:<TAG>`
- `${TB_DOCKER_NAMESPACE}/tv-listener:<TAG>`
- `${TB_DOCKER_NAMESPACE}/signal-orchestrator:<TAG>`
- `${TB_DOCKER_NAMESPACE}/order-gateway:<TAG>`

Examples:

**Docker Hub namespace:**

```text
TB_DOCKER_NAMESPACE=bcanmaya
```

**Images:**

- `bcanmaya/nginx-proxy:v0.1.0`
- `bcanmaya/tv-listener:v0.1.0`
- `bcanmaya/signal-orchestrator:v0.1.0`
- `bcanmaya/order-gateway:v0.1.0`

## 3. Local Release (Phase 1)

On your release machine (local or CI):

**1. Choose a new version (for example `0.1.1`) and run:**

```bash
scripts/release_phase1.sh 0.1.1
```

This script will:

- Set `VERSION` to `0.1.1`,
- Run tests inside Docker,
- Build and push images for `linux/amd64` using `TB_DOCKER_NAMESPACE` and `TRADEBOT_TAG`,
- Update the `.env` file with `TB_DOCKER_NAMESPACE` and `TRADEBOT_TAG`,
- Commit and push all changes to GitHub.

**Note:** `scripts/build_and_push_docker.sh` uses `docker buildx build --platform linux/amd64` to ensure images are compatible with the Linux/amd64 server environment.

## 4. Server Deployment (Phase 1)

On the target server (where Docker Compose runs TradeBot):

```bash
scripts/deploy_phase1.sh
```

This script:

- Pulls the latest code from `main`,
- Uses the committed `.env` file to determine `TB_DOCKER_NAMESPACE` and `TRADEBOT_TAG`,
- Pulls the corresponding images (including nginx-proxy),
- Restarts the Phase 1 services with `docker compose up -d` (including nginx-proxy on port 80).

The reverse proxy on port 80 is now part of the standard deployment, providing external access to the TradingView webhook endpoint.

## 5. Git Commit & Push

The `scripts/release_phase1.sh` script automatically handles git commit and push as part of the release process. You do not need to manually commit or push changes when using the release script.

If you need to make changes outside of the release script, ensure that:

- Tests pass (run `./scripts/test_phase1_in_docker.sh`).
- Images are built and pushed with the new tag.
- The same tag is used on the server via `TRADEBOT_TAG`.

