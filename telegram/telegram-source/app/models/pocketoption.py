"""PocketOption signal model definitions."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PocketOptionSignalType(str, Enum):
    """PocketOption signal type."""
    PREPARE = "PREPARE"
    ENTRY = "ENTRY"
    REPEAT_X2 = "REPEAT_X2"


class PocketOptionDirection(str, Enum):
    """PocketOption trade direction."""
    CALL = "CALL"
    PUT = "PUT"
    UP = "UP"
    DOWN = "DOWN"
    LOWER = "LOWER"
    HIGHER = "HIGHER"
    
    @classmethod
    def from_lower_higher(cls, text: str) -> Optional["PocketOptionDirection"]:
        """Map LOWER/HIGHER to DOWN/UP."""
        text_upper = text.upper().strip()
        if text_upper == "LOWER":
            return cls.DOWN
        elif text_upper == "HIGHER":
            return cls.UP
        return None


@dataclass
class PocketOptionSignal:
    """Parsed PocketOption signal from Telegram message."""
    signal_type: PocketOptionSignalType
    asset: Optional[str] = None
    duration_minutes: Optional[int] = None
    direction: Optional[PocketOptionDirection] = None
    amount_multiplier: Optional[float] = None
    raw_message_id: int = 0
    raw_channel_id: int = 0
    raw_text: str = ""
