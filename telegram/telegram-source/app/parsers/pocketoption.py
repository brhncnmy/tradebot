"""PocketOption message parser."""

import re
from typing import Optional

from telethon.tl.custom.message import Message

from app.models.pocketoption import PocketOptionDirection, PocketOptionSignal
from app.parsers.base import BaseParser
from app.logging_config import get_logger

logger = get_logger("pocketoption-parser")


class PocketOptionParser(BaseParser):
    """Parser for PocketOption signal messages."""
    
    # Compiled regex patterns for performance
    ASSET_PATTERN = re.compile(r"asset:\s*([A-Z0-9]+)", re.IGNORECASE)
    DIRECTION_PATTERN = re.compile(r"direction:\s*(CALL|PUT|UP|DOWN)", re.IGNORECASE)
    DURATION_PATTERN = re.compile(r"duration:\s*(\d+)\s*([mM])", re.IGNORECASE)
    # Match "Amount: $5", "Amount: 5$", "$5", "5$" (must have $ or "Amount:" prefix to avoid matching duration)
    # Look for "amount:" label OR standalone "$" or "$" at end
    AMOUNT_PATTERN = re.compile(r"(?:amount:\s*)?\$?(\d+(?:\.\d+)?)\$?(?:\s|$)", re.IGNORECASE)
    STRATEGY_PATTERN = re.compile(r"strategy:\s*(.+?)(?:\n|$)", re.IGNORECASE | re.DOTALL)
    
    def parse(self, message: Message) -> Optional[PocketOptionSignal]:
        """
        Parse a Telegram message into a PocketOptionSignal.
        
        Expected format:
        PO SIGNAL
        Asset: EURUSD
        Direction: CALL
        Duration: 1m
        Amount: 5$
        Strategy: LondonBreakout
        
        Args:
            message: Telethon message object
            
        Returns:
            PocketOptionSignal if parsing succeeds, None otherwise
        """
        if not message.text:
            logger.warning("Message has no text content", extra={"message_id": message.id})
            return None
        
        text = message.text.strip()
        logger.debug("Parsing message", extra={"message_id": message.id, "text_preview": text[:100]})
        
        # Extract asset
        asset_match = self.ASSET_PATTERN.search(text)
        if not asset_match:
            logger.warning("Failed to parse asset from message", extra={"message_id": message.id})
            return None
        asset = asset_match.group(1).strip().upper()
        
        # Extract direction
        direction_match = self.DIRECTION_PATTERN.search(text)
        if not direction_match:
            logger.warning("Failed to parse direction from message", extra={"message_id": message.id})
            return None
        
        direction_str = direction_match.group(1).upper()
        try:
            direction = PocketOptionDirection(direction_str)
        except ValueError:
            logger.warning(
                "Invalid direction value",
                extra={"message_id": message.id, "direction": direction_str}
            )
            return None
        
        # Extract duration
        duration_match = self.DURATION_PATTERN.search(text)
        if not duration_match:
            logger.warning("Failed to parse duration from message", extra={"message_id": message.id})
            return None
        
        duration_value = int(duration_match.group(1))
        duration_unit = duration_match.group(2).upper()
        
        if duration_unit == "M":
            duration_seconds = duration_value * 60
        else:
            logger.warning(
                "Unsupported duration unit",
                extra={"message_id": message.id, "unit": duration_unit}
            )
            return None
        
        # Extract amount/stake - search after duration to avoid matching duration value
        # Look for "Amount:" label first, then try standalone patterns
        amount_match = None
        amount_value = None
        
        # First try with "Amount:" label (most reliable)
        amount_label_match = re.search(r"amount:\s*\$?(\d+(?:\.\d+)?)\$?", text, re.IGNORECASE)
        if amount_label_match:
            amount_value = amount_label_match.group(1)
        else:
            # Try standalone "$X" or "X$" patterns (but not part of duration like "1m")
            # Look for $ followed by digits, or digits followed by $, but not "Xm" pattern
            standalone_amount_match = re.search(r"(?:^|\s)(\$(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\$)(?:\s|$)", text, re.IGNORECASE | re.MULTILINE)
            if standalone_amount_match:
                # Extract the number part (either group 2 or group 3)
                amount_value = standalone_amount_match.group(2) or standalone_amount_match.group(3)
            else:
                # Last resort: look for a number on its own line after duration (but not the duration value itself)
                # Find duration position first
                duration_pos = duration_match.end()
                # Look for a number after duration that's not followed by 'm'
                remaining_text = text[duration_pos:]
                number_match = re.search(r"(?:^|\s)(\d+(?:\.\d+)?)(?:\s|$)", remaining_text, re.IGNORECASE | re.MULTILINE)
                if number_match:
                    # Verify it's not part of another pattern
                    num_str = number_match.group(1)
                    num_pos = number_match.start()
                    # Check if it's followed by 'm' (would be duration) or is part of asset/direction
                    if num_pos + len(num_str) < len(remaining_text):
                        next_char = remaining_text[num_pos + len(num_str):num_pos + len(num_str) + 1].strip()
                        if next_char != 'm' and next_char != 'M':
                            amount_value = num_str
        
        if not amount_value:
            logger.warning("Failed to parse amount from message", extra={"message_id": message.id})
            return None
        
        try:
            stake = float(amount_value)
        except ValueError:
            logger.warning(
                "Failed to convert amount to float",
                extra={"message_id": message.id, "amount": amount_value}
            )
            return None
        
        # Extract strategy (optional)
        strategy_match = self.STRATEGY_PATTERN.search(text)
        strategy = strategy_match.group(1).strip() if strategy_match else None
        
        signal = PocketOptionSignal(
            asset=asset,
            direction=direction,
            duration_seconds=duration_seconds,
            stake=stake,
            strategy=strategy,
            raw_message_id=message.id,
            raw_channel_id=message.chat_id if message.chat_id else 0,
            raw_text=text,
        )
        
        logger.info(
            "Successfully parsed PocketOption signal",
            extra={
                "message_id": message.id,
                "asset": asset,
                "direction": direction.value,
                "duration_seconds": duration_seconds,
                "stake": stake,
                "strategy": strategy,
            }
        )
        
        return signal

