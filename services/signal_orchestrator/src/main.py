import os

import httpx
from fastapi import FastAPI, HTTPException, status

from common.models.normalized_signal import NormalizedSignal
from common.models.order_request import AccountRef, OpenOrderRequest
from common.models.tv_command import TvCommand
from common.utils.config import get_routing_profile
from common.utils.logging import get_logger

app = FastAPI(title="signal-orchestrator")
logger = get_logger("signal-orchestrator")

ORDER_GATEWAY_URL = os.getenv(
    "ORDER_GATEWAY_URL", "http://order-gateway:8002"
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "signal-orchestrator"}


@app.post("/signals")
async def handle_signal(signal: NormalizedSignal):
    """
    Process normalized signal and route to appropriate accounts.
    
    Args:
        signal: NormalizedSignal from source
        
    Returns:
        Response with routing results
    """
    logger.info(f"Received signal: {signal.dict()}")
    
    # Determine routing profile
    profile_name = signal.routing_profile or "default"
    
    try:
        accounts = get_routing_profile(profile_name)
    except ValueError as e:
        logger.error(f"Routing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Enhanced routing logging
    account_ids = [acc.account_id for acc in accounts]
    logger.info(
        "Routing signal: routing_profile=%s accounts=%s command=%s symbol=%s",
        profile_name,
        account_ids,
        signal.command.value,
        signal.symbol,
    )
    
    if len(accounts) == 0:
        logger.warning(
            "No available accounts for routing_profile=%s command=%s symbol=%s - signal will be dropped",
            profile_name,
            signal.command.value,
            signal.symbol,
        )
        return {
            "status": "dropped",
            "routing_profile": profile_name,
            "reason": "no_available_accounts",
            "routed_accounts": 0,
            "results": [],
        }
    
    # Validate minimal requirements
    if signal.command in (TvCommand.ENTER_LONG, TvCommand.ENTER_SHORT):
        if signal.quantity is None or signal.quantity <= 0:
            logger.warning("Missing quantity for ENTER command %s", signal.command.value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity required for ENTER commands"
            )
        if signal.side is None:
            logger.warning("Missing side for ENTER command %s", signal.command.value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="side required for ENTER commands"
            )
    elif signal.command in (TvCommand.EXIT_LONG, TvCommand.EXIT_SHORT):
        # EXIT commands also require quantity (for now, treat as full exit)
        if signal.quantity is None or signal.quantity <= 0:
            logger.warning("Missing quantity for EXIT command %s", signal.command.value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity required for EXIT commands"
            )
        if signal.side is None:
            logger.warning("Missing side for EXIT command %s", signal.command.value)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="side required for EXIT commands"
            )
    
    # Build order requests for each account
    results = []
    for account in accounts:
        order_request = OpenOrderRequest(
            account=AccountRef(
                exchange=account.exchange,
                account_id=account.account_id
            ),
            symbol=signal.symbol,
            side=signal.side,
            entry_type=signal.entry_type,
            price=signal.entry_price,
            leverage=signal.leverage,
            quantity=signal.quantity,
            stop_loss=signal.stop_loss,
            take_profits=signal.take_profits,
            client_order_id=None,
            meta={
                "source": signal.source,
                "strategy_name": signal.strategy_name,
                "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
            },
            command=signal.command,
            margin_type=signal.margin_type,
            tp_close_pct=signal.tp_close_pct,
            raw_payload=signal.raw_payload,
        )
        
        # Forward to order-gateway
        url = f"{ORDER_GATEWAY_URL}/orders/open"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=order_request.dict())
                status = resp.status_code
                try:
                    data = resp.json()
                except ValueError:
                    data = None
                
                if status != 200:
                    logger.error(
                        "Order-gateway HTTP error: account=%s status=%s body=%r",
                        account.account_id,
                        status,
                        data,
                    )
                    results.append({
                        "account_id": account.account_id,
                        "status": "error",
                        "error": f"HTTP {status}",
                        "body": data,
                    })
                    continue
                
                api_code = (data or {}).get("api_code")
                order_status = (data or {}).get("order_status")
                ok = (data or {}).get("ok", False)
                
                if order_status == "no_position" and api_code == 101205:
                    logger.info(
                        "No position to close on BingX; treating as no-op: account=%s symbol=%s api_code=%s api_msg=%s",
                        account.account_id,
                        signal.symbol,
                        api_code,
                        (data or {}).get("api_msg"),
                    )
                    results.append({
                        "account_id": account.account_id,
                        "status": 200,
                        "result": data,
                    })
                    continue
                
                if not ok:
                    logger.error(
                        "Order-gateway reported error: account=%s order_status=%s api_code=%s api_msg=%s",
                        account.account_id,
                        order_status,
                        api_code,
                        (data or {}).get("api_msg"),
                    )
                    results.append({
                        "account_id": account.account_id,
                        "status": "error",
                        "error": (data or {}).get("api_msg", "Unknown error"),
                        "api_code": api_code,
                    })
                    continue
                
                logger.info(
                    "Order forwarded successfully: account=%s symbol=%s order_status=%s api_code=%s",
                    account.account_id,
                    signal.symbol,
                    order_status or "ok",
                    api_code,
                )
                results.append({
                    "account_id": account.account_id,
                    "status": status,
                    "result": data,
                })
            except httpx.HTTPError as e:
                logger.error(f"Failed to forward order for {account.account_id}: {e}")
                results.append({
                    "account_id": account.account_id,
                    "status": "error",
                    "error": str(e)
                })
    
    return {
        "status": "processed",
        "routed_accounts": len(accounts),
        "results": results
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)

