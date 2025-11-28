"""Main entry point for telegram-source service."""

import asyncio
import signal
import sys
from typing import Optional

from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from app.config import TelegramSourceConfig
from app.logging_config import get_logger
from app.parsers.pocketoption import PocketOptionParser
from app.clients.pocketoption_bot_client import PocketOptionBotClient

logger = get_logger("telegram-source")


class TelegramSourceService:
    """Main service for listening to Telegram channels and parsing signals."""
    
    def __init__(self, config: TelegramSourceConfig):
        """
        Initialize the service.
        
        Args:
            config: Telegram source configuration
        """
        self.config = config
        self.client: Optional[TelegramClient] = None
        self.parser = PocketOptionParser()
        self.bot_client = PocketOptionBotClient(config)
        self._running = False
    
    async def start(self) -> None:
        """Start the Telegram client and begin listening."""
        session_file = self.config.session_file
        
        # Ensure session directory exists
        self.config.session_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Initializing Telegram client",
            extra={
                "session_file": str(session_file),
                "account_id": self.config.account_id,
                "channel_id": self.config.pocketoption_channel_id,
            }
        )
        
        # Create Telegram client
        self.client = TelegramClient(
            str(session_file),
            self.config.api_id,
            self.config.api_hash,
        )
        
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                logger.error(
                    "Telegram client is not authorized. Please run tg-login helper first.",
                    extra={"session_file": str(session_file)}
                )
                raise RuntimeError(
                    f"Session not authorized. Run: scripts/tg_login_telegram_source.sh {self.config.account_id}"
                )
            
            # Verify we can get our own user info
            me = await self.client.get_me()
            logger.info(
                "Telegram client connected and authorized",
                extra={
                    "user_id": me.id,
                    "username": me.username or "no username",
                }
            )
            
            # Register message handler for PocketOption channel
            channel_id = self.config.pocketoption_channel_id
            
            @self.client.on(events.NewMessage(chats=[channel_id]))
            async def handle_new_message(event: events.NewMessage.Event) -> None:
                """Handle new messages from the PocketOption channel."""
                message = event.message
                # Get raw message text
                raw_text = message.text or "(no text)"
                
                logger.info(
                    "Received new message",
                    extra={
                        "message_id": message.id,
                        "channel_id": message.chat_id,
                        "raw_text": raw_text[:200],  # First 200 chars for debugging
                    }
                )
                
                # Parse message
                signal = self.parser.parse(message)
                
                if signal is None:
                    logger.warning(
                        "Failed to parse message as PocketOption signal",
                        extra={"message_id": message.id}
                    )
                    return
                
                # Log structured signal
                logger.info(
                    "Parsed PocketOption signal",
                    extra={
                        "signal_type": signal.signal_type.value,
                        "asset": signal.asset,
                        "duration_minutes": signal.duration_minutes,
                        "direction": signal.direction.value if signal.direction else None,
                        "amount_multiplier": signal.amount_multiplier,
                        "message_id": message.id,
                        "raw_text": signal.raw_text[:200],  # First 200 chars for debugging
                    }
                )
                
                # Send to PocketOption bot (or DRY-RUN)
                await self.bot_client.place_trade(signal)
            
            logger.info(
                "Registered message handler for PocketOption channel",
                extra={"channel_id": channel_id}
            )
            
            self._running = True
            logger.info("Telegram source service started successfully")
            
            # Keep running until interrupted
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error("Failed to start Telegram client", exc_info=True)
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        if self.client:
            await self.client.disconnect()
            logger.info("Telegram client disconnected")
        self._running = False
    
    async def stop(self) -> None:
        """Stop the service gracefully."""
        logger.info("Stopping telegram-source service...")
        self._running = False
        if self.client:
            await self.client.disconnect()


async def main() -> None:
    """Main entry point."""
    try:
        config = TelegramSourceConfig.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    
    service = TelegramSourceService(config)
    
    # Handle graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(service.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error("Service error", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())


