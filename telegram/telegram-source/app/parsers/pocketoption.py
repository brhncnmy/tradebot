"""PocketOption message parser."""

import re
from typing import Optional

from telethon.tl.custom.message import Message

from app.models.pocketoption import (
    PocketOptionDirection,
    PocketOptionSignal,
    PocketOptionSignalType,
)
from app.parsers.base import BaseParser
from app.logging_config import get_logger

logger = get_logger("pocketoption-parser")


class PocketOptionParser(BaseParser):
    """Parser for PocketOption signal messages."""
    
    # Compiled regex patterns for performance
    PREPARE_PATTERN = re.compile(r"^Prepare a currency\s+(?P<asset>.+)$", re.IGNORECASE)
    ENTRY_PATTERN = re.compile(r"^(?P<asset>.+?)\s+(?P<duration>\d+)\s*min\s+(?P<direction>LOWER|HIGHER)\b.*$", re.IGNORECASE)
    REPEAT_X2_PATTERN = re.compile(r"Repeat.*Amount\s*x\s*2", re.IGNORECASE | re.DOTALL)
    PROFIT_PATTERN = re.compile(r"^profit\s*👍", re.IGNORECASE)
    LOSS_PATTERN = re.compile(r"^loss\s*👎", re.IGNORECASE)
    
    def parse(self, message: Message) -> Optional[PocketOptionSignal]:
        """
        Parse a Telegram message into a PocketOptionSignal.
        
        Supported patterns:
        1. PREPARE: "Prepare a currency GBP/USD OTC"
        2. ENTRY: "GBP/USD OTC 5 min LOWER 📉"
        3. REPEAT_X2: "🏪 Repeat/ Amount x2\nExpiration & Direction same"
        4. Profit/loss messages are ignored (return None)
        5. Other messages are ignored (return None)
        
        Args:
            message: Telethon message object
            
        Returns:
            PocketOptionSignal if parsing succeeds, None otherwise
        """
        if not message.text:
            logger.debug("Message has no text content", extra={"message_id": message.id})
            return None
        
        text = message.text.strip()
        logger.debug("Parsing message", extra={"message_id": message.id, "text_preview": text[:100]})
        
        # Check for profit/loss messages first (ignore these)
        if self.PROFIT_PATTERN.match(text) or self.LOSS_PATTERN.match(text):
            logger.debug("Ignoring profit/loss message", extra={"message_id": message.id})
            return None
        
        # Try PREPARE pattern
        prepare_match = self.PREPARE_PATTERN.match(text)
        if prepare_match:
            asset = prepare_match.group("asset").strip()
            logger.info(
                "Parsed PREPARE signal",
                extra={"message_id": message.id, "asset": asset}
            )
            return PocketOptionSignal(
                signal_type=PocketOptionSignalType.PREPARE,
                asset=asset,
                duration_minutes=None,
                direction=None,
                amount_multiplier=None,
                raw_message_id=message.id,
                raw_channel_id=message.chat_id if message.chat_id else 0,
                raw_text=text,
            )
        
        # Try ENTRY pattern
        entry_match = self.ENTRY_PATTERN.match(text)
        if entry_match:
            asset = entry_match.group("asset").strip()
            duration_str = entry_match.group("duration")
            direction_str = entry_match.group("direction").upper()
            
            try:
                duration_minutes = int(duration_str)
            except ValueError:
                logger.warning(
                    "Failed to parse duration",
                    extra={"message_id": message.id, "duration": duration_str}
                )
                return None
            
            # Map LOWER/HIGHER to direction enum
            direction = PocketOptionDirection.from_lower_higher(direction_str)
            if direction is None:
                logger.warning(
                    "Invalid direction value",
                    extra={"message_id": message.id, "direction": direction_str}
                )
                return None
            
            logger.info(
                "Parsed ENTRY signal",
                extra={
                    "message_id": message.id,
                    "asset": asset,
                    "duration_minutes": duration_minutes,
                    "direction": direction.value,
                }
            )
            return PocketOptionSignal(
                signal_type=PocketOptionSignalType.ENTRY,
                asset=asset,
                duration_minutes=duration_minutes,
                direction=direction,
                amount_multiplier=None,
                raw_message_id=message.id,
                raw_channel_id=message.chat_id if message.chat_id else 0,
                raw_text=text,
            )
        
        # Try REPEAT_X2 pattern
        if self.REPEAT_X2_PATTERN.search(text):
            logger.info("Parsed REPEAT_X2 signal", extra={"message_id": message.id})
            return PocketOptionSignal(
                signal_type=PocketOptionSignalType.REPEAT_X2,
                asset=None,
                duration_minutes=None,
                direction=None,
                amount_multiplier=2.0,
                raw_message_id=message.id,
                raw_channel_id=message.chat_id if message.chat_id else 0,
                raw_text=text,
            )
        
        # All other messages are ignored
        logger.debug("Ignoring message (no matching pattern)", extra={"message_id": message.id})
        return None
