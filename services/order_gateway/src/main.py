import os
import uuid

from fastapi import FastAPI, HTTPException

from common.models.order_request import OpenOrderRequest
from common.utils.config import get_account
from common.utils.logging import get_logger
from services.order_gateway.src.exchanges.bingx_client import bingx_place_order

app = FastAPI(title="order-gateway")
logger = get_logger("order-gateway")


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
    import os
    api_key = os.getenv(account_cfg.api_key_env or "")
    secret_key = os.getenv(account_cfg.secret_key_env or "")
    
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
    except Exception as e:
        logger.exception(
            f"BingX order failed: mode={mode}, account_id={account_cfg.account_id}, "
            f"symbol={request.symbol}, side={request.side}, quantity={request.quantity}, "
            f"error={e}"
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to place order on BingX"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.order_gateway.src.main:app", host="0.0.0.0", port=8002, reload=True)
