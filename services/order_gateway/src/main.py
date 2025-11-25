import os
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from fastapi import FastAPI, HTTPException

from common.models.normalized_signal import Side
from common.models.order_request import OpenOrderRequest
from common.models.tv_command import TvCommand
from common.utils.config import get_account
from common.utils.logging import get_logger
from services.order_gateway.src.exchanges.bingx_client import bingx_place_order

app = FastAPI(title="order-gateway")
logger = get_logger("order-gateway")


class ActionType(str, Enum):
    """Internal routed actions derived from TradingView commands."""

    OPEN_POSITION = "OPEN_POSITION"
    CLOSE_POSITION_FULL = "CLOSE_POSITION_FULL"
    CLOSE_POSITION_PARTIAL = "CLOSE_POSITION_PARTIAL"
    CLOSE_ALL_POSITIONS = "CLOSE_ALL_POSITIONS"


@dataclass
class RoutedAction:
    """Action derived from a TradingView command."""

    action_type: ActionType
    symbol: str
    side: Optional[Side]
    quantity: Optional[float]
    tp_close_pct: Optional[float]
    margin_type: Optional[str]
    leverage: Optional[float]
    command: TvCommand


def map_command_to_action(request: OpenOrderRequest) -> RoutedAction:
    """Map TradingView command to an internal routed action."""

    command = request.command

    if command == TvCommand.ENTER_LONG:
        return RoutedAction(
            action_type=ActionType.OPEN_POSITION,
            symbol=request.symbol,
            side="long",
            quantity=request.quantity,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.ENTER_SHORT:
        return RoutedAction(
            action_type=ActionType.OPEN_POSITION,
            symbol=request.symbol,
            side="short",
            quantity=request.quantity,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.EXIT_LONG:
        return RoutedAction(
            action_type=ActionType.CLOSE_POSITION_FULL,
            symbol=request.symbol,
            side="long",
            quantity=request.quantity,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.EXIT_SHORT:
        return RoutedAction(
            action_type=ActionType.CLOSE_POSITION_FULL,
            symbol=request.symbol,
            side="short",
            quantity=request.quantity,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.EXIT_LONG_ALL:
        return RoutedAction(
            action_type=ActionType.CLOSE_POSITION_FULL,
            symbol=request.symbol,
            side="long",
            quantity=None,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.EXIT_SHORT_ALL:
        return RoutedAction(
            action_type=ActionType.CLOSE_POSITION_FULL,
            symbol=request.symbol,
            side="short",
            quantity=None,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.EXIT_LONG_PARTIAL:
        return RoutedAction(
            action_type=ActionType.CLOSE_POSITION_PARTIAL,
            symbol=request.symbol,
            side="long",
            quantity=None,
            tp_close_pct=request.tp_close_pct,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.EXIT_SHORT_PARTIAL:
        return RoutedAction(
            action_type=ActionType.CLOSE_POSITION_PARTIAL,
            symbol=request.symbol,
            side="short",
            quantity=None,
            tp_close_pct=request.tp_close_pct,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )
    if command == TvCommand.CANCEL_ALL:
        return RoutedAction(
            action_type=ActionType.CLOSE_ALL_POSITIONS,
            symbol=request.symbol,
            side=None,
            quantity=None,
            tp_close_pct=None,
            margin_type=request.margin_type,
            leverage=request.leverage,
            command=command,
        )

    raise ValueError(f"Unhandled command: {command}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "order-gateway"}


@app.post("/orders/open")
async def open_order(request: OpenOrderRequest):
    """
    Process order request and route to exchange.
    
    Args:
        request: OpenOrderRequest with order details
        
    Returns:
        Response with order status and order ID
    """
    # Fetch account config
    try:
        account_cfg = get_account(request.account.account_id)
    except ValueError as e:
        logger.error(f"Account lookup failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # Validate exchange
    if account_cfg.exchange.lower() != "bingx":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported exchange: {account_cfg.exchange}"
        )

    # Interpret command into routed action
    try:
        action = map_command_to_action(request)
    except ValueError as exc:
        logger.error("Failed to map command: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info(
        "Order-gateway routed action: type=%s symbol=%s side=%s quantity=%s tp_close_pct=%s margin_type=%s leverage=%s command=%s",
        action.action_type.value,
        action.symbol,
        action.side,
        action.quantity,
        action.tp_close_pct,
        action.margin_type,
        action.leverage,
        request.command.value,
    )

    # For EXIT commands, allow them to go through the same order path as ENTER
    # They will use the opposite side (BUY to close SHORT, SELL to close LONG)
    if action.action_type == ActionType.CLOSE_POSITION_FULL and request.command in (TvCommand.EXIT_LONG, TvCommand.EXIT_SHORT):
        # EXIT_LONG means we need to SELL (close long position)
        # EXIT_SHORT means we need to BUY (close short position)
        # The side in the request should already be correct from upstream
        if request.quantity is None or request.quantity <= 0:
            raise HTTPException(status_code=400, detail="quantity required for EXIT commands")
        if request.side is None:
            if action.side is None:
                raise HTTPException(status_code=400, detail="side required for EXIT commands")
            request = OpenOrderRequest(**request.model_dump(), side=action.side)
        # Treat EXIT as a regular order (closing is just opening the opposite side)
        return await handle_bingx_order(account_cfg, request)
    
    if action.action_type != ActionType.OPEN_POSITION:
        logger.info(
            "Action %s for symbol=%s is recognized but not implemented yet (demo logging only).",
            action.action_type.value,
            action.symbol,
        )
        return {
            "status": "accepted",
            "mode": account_cfg.mode,
            "exchange": account_cfg.exchange,
            "action": action.action_type.value,
            "note": "Action recognized but not implemented yet",
        }
    
    # Ensure required fields for open position
    if request.quantity is None or request.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity required for OPEN_POSITION actions")
    if request.side is None:
        if action.side is None:
            raise HTTPException(status_code=400, detail="side required for OPEN_POSITION actions")
        request = OpenOrderRequest(**request.model_dump(), side=action.side)

    # Handle BingX orders based on mode
    return await handle_bingx_order(account_cfg, request)


async def handle_bingx_order(account_cfg, request: OpenOrderRequest):
    """
    Handle BingX order based on account mode.
    
    Args:
        account_cfg: AccountConfig instance
        request: OpenOrderRequest instance
        
    Returns:
        Response dict with order status
    """
    mode = account_cfg.mode
    
    # Dry mode: log only, no API call
    if mode == "dry":
        fake_id = f"dryrun-{uuid.uuid4().hex}"
        logger.info(
            f"DRY_RUN order: account_id={account_cfg.account_id}, "
            f"exchange={account_cfg.exchange}, symbol={request.symbol}, "
            f"side={request.side}, entry_type={request.entry_type}, "
            f"quantity={request.quantity}"
        )
        return {
            "status": "accepted",
            "mode": "dry",
            "exchange": account_cfg.exchange,
            "order_id": fake_id
        }
    
    # Test, demo, or live mode: make API call
    # Read credentials to log status (without exposing secrets)
    api_key, secret_key = account_cfg.get_credentials()
    
    logger.info(
        "BingX account resolved: id=%s, exchange=%s, mode=%s, has_api_key=%s, has_secret=%s",
        account_cfg.account_id,
        account_cfg.exchange,
        account_cfg.mode,
        bool(api_key),
        bool(secret_key),
    )
    
    try:
        response = await bingx_place_order(account_cfg, request)
        
        # Extract order ID from response
        order_id = response.get("data", {}).get("orderId") or response.get("orderId")
        
        logger.info(
            f"BingX order sent: mode={mode}, account_id={account_cfg.account_id}, "
            f"symbol={request.symbol}, side={request.side}, quantity={request.quantity}, "
            f"response_code={response.get('code')}, order_id={order_id}"
        )
        
        return {
            "status": "accepted",
            "mode": mode,
            "exchange": account_cfg.exchange,
            "order_id": order_id,
            "raw": response
        }
    except ValueError as e:
        logger.error(f"BingX order validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except RuntimeError as e:
        # BingX API errors (e.g., signature verification failed, invalid API key)
        error_msg = str(e)
        logger.error(
            f"BingX API error: mode={mode}, account_id={account_cfg.account_id}, "
            f"symbol={request.symbol}, side={request.side}, quantity={request.quantity}, "
            f"error={error_msg}"
        )
        # Return 400 for API-level errors (bad request, authentication issues)
        # This is more appropriate than 502 (bad gateway) for API errors
        raise HTTPException(
            status_code=400,
            detail=f"BingX API error: {error_msg}"
        )
    except Exception as e:
        # Network errors, connection issues, etc. - these are true gateway errors
        logger.exception(
            f"BingX order failed (network/system error): mode={mode}, account_id={account_cfg.account_id}, "
            f"symbol={request.symbol}, side={request.side}, quantity={request.quantity}, "
            f"error={e}"
        )
        raise HTTPException(
            status_code=502,
            detail=f"Failed to place order on BingX: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.order_gateway.src.main:app", host="0.0.0.0", port=8002, reload=True)
