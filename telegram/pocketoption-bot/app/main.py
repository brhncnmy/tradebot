"""Main entry point for pocketoption-bot HTTP API service."""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.logging_config import get_logger
from app.models.pocketoption import PocketOptionSignal, TradeResult
from app.service.trade_executor import TradeExecutor

app = FastAPI(title="pocketoption-bot")
logger = get_logger("pocketoption-bot")

# Initialize settings and executor
settings = get_settings()
executor = TradeExecutor(settings)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "enabled": settings.enabled,
        "dry_run": settings.dry_run,
    }


@app.post("/place_trade")
async def place_trade(signal: PocketOptionSignal) -> TradeResult:
    """
    Place a PocketOption trade based on a signal.
    
    Args:
        signal: PocketOptionSignal from telegram-source
        
    Returns:
        TradeResult indicating the outcome
    """
    logger.info(
        "Received trade request",
        extra={
            "signal_type": signal.signal_type.value,
            "asset": signal.asset,
            "duration_minutes": signal.duration_minutes,
            "direction": signal.direction,
            "amount_multiplier": signal.amount_multiplier,
            "message_id": signal.raw_message_id,
        }
    )
    
    # Execute the trade
    result = executor.execute(signal)
    
    # Map result to HTTP response
    if result.status == "error":
        logger.error(
            "Trade execution error",
            extra={
                "reason": result.reason,
                "signal_type": signal.signal_type.value,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.reason or "Trade execution error",
        )
    
    # Return successful result (accepted or skipped)
    logger.info(
        "Trade request processed",
        extra={
            "status": result.status,
            "reason": result.reason,
            "dry_run": result.dry_run,
            "signal_type": signal.signal_type.value,
        }
    )
    
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)

