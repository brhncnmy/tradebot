# Phase 1 – TradingView to BingX (DRY_RUN) Pipeline

## Overview

Phase 1 implements a simple end-to-end pipeline from TradingView webhooks to BingX order execution:

```
TradingView -> tv-listener -> signal-orchestrator -> order-gateway -> BingX
```

In Phase 1, order-gateway runs primarily in `DRY_RUN` mode for safety. This means orders are validated and logged, but no real trades are executed on the exchange. Instead, fake order IDs (e.g., `dryrun-abc123...`) are returned for verification.

## Services Involved

- **tv-listener**: Receives TradingView webhooks, validates the payload, and normalizes it into a `NormalizedSignal` object that is forwarded to signal-orchestrator.

- **signal-orchestrator**: Applies routing profiles (e.g., `default`) and builds `OpenOrderRequest` objects for each target account. By default, signals are routed to the `bingx_primary` account.

- **order-gateway**: Executes orders per account configuration. For accounts in `DRY_RUN` mode, it returns fake order IDs without making real API calls to BingX. For `LIVE` mode accounts, it calls the BingX API to place actual orders.

## TradingView Webhook URL

The tv-listener service exposes a `POST /webhook/tradingview` endpoint internally. When exposed externally via a reverse proxy, the URL typically follows this pattern:

```
https://<your-domain>/tv-listener/webhook/tradingview
```

The exact path may depend on your reverse proxy configuration, but the internal FastAPI route is always `/webhook/tradingview`.

## TradingView JSON Payload Schema

The webhook expects a JSON payload matching the `TradingViewWebhookPayload` schema:

- **`symbol`** (string, required) – Trading symbol, e.g., `"BTC-USDT"`.

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

2. **Webhook URL**: Set the webhook URL to your externally exposed tv-listener endpoint (e.g., `https://<your-domain>/tv-listener/webhook/tradingview`).

3. **Message**: In the alert message field, paste the JSON payload exactly as shown in the example above. TradingView will send this JSON as-is in the webhook POST request body.

## DRY_RUN vs LIVE

Account modes are configured in `common/utils/config.py`:

- The default `bingx_primary` account is configured with `mode="DRY_RUN"` for safety.

- To enable LIVE trading:

  1. Change the account mode to `LIVE` in the config:

     ```python
     "bingx_primary": AccountConfig(
         account_id="bingx_primary",
         exchange="bingx",
         mode="LIVE",  # Changed from DRY_RUN
         api_key_env="BINGX_PRIMARY_API_KEY",
         secret_key_env="BINGX_PRIMARY_SECRET_KEY",
         source_key_env="BINGX_PRIMARY_SOURCE_KEY"
     )
     ```

  2. Set the required environment variables:

     - `BINGX_PRIMARY_API_KEY` – Your BingX API key
     - `BINGX_PRIMARY_SECRET_KEY` – Your BingX secret key
     - `BINGX_PRIMARY_SOURCE_KEY` – Optional source key

  3. **Important**: Thoroughly test your pipeline in `DRY_RUN` mode before enabling `LIVE` mode. Verify that signals are correctly routed, orders are properly formatted, and the system behaves as expected.

