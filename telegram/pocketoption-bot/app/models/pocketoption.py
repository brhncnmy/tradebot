"""PocketOption signal models for HTTP API."""

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PocketOptionSignalType(str, Enum):
    """PocketOption signal type."""
    PREPARE = "PREPARE"
    ENTRY = "ENTRY"
    REPEAT_X2 = "REPEAT_X2"


class PocketOptionDirection(str, Enum):
    """PocketOption trade direction."""
    UP = "UP"
    DOWN = "DOWN"
    CALL = "CALL"
    PUT = "PUT"
    LOWER = "LOWER"
    HIGHER = "HIGHER"
    
    @classmethod
    def normalize(cls, value: str) -> Optional["PocketOptionDirection"]:
        """
        Normalize direction string to enum value.
        
        Maps:
        - LOWER -> DOWN
        - HIGHER -> UP
        - If already an enum value, return it directly
        """
        if not value:
            return None
        
        value_upper = value.upper().strip()
        
        # Direct enum match
        try:
            return cls(value_upper)
        except ValueError:
            pass
        
        # Map LOWER/HIGHER
        if value_upper == "LOWER":
            return cls.DOWN
        elif value_upper == "HIGHER":
            return cls.UP
        
        return None


class PocketOptionSignal(BaseModel):
    """PocketOption signal received via HTTP API."""
    signal_type: PocketOptionSignalType
    asset: Optional[str] = None
    duration_minutes: Optional[int] = None
    direction: Optional[str] = None  # Accept string, will be normalized
    amount_multiplier: Optional[float] = None
    raw_message_id: int
    raw_channel_id: int
    raw_text: str
    
    @field_validator("direction", mode="before")
    @classmethod
    def normalize_direction(cls, v):
        """Normalize direction string to enum value."""
        if v is None:
            return None
        if isinstance(v, PocketOptionDirection):
            return v
        normalized = PocketOptionDirection.normalize(str(v))
        return normalized if normalized else v
    
    @property
    def normalized_direction(self) -> Optional[PocketOptionDirection]:
        """Get normalized direction enum value."""
        if self.direction is None:
            return None
        if isinstance(self.direction, PocketOptionDirection):
            return self.direction
        return PocketOptionDirection.normalize(str(self.direction))


class TradeResult(BaseModel):
    """Result of trade execution attempt."""
    status: Literal["accepted", "skipped", "error"]
    reason: Optional[str] = None
    dry_run: bool
    enabled: bool

