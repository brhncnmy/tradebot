"""PocketOption signal model definitions."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PocketOptionDirection(str, Enum):
    """PocketOption trade direction."""
    CALL = "CALL"
    PUT = "PUT"
    UP = "UP"
    DOWN = "DOWN"


@dataclass
class PocketOptionSignal:
    """Parsed PocketOption signal from Telegram message."""
    asset: str
    direction: PocketOptionDirection
    duration_seconds: int
    stake: float
    strategy: Optional[str]
    raw_message_id: int
    raw_channel_id: int
    raw_text: str


