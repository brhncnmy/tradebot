import os
from datetime import datetime
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from common.models.normalized_signal import NormalizedSignal, TakeProfitLevel, Side
from common.utils.logging import get_logger

app = FastAPI(title="tv-listener")
logger = get_logger("tv-listener")


class TradingViewTpLevel(BaseModel):
    """TradingView take profit level."""
    price: float
    size_pct: float = Field(gt=0, le=100)


class TradingViewWebhookPayload(BaseModel):
    """TradingView webhook payload model."""
    symbol: str
    side: str  # "long", "short", "buy", "sell"
    entry_type: str  # "market" or "limit"
    entry_price: Optional[float] = None
    quantity: float
    stop_loss: Optional[float] = None
    take_profits: Optional[List[TradingViewTpLevel]] = None
    routing_profile: Optional[str] = None
    leverage: Optional[float] = None
    strategy_name: Optional[str] = None


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


def map_tradingview_payload_to_normalized_signal(payload: TradingViewWebhookPayload) -> NormalizedSignal:
    """
    Map TradingView webhook payload to NormalizedSignal.
    
    Args:
        payload: TradingViewWebhookPayload instance
        
    Returns:
        NormalizedSignal instance
        
    Raises:
        ValueError: If required fields are invalid or missing
    """
    # Normalize side
    side_raw = payload.side.lower()
    if side_raw in ("long", "buy"):
        normalized_side: Side = "long"
    elif side_raw in ("short", "sell"):
        normalized_side = "short"
    else:
        raise ValueError(f"Invalid side: {payload.side}. Must be one of: long, short, buy, sell")
    
    # Normalize entry_type
    normalized_entry_type = payload.entry_type.lower()
    if normalized_entry_type not in ("market", "limit"):
        raise ValueError(f"Invalid entry_type: {payload.entry_type}. Must be 'market' or 'limit'")
    
    # Validate limit order requires entry_price
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
    
    # Build NormalizedSignal
    return NormalizedSignal(
        source="tradingview",
        strategy_name=payload.strategy_name,
        symbol=normalized_symbol,
        side=normalized_side,
        entry_type=normalized_entry_type,
        entry_price=payload.entry_price,
        quantity=payload.quantity,
        leverage=payload.leverage,
        stop_loss=payload.stop_loss,
        take_profits=tp_list,
        routing_profile=routing_profile,
        timestamp=datetime.utcnow(),
        raw_payload=payload.model_dump()  # keep original symbol inside raw payload
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "tv-listener"}


@app.get("/debug/example-tradingview-payload")
async def example_tradingview_payload():
    """Return an example TradingView webhook payload for reference."""
    example = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "stop_loss": 28000.0,
        "take_profits": [
            {"price": 31000.0, "size_pct": 50},
            {"price": 32000.0, "size_pct": 50},
        ],
        "routing_profile": "default",
        "leverage": 10,
        "strategy_name": "tv_example_strategy",
    }
    return example


@app.post("/webhook/tradingview")
async def tradingview_webhook(payload: TradingViewWebhookPayload):
    """
    Receive TradingView webhook and forward to signal-orchestrator.
    
    Args:
        payload: TradingViewWebhookPayload from TradingView
        
    Returns:
        Response with forwarding status
    """
    logger.info(f"Received TradingView webhook: {payload.model_dump()}")
    
    try:
        signal = map_tradingview_payload_to_normalized_signal(payload)
    except ValueError as err:
        logger.error(f"Failed to map payload: {err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    
    logger.info(f"Mapped to normalized signal: {signal.model_dump(mode='json')}")
    
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
