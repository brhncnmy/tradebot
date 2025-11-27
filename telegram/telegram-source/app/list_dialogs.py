"""List all Telegram dialogs/channels for the configured account."""

import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

from app.logging_config import get_logger

logger = get_logger("list-dialogs")


def load_config_for_listing():
    """Load minimal config for listing dialogs (channel_id not required)."""
    import os
    
    api_id = os.getenv("TELEGRAM_API_ID")
    if not api_id:
        raise ValueError("TELEGRAM_API_ID environment variable is required")
    
    api_hash = os.getenv("TELEGRAM_API_HASH")
    if not api_hash:
        raise ValueError("TELEGRAM_API_HASH environment variable is required")
    
    account_id = os.getenv("TELEGRAM_ACCOUNT_ID")
    if not account_id:
        raise ValueError("TELEGRAM_ACCOUNT_ID environment variable is required")
    
    session_dir = Path(os.getenv("TELEGRAM_SESSION_DIR", "/app/telegram/sessions"))
    session_file = session_dir / f"session_{account_id}.session"
    
    return {
        "api_id": int(api_id),
        "api_hash": api_hash,
        "session_file": session_file,
        "account_id": account_id,
    }


async def list_dialogs() -> None:
    """List all dialogs/channels for the configured Telegram account."""
    try:
        config = load_config_for_listing()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        logger.error("Configuration error", extra={"error": str(e)})
        sys.exit(1)
    
    # Ensure session directory exists
    config["session_file"].parent.mkdir(parents=True, exist_ok=True)
    
    session_file = config["session_file"]
    logger.info(
        "Loading Telegram client",
        extra={
            "session_file": str(session_file),
            "account_id": config["account_id"],
        }
    )
    
    # Create Telegram client
    client = TelegramClient(
        str(session_file),
        config["api_id"],
        config["api_hash"],
    )
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            error_msg = (
                f"Telegram client is not authorized. "
                f"Please run: scripts/tg_login_telegram_source.sh {config['account_id']}"
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
        
        print(f"Listing dialogs for: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})".strip())
        print("=" * 80)
        
        # Iterate over all dialogs
        dialog_count = 0
        async for dialog in client.iter_dialogs():
            dialog_count += 1
            
            # Determine dialog type
            entity = dialog.entity
            if isinstance(entity, Channel):
                if entity.megagroup:
                    dialog_type = "supergroup"
                else:
                    dialog_type = "channel"
            elif isinstance(entity, Chat):
                dialog_type = "group"
            elif isinstance(entity, User):
                dialog_type = "user"
            else:
                dialog_type = "unknown"
            
            # Get dialog ID (peer ID)
            dialog_id = dialog.id
            
            # Get title
            title = dialog.name or "No title"
            
            # Get username if available
            username = None
            if isinstance(entity, (Channel, User)):
                username = getattr(entity, "username", None)
            
            # Print in readable format
            username_str = f"@{username}" if username else "N/A"
            print(f"ID={dialog_id} | TYPE={dialog_type} | TITLE=\"{title}\" | USERNAME={username_str}")
        
        print("=" * 80)
        print(f"Total dialogs: {dialog_count}")
        logger.info("Listed all dialogs", extra={"count": dialog_count})
        
    except Exception as e:
        error_msg = f"Error listing dialogs: {e}"
        print(error_msg, file=sys.stderr)
        logger.error("Failed to list dialogs", exc_info=True)
        sys.exit(1)
    finally:
        await client.disconnect()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(list_dialogs())
    except KeyboardInterrupt:
        print("\nListing cancelled by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

