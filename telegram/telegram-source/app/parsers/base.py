"""Base parser interface for Telegram message parsers."""

from abc import ABC, abstractmethod
from typing import Optional

from telethon.tl.custom.message import Message

from app.models.pocketoption import PocketOptionSignal


class BaseParser(ABC):
    """Abstract base class for message parsers."""
    
    @abstractmethod
    def parse(self, message: Message) -> Optional[PocketOptionSignal]:
        """
        Parse a Telegram message into a PocketOptionSignal.
        
        Args:
            message: Telethon message object
            
        Returns:
            PocketOptionSignal if parsing succeeds, None otherwise
        """
        ...


