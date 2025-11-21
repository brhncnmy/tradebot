# TradeBot v2

Automated trading system built as a Python monorepo with microservices communicating via HTTP/JSON and orchestrated with Docker Compose.

## Phase 1 – TradingView DRY_RUN Pipeline

In Phase 1, TradeBot supports a simple end-to-end pipeline from TradingView to BingX via three core services:

- **tv-listener**: Receives TradingView webhooks and normalizes them into `NormalizedSignal` objects.
- **signal-orchestrator**: Applies routing profiles (e.g. `default`) and builds `OpenOrderRequest` objects per account (e.g. `bingx_primary`).
- **order-gateway**: Executes orders per account. In `DRY_RUN` mode it generates fake order IDs such as `dryrun-...` without touching the exchange.

### Basic workflow:

1. Start the services:

   ```bash
   docker compose build tv-listener signal-orchestrator order-gateway
   docker compose up -d tv-listener signal-orchestrator order-gateway
   ```

   (Optional: Run tests first with `./scripts/test_phase1_in_docker.sh`)

2. Expose tv-listener externally (e.g. via reverse proxy) so that you can call:
   ```
   https://<your-domain>/tv-listener/webhook/tradingview
   ```

3. In TradingView, configure an alert with:
   - Webhook URL: your externally reachable URL.
   - Message: a JSON payload matching the format described in `docs/phase1_tradingview_pipeline.md`.

4. Verify behavior:
   - When an alert fires, tv-listener forwards it to signal-orchestrator.
   - signal-orchestrator routes the signal to order-gateway.
   - order-gateway logs the order request and, for DRY_RUN accounts, returns a `dryrun-...` order ID.

By default, the `bingx_primary` account is configured as `DRY_RUN`. To enable LIVE trading, you must:

- Change the account mode to `LIVE` in `common/utils/config.py`.
- Provide valid BingX API credentials via environment variables.
- Carefully test in `DRY_RUN` before enabling `LIVE`.

For detailed documentation, see `docs/phase1_tradingview_pipeline.md`.

### Release & Deployment (Phase 1)

For building and pushing versioned Docker images and deploying them on a server with Docker Compose, see:

- `docs/release_workflow_phase1.md`

In short:

- Maintain the `VERSION` file at the repo root (e.g. `0.1.0`).
- Before building images, run the Phase 1 tests inside Docker:

  ```bash
  chmod +x scripts/test_phase1_in_docker.sh
  ./scripts/test_phase1_in_docker.sh
  ```

- Set `TB_DOCKER_NAMESPACE` to your Docker registry namespace (for example your Docker Hub username).
- Optionally set `TRADEBOT_TAG` to a specific tag (defaults to `v<VERSION>`).
- Then build and push the images:

  ```bash
  chmod +x scripts/build_and_push_docker.sh
  ./scripts/build_and_push_docker.sh
  ```

On the server, set the same `TB_DOCKER_NAMESPACE` and `TRADEBOT_TAG`, then:

```bash
docker compose pull tv-listener signal-orchestrator order-gateway
docker compose up -d tv-listener signal-orchestrator order-gateway
```

This ensures that the Phase 1 TradingView → tv-listener → signal-orchestrator → order-gateway → BingX pipeline runs with explicit, versioned Docker images.

