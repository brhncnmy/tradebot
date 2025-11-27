"""Interactive Telegram login helper for creating session files."""

import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from app.config import TelegramSourceConfig
from app.logging_config import get_logger

logger = get_logger("tg-login")


async def login() -> None:
    """Interactive login flow to create/refresh Telegram session."""
    try:
        config = TelegramSourceConfig.from_env()
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Ensure session directory exists
    config.session_dir.mkdir(parents=True, exist_ok=True)
    
    session_file = config.session_file
    print(f"Session file: {session_file}")
    print(f"Account ID: {config.account_id}")
    
    # Create Telegram client
    client = TelegramClient(str(session_file), config.api_id, config.api_hash)
    
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            print("Not authorized. Starting login flow...")
            
            # Request phone number
            phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
            if not phone:
                print("Error: Phone number is required", file=sys.stderr)
                sys.exit(1)
            
            # Send code request
            print("Sending login code...")
            await client.send_code_request(phone)
            
            # Request code
            code = input("Enter the login code you received: ").strip()
            if not code:
                print("Error: Login code is required", file=sys.stderr)
                sys.exit(1)
            
            try:
                # Sign in with code
                await client.sign_in(phone, code)
                print("Login successful!")
            except SessionPasswordNeededError:
                # 2FA required
                password = input("Enter your 2FA password: ").strip()
                if not password:
                    print("Error: 2FA password is required", file=sys.stderr)
                    sys.exit(1)
                
                await client.sign_in(password=password)
                print("Login successful with 2FA!")
        else:
            print("Already authorized. Session is valid.")
            # Test connection
            me = await client.get_me()
            print(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'no username'})".strip())
        
        print(f"Session saved to: {session_file}")
        
    except Exception as e:
        print(f"Login error: {e}", file=sys.stderr)
        logger.error("Login failed", exc_info=True)
        sys.exit(1)
    finally:
        await client.disconnect()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(login())
    except KeyboardInterrupt:
        print("\nLogin cancelled by user", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


