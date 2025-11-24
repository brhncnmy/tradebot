import os
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from common.models.normalized_signal import NormalizedSignal, Side, TakeProfitLevel
from common.models.tv_command import TvCommand
from common.utils.logging import get_logger

app = FastAPI(title="tv-listener")
logger = get_logger("tv-listener")


class TradingViewTpLevel(BaseModel):
    """TradingView take profit level."""
    price: float
    size_pct: float = Field(gt=0, le=100)


class TradingViewWebhookPayload(BaseModel):
    """TradingView webhook payload model."""
    command: str
    symbol: str
    order_type: Optional[str] = "market"
    entry_price: Optional[float] = None
    quantity: Optional[float] = None
    margin_type: Optional[str] = None
    leverage: Optional[float] = None
    tp_close_pct: Optional[float] = None
    routing_profile: Optional[str] = None
    strategy_name: Optional[str] = None
    timestamp: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profits: Optional[List[TradingViewTpLevel]] = None


def normalize_symbol(symbol: str) -> str:
    """
    Normalize a TradingView symbol string into an exchange-agnostic symbol.
    
    Examples:
    - "BINANCE:LIGHTUSDT.P" -> "LIGHTUSDT"
    - "BINANCE:BTCUSDT.P"   -> "BTCUSDT"
    - "BTC-USDT"            -> "BTC-USDT" (left as-is)
    - "BINANCE:BTCUSDT"     -> "BTCUSDT"
    
    Args:
        symbol: Raw symbol string from TradingView (may include exchange prefix and suffix)
        
    Returns:
        Normalized symbol string (exchange-agnostic)
    """
    s = symbol.strip()
    
    # Drop exchange prefix if present (e.g. "BINANCE:LIGHTUSDT.P")
    if ":" in s:
        s = s.split(":", 1)[1]
    
    # Drop simple suffixes like ".P" or ".p"
    if s.endswith(".P") or s.endswith(".p"):
        s = s[:-2]
    
    return s


def _map_command_to_side(command: TvCommand) -> Optional[Side]:
    """Map TradingView command to a logical side when applicable."""
    if command in (
        TvCommand.ENTER_LONG,
        TvCommand.EXIT_LONG_ALL,
        TvCommand.EXIT_LONG_PARTIAL,
    ):
        return "long"
    if command in (
        TvCommand.ENTER_SHORT,
        TvCommand.EXIT_SHORT_ALL,
        TvCommand.EXIT_SHORT_PARTIAL,
    ):
        return "short"
    return None


def map_tradingview_payload_to_normalized_signal(
    payload: TradingViewWebhookPayload,
    raw_payload_text: str,
) -> NormalizedSignal:
    """
    Map TradingView webhook payload to NormalizedSignal.
    
    Args:
        payload: TradingViewWebhookPayload instance
        
    Returns:
        NormalizedSignal instance
        
    Raises:
        ValueError: If required fields are invalid or missing
    """
    # Parse command enum
    try:
        command = TvCommand(payload.command.strip().upper())
    except Exception as exc:  # ValueError or AttributeError
        raise ValueError(f"Unsupported command: {payload.command}") from exc
    
    normalized_side = _map_command_to_side(command)
    
    # Normalize order type (falls back to market)
    normalized_entry_type = (payload.order_type or "market").lower()
    if normalized_entry_type not in ("market", "limit"):
        raise ValueError(f"Invalid order_type: {payload.order_type}. Must be 'market' or 'limit'")
    if normalized_entry_type == "limit" and payload.entry_price is None:
        raise ValueError("entry_price required for limit orders")
    
    # Build take_profits list
    tp_list: List[TakeProfitLevel] = []
    if payload.take_profits is not None:
        for tp in payload.take_profits:
            tp_list.append(TakeProfitLevel(price=tp.price, size_pct=tp.size_pct))
    
    # Determine routing_profile
    routing_profile = payload.routing_profile or "default"
    
    # Normalize symbol (e.g. "BINANCE:LIGHTUSDT.P" -> "LIGHTUSDT")
    normalized_symbol = normalize_symbol(payload.symbol)
    
    # Convert TradingView timestamp (ms) to datetime if provided
    signal_timestamp = None
    if payload.timestamp:
        try:
            signal_timestamp = datetime.utcfromtimestamp(payload.timestamp / 1000)
        except Exception:
            logger.warning("Invalid timestamp value from TradingView: %s", payload.timestamp)
            signal_timestamp = datetime.utcnow()
    
    # Build NormalizedSignal
    # Basic field warnings (non-fatal)
    if command in (TvCommand.ENTER_LONG, TvCommand.ENTER_SHORT) and payload.quantity is None:
        logger.warning("TradingView payload missing quantity for command %s", command.value)
    
    return NormalizedSignal(
        command=command,
        source="tradingview",
        strategy_name=payload.strategy_name,
        symbol=normalized_symbol,
        side=normalized_side,
        entry_type=normalized_entry_type,
        entry_price=payload.entry_price,
        quantity=payload.quantity,
        leverage=payload.leverage,
        margin_type=payload.margin_type,
        tp_close_pct=payload.tp_close_pct,
        stop_loss=payload.stop_loss,
        take_profits=tp_list,
        routing_profile=routing_profile,
        timestamp=signal_timestamp or datetime.utcnow(),
        raw_payload=raw_payload_text,
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "tv-listener"}


@app.get("/debug/example-tradingview-payload")
async def example_tradingview_payload():
    """Return an example TradingView webhook payload for reference."""
    example = {
        "command": "ENTER_LONG",
        "symbol": "BTC-USDT",
        "order_type": "market",
        "quantity": 0.001,
        "stop_loss": 28000.0,
        "take_profits": [
            {"price": 31000.0, "size_pct": 50},
            {"price": 32000.0, "size_pct": 50},
        ],
        "routing_profile": "default",
        "leverage": 10,
        "margin_type": "ISOLATED",
        "tp_close_pct": None,
        "strategy_name": "tv_example_strategy",
        "timestamp": 1732387200000,
    }
    return example


@app.post("/webhook/tradingview")
async def tradingview_webhook(request: Request, payload: TradingViewWebhookPayload):
    """
    Receive TradingView webhook and forward to signal-orchestrator.
    
    Args:
        payload: TradingViewWebhookPayload from TradingView
        
    Returns:
        Response with forwarding status
    """
    raw_body = (await request.body()).decode("utf-8", errors="replace")
    logger.info("TradingView RAW payload: %s", raw_body)
    
    try:
        signal = map_tradingview_payload_to_normalized_signal(payload, raw_body)
    except ValueError as err:
        logger.error(f"Failed to map payload: {err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    
    logger.info(
        "TradingView NORMALIZED: command=%s symbol=%s quantity=%s margin_type=%s leverage=%s tp_close_pct=%s routing_profile=%s",
        signal.command.value,
        signal.symbol,
        signal.quantity,
        signal.margin_type,
        signal.leverage,
        signal.tp_close_pct,
        signal.routing_profile,
    )
    
    # Read env for signal orchestrator URL
    base_url = os.getenv("SIGNAL_ORCHESTRATOR_URL", "http://signal-orchestrator:8001")
    url = f"{base_url.rstrip('/')}/signals"
    
    # Forward to signal-orchestrator using JSON-safe serialization
    payload = signal.model_dump(mode="json")
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(url, json=payload)
            logger.info(f"Forwarded signal to orchestrator, status: {resp.status_code}")
            return {
                "status": "forwarded",
                "upstream_status": resp.status_code,
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to forward signal: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to forward signal: {str(e)}"
            )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
