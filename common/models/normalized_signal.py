from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from common.models.tv_command import TvCommand

Side = Literal["long", "short"]


class TakeProfitLevel(BaseModel):
    """Take profit level with price and size percentage."""
    price: float = Field(..., gt=0, description="Take profit price level")
    size_pct: float = Field(..., ge=0, le=100, description="Percentage of position to close at this level (0-100)")


class NormalizedSignal(BaseModel):
    """Normalized trading signal from any source."""
    command: TvCommand = Field(..., description="TradingView command (ENTER/EXIT/CANCEL)")
    source: str = Field(..., description="Signal source identifier (e.g., 'tradingview')")
    strategy_name: Optional[str] = Field(None, description="Strategy name that generated the signal")
    symbol: str = Field(..., description="Trading symbol (e.g., 'BTCUSDT', 'BTC-USDT')")
    side: Optional[Side] = Field(None, description="Position side: 'long' or 'short' (may be None for CANCEL)")
    entry_type: Literal["market", "limit"] = Field("limit", description="Entry order type")
    entry_price: Optional[float] = Field(None, gt=0, description="Entry price (required for limit orders)")
    quantity: Optional[float] = Field(None, gt=0, description="Position size in base units or contracts")
    leverage: Optional[float] = Field(None, gt=0, description="Leverage multiplier")
    margin_type: Optional[str] = Field(None, description="Margin type requested by the strategy (e.g., ISOLATED)")
    risk_per_trade_pct: Optional[float] = Field(None, ge=0, le=100, description="Risk percentage per trade")
    tp_close_pct: Optional[float] = Field(
        None, ge=0, le=100, description="Percentage of the position to close for partial exits"
    )
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price level")
    take_profits: List[TakeProfitLevel] = Field(default_factory=list, description="Take profit levels")
    routing_profile: Optional[str] = Field(None, description="Routing profile name for account selection")
    timestamp: Optional[datetime] = Field(None, description="Signal timestamp")
    raw_payload: Optional[str] = Field(None, description="Original raw JSON payload from source")

