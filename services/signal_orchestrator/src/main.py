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
    logger.info(f"Using routing profile: {profile_name}")
    
    try:
        accounts = get_routing_profile(profile_name)
    except ValueError as e:
        logger.error(f"Routing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    logger.info(f"Routed to {len(accounts)} account(s)")
    logger.info(f"Orchestrator: routing command={signal.command.value} symbol={signal.symbol} qty={signal.quantity}")
    
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
                response = await client.post(url, json=order_request.dict())
                response.raise_for_status()
                result = response.json()
                logger.info(f"Order forwarded to gateway for {account.account_id}, status: {response.status_code}")
                results.append({
                    "account_id": account.account_id,
                    "status": response.status_code,
                    "result": result
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

