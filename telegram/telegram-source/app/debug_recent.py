"""Debug tool to parse the last 10 messages from PocketOption channel."""

import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient

from app.config import TelegramSourceConfig
from app.logging_config import get_logger
from app.parsers.pocketoption import PocketOptionParser

logger = get_logger("debug-recent")


async def debug_recent() -> None:
    """Fetch and parse the last 10 messages from PocketOption channel."""
    try:
        config = TelegramSourceConfig.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        logger.error("Configuration error", extra={"error": str(e)})
        sys.exit(1)
    
    # Ensure session directory exists
    config.session_dir.mkdir(parents=True, exist_ok=True)
    
    session_file = config.session_file
    logger.info(
        "Loading Telegram client",
        extra={
            "session_file": str(session_file),
            "account_id": config.account_id,
            "channel_id": config.pocketoption_channel_id,
        }
    )
    
    # Create Telegram client
    client = TelegramClient(
        str(session_file),
        config.api_id,
        config.api_hash,
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            error_msg = (
                f"Telegram client is not authorized. "
                f"Please run: scripts/tg_login_telegram_source.sh {config.account_id}"
            )
            print(error_msg, file=sys.stderr)
            logger.error("Client not authorized", extra={"session_file": str(session_file)})
            sys.exit(1)
        
        # Verify we can get our own user info
        me = await client.get_me()
        logger.info(
            "Telegram client connected and authorized",
            extra={
                "user_id": me.id,
                "username": me.username or "no username",
            }
        )
        
        # Get the channel entity
        channel_id = config.pocketoption_channel_id
        try:
            entity = await client.get_entity(channel_id)
        except Exception as e:
            print(f"Error: Could not access channel {channel_id}: {e}", file=sys.stderr)
            logger.error("Failed to access channel", extra={"channel_id": channel_id}, exc_info=True)
            sys.exit(1)
        
        print(f"Fetching last 10 messages from channel: {entity.title or channel_id}")
        print("=" * 80)
        
        # Fetch last 10 messages (newest first)
        messages = await client.get_messages(entity, limit=10)
        
        if not messages:
            print("No messages found in channel.")
            return
        
        # Reverse to show oldest first
        messages = list(reversed(messages))
        
        parser = PocketOptionParser()
        
        for idx, message in enumerate(messages, 1):
            msg_id = message.id
            raw_text = message.text or "(no text)"
            
            # Parse the message
            signal = parser.parse(message)
            
            # Print result
            print(f"\n[{idx}/10] msg_id={msg_id} RAW=\"{raw_text[:60]}{'...' if len(raw_text) > 60 else ''}\"")
            
            if signal is None:
                print("  -> IGNORED (no signal)")
            else:
                # Format signal details
                details = []
                details.append(f"type={signal.signal_type.value}")
                if signal.asset:
                    details.append(f"asset=\"{signal.asset}\"")
                if signal.duration_minutes is not None:
                    details.append(f"duration_minutes={signal.duration_minutes}")
                if signal.direction:
                    details.append(f"direction={signal.direction.value}")
                if signal.amount_multiplier is not None:
                    details.append(f"amount_multiplier={signal.amount_multiplier}")
                
                print(f"  -> SIGNAL {' '.join(details)}")
        
        print("\n" + "=" * 80)
        print(f"Total messages processed: {len(messages)}")
        logger.info("Debug recent completed", extra={"message_count": len(messages)})
        
    except Exception as e:
        error_msg = f"Error: {e}"
        print(error_msg, file=sys.stderr)
        logger.error("Failed to debug recent messages", exc_info=True)
        sys.exit(1)
    finally:
        await client.disconnect()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(debug_recent())
    except KeyboardInterrupt:
        print("\nDebug cancelled by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

