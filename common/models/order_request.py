from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from common.models.normalized_signal import Side, TakeProfitLevel
from common.models.tv_command import TvCommand


class AccountRef(BaseModel):
    """Reference to a trading account."""
    exchange: str = Field(..., description="Exchange identifier (e.g., 'bingx')")
    account_id: str = Field(..., description="Account identifier within the exchange")


class OpenOrderRequest(BaseModel):
    """Request to open a new position."""
    account: AccountRef = Field(..., description="Target trading account")
    symbol: str = Field(..., description="Trading symbol")
    side: Optional[Side] = Field(None, description="Position side: 'long' or 'short'")
    entry_type: Literal["market", "limit"] = Field(..., description="Entry order type")
    price: Optional[float] = Field(None, gt=0, description="Entry price (required for limit orders)")
    leverage: Optional[float] = Field(None, gt=0, description="Leverage multiplier")
    quantity: Optional[float] = Field(None, gt=0, description="Position size in base units or contracts")
    stop_loss: Optional[float] = Field(None, gt=0, description="Stop loss price level")
    take_profits: List[TakeProfitLevel] = Field(default_factory=list, description="Take profit levels")
    client_order_id: Optional[str] = Field(None, description="Client-provided order identifier")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    command: TvCommand = Field(..., description="TradingView command for this request")
    margin_type: Optional[str] = Field(None, description="Desired margin type if provided by source")
    tp_close_pct: Optional[float] = Field(None, description="Partial close percentage for EXIT commands")
    raw_payload: Optional[str] = Field(None, description="Original raw payload for debugging")

