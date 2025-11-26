"""BingX Swap API client supporting test, demo, and live trading modes.

Current error handling: Raises RuntimeError for any non-zero API code. HTTP errors raise httpx.HTTPError.
Code 101205 ("No position to close") is currently treated as a hard error, but should be a soft/no-op.
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Literal
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from common.models.order_request import OpenOrderRequest
from common.utils.config import AccountConfig
from common.utils.logging import get_logger
from services.order_gateway.src.exchanges.symbol_utils import to_bingx_symbol

logger = get_logger("bingx-client")


class BingxAPIError(Exception):
    """BingX API error with support for soft errors (e.g., no position to close)."""
    
    def __init__(self, api_code: int, api_msg: str, *, is_no_position: bool = False, raw_body: dict | None = None):
        self.api_code = api_code
        self.api_msg = api_msg
        self.is_no_position = is_no_position
        self.raw_body = raw_body or {}
        super().__init__(f"BingX API error: {api_msg} (code: {api_code})")


class BingxEnvironment(BaseModel):
    """BingX API environment configuration."""
    base_url: str
    order_path: str  # "/openApi/swap/v2/trade/order" or ".../order/test"


def get_bingx_env(mode: str) -> BingxEnvironment:
    """
    Get BingX environment configuration based on account mode.
    
    Args:
        mode: Account mode ("test", "demo", "live")
        
    Returns:
        BingxEnvironment with base_url and order_path
        
    Raises:
        ValueError: If mode is not supported for HTTP calls
    """
    if mode == "test":
        return BingxEnvironment(
            base_url="https://open-api.bingx.com",
            order_path="/openApi/swap/v2/trade/order/test",
        )
    elif mode == "demo":
        return BingxEnvironment(
            base_url="https://open-api-vst.bingx.com",
            order_path="/openApi/swap/v2/trade/order",
        )
    elif mode == "live":
        return BingxEnvironment(
            base_url="https://open-api.bingx.com",
            order_path="/openApi/swap/v2/trade/order",
        )
    # For "dry" we will not call this function.
    raise ValueError(f"Unsupported BingX mode for HTTP: {mode}")


def _map_position_side(side: str) -> str:
    """
    Map normalized side to BingX positionSide.
    
    Args:
        side: Normalized side ("long", "short", "buy", "sell")
        
    Returns:
        BingX positionSide ("LONG" or "SHORT")
        
    Raises:
        ValueError: If side is not supported
    """
    s = side.lower()
    if s in ("buy", "long"):
        return "LONG"
    if s in ("sell", "short"):
        return "SHORT"
    raise ValueError(f"Unsupported side for positionSide: {side}")


def build_signed_query(params: Dict[str, Any], secret: str) -> str:
    """
    Build and sign query string for BingX API.
    
    Args:
        params: Dictionary of query parameters
        secret: API secret key for signing
        
    Returns:
        Signed query string with signature parameter appended
    """
    # Add timestamp in ms if not present
    params = dict(params)
    params.setdefault("timestamp", int(time.time() * 1000))
    
    # Sort keys lexicographically
    items = sorted(params.items(), key=lambda kv: kv[0])
    query = urlencode(items, doseq=False)
    
    # Sign with HMAC-SHA256
    signature = hmac.new(
        secret.encode("utf-8"),
        query.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    
    return f"{query}&signature={signature}"


async def bingx_place_order(
    account_config: AccountConfig,
    order: OpenOrderRequest,
) -> Dict[str, Any]:
    """
    Send an order to BingX according to the account mode:
    - mode == "test": Test Order endpoint (no real order)
    - mode == "demo": Demo trading endpoint (VST host, virtual USDT)
    - mode == "live": Real trading endpoint (PROD host)
    
    Args:
        account_config: Account configuration with mode and credentials
        order: OpenOrderRequest with order details
        
    Returns:
        Response data from BingX API
        
    Raises:
        ValueError: If required fields are missing
        httpx.HTTPError: If HTTP request fails
        RuntimeError: If API returns an error code
    """
    import os
    
    # Get credentials from environment (supports numeric scheme with legacy fallback)
    api_key, secret_key = account_config.get_credentials()
    source_key = os.getenv(account_config.source_key_env) if account_config.source_key_env else None
    
    if not api_key or not secret_key:
        raise ValueError(f"Missing API credentials for account {account_config.account_id}")
    
    # Get environment based on mode
    env = get_bingx_env(account_config.mode)
    
    # Convert symbol to BingX format
    symbol = to_bingx_symbol(order.symbol)
    
    # Map logical side / entry_type to BingX fields
    # For now we support only MARKET entry orders
    # Determine if this is an exit order (closing position)
    from common.models.tv_command import TvCommand
    is_exit = order.command in (TvCommand.EXIT_LONG, TvCommand.EXIT_SHORT, TvCommand.EXIT_LONG_ALL, TvCommand.EXIT_SHORT_ALL)
    
    # For entry: long → BUY, short → SELL
    # For exit: long → SELL (close long), short → BUY (close short)
    if is_exit:
        # Flip the side for exit orders
        side = "SELL" if order.side == "long" else "BUY"
    else:
        side = "BUY" if order.side == "long" else "SELL"
    
    order_type = "MARKET" if order.entry_type == "market" else "LIMIT"
    
    # Map positionSide for Hedge mode (same for both entry and exit)
    position_side = _map_position_side(order.side)
    
    quantity = order.quantity
    if quantity is None:
        raise ValueError("BingX order requires quantity; got None")
    
    # Build parameters
    params: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "type": order_type,
        "quantity": quantity,
        "positionSide": position_side,
    }
    
    # For EXIT orders, add reduceOnly flag only when supported by the account (one-way mode)
    if is_exit and account_config.supports_reduce_only:
        params["reduceOnly"] = "true"
    
    # Add price for limit orders
    if order.entry_type == "limit" and order.price is not None:
        params["price"] = order.price
    
    # Add leverage if provided
    if order.leverage is not None:
        params["leverage"] = str(int(order.leverage))
    
    # Build and sign query
    query = build_signed_query(params, secret_key)
    
    # Build URL
    url = f"{env.base_url}{env.order_path}?{query}"
    
    # Build headers
    headers = {
        "X-BX-APIKEY": api_key,
    }
    if source_key:
        headers["X-SOURCE-KEY"] = source_key
    
    # Log request (without secrets)
    logger.info(
        "BingX order request: account=%s mode=%s command=%s symbol=%s side=%s positionSide=%s quantity=%s reduceOnly_applied=%s endpoint=%s",
        account_config.account_id,
        account_config.mode,
        order.command.value,
        symbol,
        side,
        position_side,
        quantity,
        "true" if params.get("reduceOnly") else "false",
        env.order_path,
    )
    
    # Make request
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, headers=headers, content=b"")
        except httpx.HTTPError as e:
            # Log HTTP-level errors with full context
            logger.error(
                "BingX HTTP error: account=%s exchange=bingx command=%s symbol=%s side=%s positionSide=%s quantity=%s leverage=%s margin_type=%s error=%s",
                account_config.account_id,
                order.command.value,
                symbol,
                side,
                position_side,
                quantity,
                order.leverage or "N/A",
                order.margin_type or "N/A",
                str(e),
            )
            raise
        
        # Parse JSON response (even for error status codes to get BingX error details)
        try:
            data = resp.json()
        except Exception:
            # If response is not JSON, use raw text
            data = {"raw_response": resp.text[:500]}
        
        # Log response with full context
        body_str = str(data)
        if len(body_str) > 300:
            body_str = body_str[:300] + "... (truncated)"
        
        if resp.status_code < 400:
            logger.info(
                "BingX response: account=%s exchange=bingx mode=%s command=%s symbol=%s side=%s positionSide=%s status=%s body=%s",
                account_config.account_id,
                account_config.mode,
                order.command.value,
                symbol,
                side,
                position_side,
                resp.status_code,
                body_str,
            )
        else:
            # Log error responses with full context
            error_code = data.get("code", "N/A")
            error_msg = data.get("msg") or data.get("message", "Unknown error")
            logger.error(
                "BingX error response: account=%s exchange=bingx command=%s symbol=%s side=%s positionSide=%s quantity=%s leverage=%s margin_type=%s http_status=%s api_code=%s api_msg=%s body=%s",
                account_config.account_id,
                order.command.value,
                symbol,
                side,
                position_side,
                quantity,
                order.leverage or "N/A",
                order.margin_type or "N/A",
                resp.status_code,
                error_code,
                error_msg,
                body_str,
            )
        
        # Raise for non-2xx HTTP status codes
        resp.raise_for_status()
        
        # Check for API error codes (BingX returns 200 OK even for API errors)
        code = data.get("code")
        if code not in (0, "0", None):
            error_msg = data.get("msg") or data.get("message", "Unknown error")
            api_code_int = int(code) if code is not None else 0
            
            # Handle soft error: "No position to close" (code 101205)
            if api_code_int == 101205:
                logger.warning(
                    "BingX soft error (no position): account=%s exchange=bingx command=%s symbol=%s side=%s positionSide=%s code=101205 msg=%s",
                    account_config.account_id,
                    account_config.exchange,
                    order.command.value,
                    symbol,
                    side,
                    position_side,
                    error_msg,
                )
                raise BingxAPIError(
                    api_code=api_code_int,
                    api_msg=error_msg or "No position to close",
                    is_no_position=True,
                    raw_body=data,
                )
            
            # Hard error for any other non-zero code
            logger.error(
                "BingX API error: account=%s exchange=bingx command=%s symbol=%s side=%s positionSide=%s api_code=%s api_msg=%s",
                account_config.account_id,
                order.command.value,
                symbol,
                side,
                position_side,
                api_code_int,
                error_msg,
            )
            raise BingxAPIError(
                api_code=api_code_int,
                api_msg=error_msg or "Unknown error",
                raw_body=data,
            )
        
        return data

