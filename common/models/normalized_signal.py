from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Side = Literal["long", "short"]


class TakeProfitLevel(BaseModel):
    """Take profit level with price and size percentage."""
    price: float = Field(..., gt=0, description="Take profit price level")
    size_pct: float = Field(..., ge=0, le=100, description="Percentage of position to close at this level (0-100)")


class NormalizedSignal(BaseModel):
    """Normalized trading signal from any source."""
    source: str = Field(..., description="Signal source identifier (e.g., 'tradingview')")
    strategy_name: Optional[str] = Field(None, description="Strategy name that generated the signal")
    symbol: str = Field(..., description="Trading symbol (e.g., 'BTCUSDT', 'BTC-USDT')")
    side: Side = Field(..., description="Position side: 'long' or 'short'")
    entry_type: Literal["market", "limit"] = Field("limit", description="Entry order type")
    entry_price: Optional[float] = Field(None, gt=0, description="Entry price (required for limit orders)")
    quantity: Optional[float] = Field(None, gt=0, description="Position size in base units or contracts")
    leverage: Optional[float] = Field(None, gt=0, description="Leverage multiplier")
    risk_per_trade_pct: Optional[float] = Field(None, ge=0, le=100, description="Risk percentage per trade")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price level")
    take_profits: List[TakeProfitLevel] = Field(default_factory=list, description="Take profit levels")
    routing_profile: Optional[str] = Field(None, description="Routing profile name for account selection")
    timestamp: Optional[datetime] = Field(None, description="Signal timestamp")
    raw_payload: Optional[Dict] = Field(None, description="Original raw payload from source")

