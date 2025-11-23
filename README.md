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

### Phase 1 – Release & Deployment

**Local release (from your dev or CI environment)**

1. Pick a new version (for example `0.1.1`).
2. Run:

   ```bash
   scripts/release_phase1.sh 0.1.1
   ```

   This will:

   - Update the `VERSION` file,
   - Run tests inside Docker,
   - Build and push images for `linux/amd64`,
   - Update `.env` with `TB_DOCKER_NAMESPACE` and `TRADEBOT_TAG`,
   - Commit and push changes to GitHub.

**Server deployment**

On the server where TradeBot runs:

```bash
cd /path/to/tradebot
scripts/deploy_phase1.sh
```

This script pulls the latest code, pulls the correct images based on `.env`, and restarts the Phase 1 services with `docker compose up -d`.

For detailed documentation, see `docs/release_workflow_phase1.md`.

