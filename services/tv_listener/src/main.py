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
    """
    TradingView webhook payload model.
    
    Supports both legacy format (with 'side' and 'entry_type') and new command-based format.
    
    Expected TradingView alert payload:
    {
      "command": "ENTER",  // Optional, defaults to "ENTER" if omitted
      "symbol": "{{ticker}}",
      "side": "{{strategy.order.action}}",  // "buy" or "sell" (normalized to LONG/SHORT)
      "entry_type": "market",  // or "order_type"
      "entry_price": {{strategy.order.price}},
      "quantity": {{strategy.order.contracts}},
      "stop_loss": null,  // Optional, nullable
      "take_profits": null,  // Optional, nullable
      "routing_profile": "default",
      "leverage": 10,
      "strategy_name": "{{strategy.order.comment}}"
    }
    
    Notes:
    - 'command' defaults to "ENTER" if omitted (backward compatibility)
    - 'side' accepts: "buy", "sell", "long", "short" (case-insensitive, normalized to LONG/SHORT)
    - Both 'entry_type' and 'order_type' are accepted (prefers 'order_type')
    - 'stop_loss' and 'take_profits' can be null
    """
    # Command field: optional, defaults to "ENTER" for backward compatibility
    command: Optional[str] = Field(default="ENTER", description="TradingView command (defaults to ENTER)")
    
    # Symbol (required)
    symbol: str
    
    # Side field: accepts buy/sell/long/short, normalized internally
    side: Optional[str] = Field(None, description="Position side: buy/sell/long/short (normalized to LONG/SHORT)")
    
    # Order type: accept both 'entry_type' and 'order_type' for compatibility
    order_type: Optional[str] = Field(default="market", description="Order type: market or limit")
    entry_type: Optional[str] = Field(None, description="Legacy field: same as order_type")
    
    # Code field: used to determine entry/exit intent
    code: Optional[str] = Field(None, description="TradingView code field (e.g., 'short entry', 'long exit')")
    
    # Optional fields
    entry_price: Optional[float] = None
    quantity: Optional[float] = None
    margin_type: Optional[str] = None
    leverage: Optional[float] = None
    tp_close_pct: Optional[float] = None
    routing_profile: Optional[str] = None
    strategy_name: Optional[str] = None
    timestamp: Optional[int] = None
    stop_loss: Optional[float] = Field(None, description="Stop loss price (nullable)")
    take_profits: Optional[List[TradingViewTpLevel]] = Field(None, description="Take profit levels (nullable)")
    
    def normalize_side(self) -> Optional[str]:
        """
        Normalize side field to LONG or SHORT.
        
        Returns:
            "LONG", "SHORT", or None if side is not provided
        """
        if not self.side:
            return None
        
        side_upper = self.side.upper().strip()
        
        # Map buy/sell to LONG/SHORT
        if side_upper in ("BUY", "LONG"):
            return "LONG"
        if side_upper in ("SELL", "SHORT"):
            return "SHORT"
        
        # If already LONG/SHORT, return as-is
        if side_upper in ("LONG", "SHORT"):
            return side_upper
        
        raise ValueError(f"Invalid side value: {self.side}. Must be one of: buy, sell, long, short")
    
    def get_order_type(self) -> str:
        """Get order type, preferring order_type over entry_type."""
        return (self.order_type or self.entry_type or "market").lower()


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
        TvCommand.EXIT_LONG,
        TvCommand.EXIT_LONG_ALL,
        TvCommand.EXIT_LONG_PARTIAL,
    ):
        return "long"
    if command in (
        TvCommand.ENTER_SHORT,
        TvCommand.EXIT_SHORT,
        TvCommand.EXIT_SHORT_ALL,
        TvCommand.EXIT_SHORT_PARTIAL,
    ):
        return "short"
    return None


def normalize_tradingview_payload(payload: TradingViewWebhookPayload) -> tuple[str, Optional[str]]:
    """
    Normalize TradingView payload to determine command and side.
    
    Uses the 'code' field first to determine entry/exit intent, then falls back
    to side-based logic for backward compatibility. Also handles direct command values.
    
    Args:
        payload: TradingViewWebhookPayload instance
        
    Returns:
        Tuple of (command_str, side_norm) where:
        - command_str: One of "ENTER_LONG", "ENTER_SHORT", "EXIT_LONG", "EXIT_SHORT", etc.
        - side_norm: "long" or "short" or None
        
    Raises:
        ValueError: If required fields are invalid or missing
    """
    # Check if command is already a full command (e.g., "ENTER_LONG", "EXIT_SHORT")
    command_str = (payload.command or "ENTER").strip().upper()
    
    # Try to parse as a known command first
    try:
        TvCommand(command_str)
        # Command is valid, derive side from command
        if command_str.startswith("ENTER_LONG") or command_str.startswith("EXIT_LONG"):
            side_norm = "long"
        elif command_str.startswith("ENTER_SHORT") or command_str.startswith("EXIT_SHORT"):
            side_norm = "short"
        else:
            side_norm = None
        return command_str, side_norm
    except (ValueError, AttributeError):
        # Command is not a known full command, continue with code/side logic
        pass
    
    # Normalize side if provided
    side_norm: Optional[str] = None
    if payload.side:
        try:
            side_raw = payload.side.lower().strip()
            if side_raw in ["buy", "long"]:
                side_norm = "long"
            elif side_raw in ["sell", "short"]:
                side_norm = "short"
            else:
                logger.warning(f"Invalid side value: {payload.side}")
                raise ValueError(f"Invalid side value: {payload.side}. Must be one of: buy, sell, long, short")
        except ValueError as e:
            raise ValueError(f"Invalid side: {e}") from e
    
    # Determine base intent using code first
    code_raw = (payload.code or "").lower().strip()
    intent = "ENTER"  # default
    dir_from_code: Optional[str] = None
    
    if "short exit" in code_raw:
        intent = "EXIT"
        dir_from_code = "short"
    elif "long exit" in code_raw:
        intent = "EXIT"
        dir_from_code = "long"
    elif "short entry" in code_raw:
        intent = "ENTER"
        dir_from_code = "short"
    elif "long entry" in code_raw:
        intent = "ENTER"
        dir_from_code = "long"
    else:
        # Fallback: use side for backward compatibility
        if side_norm:
            intent = "ENTER"
            dir_from_code = side_norm
    
    # Derive final command from (intent, dir)
    if intent == "ENTER" and dir_from_code == "long":
        command_str = "ENTER_LONG"
    elif intent == "ENTER" and dir_from_code == "short":
        command_str = "ENTER_SHORT"
    elif intent == "EXIT" and dir_from_code == "long":
        command_str = "EXIT_LONG"
    elif intent == "EXIT" and dir_from_code == "short":
        command_str = "EXIT_SHORT"
    else:
        # Final fallback: if we have side but no code match, default to ENTER
        if side_norm:
            if side_norm == "long":
                command_str = "ENTER_LONG"
            else:
                command_str = "ENTER_SHORT"
        else:
            # If we still can't determine command and the original command_str was not "ENTER", 
            # it might be an invalid command - try to parse it to get a better error
            if command_str not in ("ENTER", ""):
                try:
                    TvCommand(command_str)
                except (ValueError, AttributeError):
                    raise ValueError(f"Unsupported command: {command_str}")
            raise ValueError("Cannot determine command: missing both 'code' and 'side' fields")
    
    return command_str, side_norm


def map_tradingview_payload_to_normalized_signal(
    payload: TradingViewWebhookPayload,
    raw_payload_text: str,
) -> NormalizedSignal:
    """
    Map TradingView webhook payload to NormalizedSignal.
    
    Args:
        payload: TradingViewWebhookPayload instance
        raw_payload_text: Raw JSON body text
        
    Returns:
        NormalizedSignal instance
        
    Raises:
        ValueError: If required fields are invalid or missing
    """
    # Normalize command and side using code field
    try:
        command_str, normalized_side = normalize_tradingview_payload(payload)
    except ValueError as e:
        raise ValueError(f"Failed to normalize payload: {e}") from e
    
    # Parse command enum
    try:
        command = TvCommand(command_str)
    except Exception as exc:  # ValueError or AttributeError
        raise ValueError(f"Unsupported command: {command_str}") from exc
    
    # Ensure side is set from command (command takes precedence over payload side)
    # This ensures EXIT_SHORT has side="short" even if payload has side="buy"
    side_from_command = _map_command_to_side(command)
    if side_from_command is not None:
        normalized_side = side_from_command
    elif normalized_side is None:
        # Final fallback if command doesn't provide side
        normalized_side = _map_command_to_side(command)
    
    # Normalize order type (prefer order_type, fallback to entry_type)
    normalized_entry_type = payload.get_order_type()
    if normalized_entry_type not in ("market", "limit"):
        raise ValueError(f"Invalid order_type: {normalized_entry_type}. Must be 'market' or 'limit'")
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
        code=payload.code,
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
        "TradingView NORMALIZED: command=%s symbol=%s side=%s entry_type=%s quantity=%s code=%s",
        signal.command.value,
        signal.symbol,
        signal.side,
        signal.entry_type,
        signal.quantity,
        signal.code or "",
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
