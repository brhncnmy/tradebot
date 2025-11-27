"""HTTP client for PocketOption bot API."""

import httpx
from typing import Optional

from app.config import TelegramSourceConfig
from app.models.pocketoption import PocketOptionSignal
from app.logging_config import get_logger

logger = get_logger("pocketoption-bot-client")


class PocketOptionBotClient:
    """Client for sending PocketOption signals to the bot API."""
    
    def __init__(self, config: TelegramSourceConfig):
        """
        Initialize the client.
        
        Args:
            config: Telegram source configuration
        """
        self.config = config
        self.timeout = 5.0
    
    async def place_trade(self, signal: PocketOptionSignal) -> None:
        """
        Send a PocketOption signal to the bot API.
        
        Args:
            signal: PocketOptionSignal to send
        """
        if not self.config.pocketoption_bot_url:
            logger.info(
                "POCKETOPTION_BOT_URL not configured, skipping HTTP call",
                extra={"signal_type": signal.signal_type.value}
            )
            return
        
        if self.config.dry_run:
            logger.info(
                "DRY-RUN mode: would send signal to PocketOption bot",
                extra={
                    "signal_type": signal.signal_type.value,
                    "signal_asset": signal.asset,
                    "signal_duration_minutes": signal.duration_minutes,
                    "signal_direction": signal.direction.value if signal.direction else None,
                    "signal_amount_multiplier": signal.amount_multiplier,
                    "bot_url": self.config.pocketoption_bot_url,
                }
            )
            return
        
        # Prepare JSON payload matching new schema
        # Direction should be sent as string (will be normalized on bot side)
        direction_str = None
        if signal.direction:
            direction_str = signal.direction.value
        
        payload = {
            "signal_type": signal.signal_type.value,
            "asset": signal.asset,
            "duration_minutes": signal.duration_minutes,
            "direction": direction_str,
            "amount_multiplier": signal.amount_multiplier,
            "raw_message_id": signal.raw_message_id,
            "raw_channel_id": signal.raw_channel_id,
            "raw_text": signal.raw_text,
        }
        
        url = f"{self.config.pocketoption_bot_url.rstrip('/')}/place_trade"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                logger.info(
                    "Successfully sent signal to PocketOption bot",
                    extra={
                        "signal_type": signal.signal_type.value,
                        "status_code": response.status_code,
                    }
                )
        except httpx.HTTPError as e:
            logger.error(
                "Failed to send signal to PocketOption bot",
                extra={
                    "signal_type": signal.signal_type.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                "Unexpected error while sending signal to PocketOption bot",
                extra={
                    "signal_type": signal.signal_type.value,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
