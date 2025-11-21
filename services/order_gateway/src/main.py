import os
import uuid

from fastapi import FastAPI, HTTPException

from common.models.order_request import OpenOrderRequest
from common.utils.config import get_account
from common.utils.logging import get_logger
from services.order_gateway.src.bingx_client import BingxClient

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
    
    # DRY_RUN mode
    if account_cfg.mode == "DRY_RUN":
        fake_id = f"dryrun-{uuid.uuid4().hex}"
        logger.info(
            f"DRY_RUN order: account_id={account_cfg.account_id}, "
            f"exchange={account_cfg.exchange}, symbol={request.symbol}, "
            f"side={request.side}, entry_type={request.entry_type}, "
            f"quantity={request.quantity}"
        )
        return {
            "status": "accepted",
            "mode": "DRY_RUN",
            "exchange": account_cfg.exchange,
            "order_id": fake_id
        }
    
    # LIVE mode
    elif account_cfg.mode == "LIVE":
        # Read credentials from environment
        api_key = os.getenv(account_cfg.api_key_env or "")
        secret_key = os.getenv(account_cfg.secret_key_env or "")
        source_key = os.getenv(account_cfg.source_key_env) if account_cfg.source_key_env else None
        
        if not api_key or not secret_key:
            logger.error(f"Missing API credentials for account {account_cfg.account_id}")
            raise HTTPException(
                status_code=500,
                detail="Missing API credentials for account"
            )
        
        # Instantiate BingX client
        client = BingxClient(
            api_key=api_key,
            secret_key=secret_key,
            source_key=source_key
        )
        
        try:
            data = await client.create_perpetual_order(request)
            
            # Extract order ID from response
            order_id = data.get("data", {}).get("orderId") or data.get("orderId")
            
            logger.info(
                f"Order placed successfully: account_id={account_cfg.account_id}, "
                f"order_id={order_id}"
            )
            
            return {
                "status": "accepted",
                "mode": account_cfg.mode,
                "exchange": account_cfg.exchange,
                "order_id": order_id,
                "raw": data
            }
        except Exception as e:
            logger.exception(
                "Failed to place BingX order",
                extra={"account_id": account_cfg.account_id}
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to place order on BingX"
            )
    
    # Unsupported mode
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported account mode: {account_cfg.mode}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("services.order_gateway.src.main:app", host="0.0.0.0", port=8002, reload=True)
