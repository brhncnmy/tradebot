# Phase 1 – TradingView to BingX (DRY_RUN) Pipeline

## Overview

Phase 1 implements a simple end-to-end pipeline from TradingView webhooks to BingX order execution:

```
TradingView -> tv-listener -> signal-orchestrator -> order-gateway -> BingX
```

In Phase 1, order-gateway runs primarily in `DRY_RUN` mode for safety. This means orders are validated and logged, but no real trades are executed on the exchange. Instead, fake order IDs (e.g., `dryrun-abc123...`) are returned for verification.

## Services Involved

- **nginx-proxy**: Reverse proxy exposed on port 80. Forwards `/webhook/tradingview` and `/health` to tv-listener.

- **tv-listener**: Receives TradingView webhooks, validates the payload, and normalizes it into a `NormalizedSignal` object that is forwarded to signal-orchestrator.

- **signal-orchestrator**: Applies routing profiles (e.g., `default`) and builds `OpenOrderRequest` objects for each target account. By default, signals are routed to the `bingx_primary` account.

- **order-gateway**: Executes orders per account configuration. For accounts in `DRY_RUN` mode, it returns fake order IDs without making real API calls to BingX. For `LIVE` mode accounts, it calls the BingX API to place actual orders.

## TradingView Webhook URL

The nginx-proxy service listens on port 80 and forwards requests to tv-listener. The TradingView webhook URL is:

```
http://<server-ip>/webhook/tradingview
```

This uses HTTP on port 80 (no explicit port in the URL). The nginx-proxy forwards `/webhook/tradingview` to the internal tv-listener service.

**Note**: For local testing or debugging, you can still access tv-listener directly on port 8000 (e.g., `http://localhost:8000/webhook/tradingview`), but TradingView should use port 80 through nginx-proxy.

## TradingView JSON Payload Schema

The webhook expects a JSON payload matching the `TradingViewWebhookPayload` schema:

- **`symbol`** (string, required) – Trading symbol. Can be a clean symbol like `"BTC-USDT"` or a TradingView ticker like `"BINANCE:LIGHTUSDT.P"`. The tv-listener automatically normalizes ticker formats (e.g., `"BINANCE:LIGHTUSDT.P"` → `"LIGHTUSDT"`).

- **`side`** (string, required) – Position direction: `"long"`, `"short"`, `"buy"`, or `"sell"` (case-insensitive). `"buy"` is treated as `"long"`, `"sell"` as `"short"`.

- **`entry_type`** (string, required) – Order type: `"market"` or `"limit"`.

- **`entry_price`** (number, optional) – Entry price. Required when `entry_type` is `"limit"`.

- **`quantity`** (number, required) – Position size in base units or contracts. In Phase 1, this must be provided explicitly in the payload.

- **`stop_loss`** (number, optional) – Stop-loss price level.

- **`take_profits`** (array, optional) – List of take-profit levels. Each element is an object:
  - `price` (number) – Take-profit price level.
  - `size_pct` (number, 0-100) – Percentage of position to close at this level.

- **`routing_profile`** (string, optional) – Routing profile name. Defaults to `"default"` if omitted.

- **`leverage`** (number, optional) – Leverage multiplier to use for this signal.

- **`strategy_name`** (string, optional) – Name of the TradingView strategy that generated the signal.

## Example TradingView JSON Payload

```json
{
  "symbol": "BTC-USDT",
  "side": "buy",
  "entry_type": "market",
  "entry_price": null,
  "quantity": 0.001,
  "stop_loss": 28000.0,
  "take_profits": [
    {"price": 31000.0, "size_pct": 50},
    {"price": 32000.0, "size_pct": 50}
  ],
  "routing_profile": "default",
  "leverage": 10,
  "strategy_name": "tv_example_strategy"
}
```

## TradingView Alert Configuration

To configure a TradingView alert:

1. **Alert type**: Use any TradingView strategy or condition that supports webhook alerts.

2. **Webhook URL**: Set the webhook URL to:
   ```
   http://<server-ip>/webhook/tradingview
   ```

3. **Message**: Use the JSON template from `templates/tradingview_alert_template.json` (see below). TradingView will expand placeholders like `{{ticker}}` and `{{strategy.order.action}}` before sending the webhook.

### Alert message template (with TradingView placeholders)

Use the following JSON in the TradingView **Message** field:

```json
{
  "source": "tradingview",
  "strategy_name": "ZenNadaWater_1m",
  "symbol": "{{ticker}}",
  "side": "{{strategy.order.action}}",
  "entry_type": "market",
  "entry_price": null,
  "quantity": 0.001,
  "leverage": 10.0,
  "stop_loss": 28000.0,
  "take_profits": [
    { "price": 31000.0, "size_pct": 50.0 },
    { "price": 32000.0, "size_pct": 50.0 }
  ],
  "routing_profile": "default"
}
```

**Key placeholders:**

- **`{{ticker}}`**  
  Expands to the current chart symbol, for example `BINANCE:LIGHTUSDT.P`.  
  The tv-listener service normalizes this into a clean symbol such as `LIGHTUSDT` before routing the signal, so the same alert template can be reused across multiple symbols.

- **`{{strategy.order.action}}`**  
  Expands to `buy` or `sell` depending on the strategy order.  
  The tv-listener maps `buy` to `long` and `sell` to `short` in the normalized signal.

**Other fields:**

- Numeric fields (`quantity`, `leverage`, `stop_loss`, `take_profits`) are static examples and can be tuned per strategy.
- `entry_type` can be set to `"limit"` if you want limit orders (requires `entry_price`).
- `routing_profile` defaults to `"default"` if omitted.

## Account Modes

Account modes are configured in `common/utils/config.py`. Each account can be set to one of four modes:

- **`dry`**: Log only, no API calls. Orders are logged but not sent to the exchange. Returns fake order IDs like `dryrun-...`.

- **`test`**: Test Order endpoint (`/openApi/swap/v2/trade/order/test` on PROD host). Validates order parameters without placing real orders. Requires API credentials.

- **`demo`**: Demo trading endpoint (`/openApi/swap/v2/trade/order` on VST host). Places orders in demo environment with virtual USDT. Requires API credentials.

- **`live`**: Real trading endpoint (`/openApi/swap/v2/trade/order` on PROD host). Places actual orders with real funds. Requires API credentials and careful testing.

### Default Configuration

The default `bingx_primary` account is configured with `mode="test"` for safety. This mode:
- Validates order parameters against BingX API
- Does not place real orders
- Requires valid API credentials

### Changing Account Mode

To change the account mode:

1. Edit `common/utils/config.py`:

   ```python
   "bingx_primary": AccountConfig(
       account_id="bingx_primary",
       exchange="bingx",
       mode="live",  # Options: "dry", "test", "demo", "live"
       api_key_env="BINGX_API_KEY",
       secret_key_env="BINGX_API_SECRET",
       source_key_env=None  # Optional
   )
   ```

2. Ensure `.env.bingx` contains the required credentials (for `test`, `demo`, or `live` modes):

   - `BINGX_API_KEY` – Your BingX API key
   - `BINGX_API_SECRET` – Your BingX secret key
   - `BINGX_VST_API_KEY` – Optional VST (demo) API key
   - `BINGX_VST_API_SECRET` – Optional VST (demo) API secret

  3. **Important**: 
   - Start with `dry` mode to verify logging
   - Then use `test` mode to validate API integration
   - Test thoroughly in `demo` mode before enabling `live` mode
   - Verify that signals are correctly routed, orders are properly formatted, and the system behaves as expected

## Environment Variables and Secrets

TradeBot uses separate files for project metadata and API secrets:

### `.env` (Project Metadata)

The `.env` file in the repo root contains project-level metadata that is managed by release scripts:

- `TB_DOCKER_NAMESPACE` – Docker Hub namespace (e.g., `burhancanmaya`)
- `TRADEBOT_TAG` – Current release tag (e.g., `v0.1.6`)

**Important**: The release script (`scripts/release_phase1.sh`) updates `TRADEBOT_TAG` in-place without removing other lines. You can add custom entries to `.env`, but they should not conflict with the managed variables.

### `.env.bingx` (BingX API Secrets)

The `.env.bingx` file contains BingX API credentials and is **not committed to git** (it's in `.gitignore`):

- `BINGX_API_KEY` – BingX API key for test/live trading
- `BINGX_API_SECRET` – BingX API secret for test/live trading
- `BINGX_VST_API_KEY` – BingX VST (demo) API key (optional)
- `BINGX_VST_API_SECRET` – BingX VST (demo) API secret (optional)

**Setup on server**:

1. Create `.env.bingx` in the repo root on the server:

   ```bash
   cd ~/tradebot
   cat > .env.bingx << 'EOF'
   BINGX_API_KEY=your_api_key_here
   BINGX_API_SECRET=your_secret_here
   BINGX_VST_API_KEY=your_vst_key_here  # Optional
   BINGX_VST_API_SECRET=your_vst_secret_here  # Optional
   EOF
   ```

2. The `order-gateway` service automatically loads these variables via `env_file: - .env.bingx` in `docker-compose.yml`.

3. Verify credentials are loaded:

   ```bash
   docker compose exec order-gateway env | grep BINGX
   ```

**Note**: The `order-gateway` service does not read `BINGX_*` variables from `.env`. It only uses `.env.bingx` through the `env_file` directive in `docker-compose.yml`.

