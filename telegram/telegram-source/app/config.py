"""Configuration for telegram-source service."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TelegramSourceConfig(BaseModel):
    """Telegram source service configuration."""
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API hash")
    account_id: str = Field(..., description="Telegram account identifier (e.g., ta01)")
    pocketoption_channel_id: str | int = Field(..., description="PocketOption channel ID")
    session_dir: Path = Field(default=Path("/app/telegram/sessions"), description="Session directory path")
    pocketoption_bot_url: Optional[str] = Field(default=None, description="PocketOption bot HTTP API URL")
    dry_run: bool = Field(default=True, description="Enable DRY-RUN mode (no actual HTTP calls)")

    @field_validator("api_id", mode="before")
    @classmethod
    def parse_api_id(cls, v):
        """Parse API ID from string if needed."""
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("pocketoption_channel_id", mode="before")
    @classmethod
    def parse_channel_id(cls, v):
        """Parse channel ID, keeping as string or int."""
        if isinstance(v, str) and v.lstrip("-").isdigit():
            return int(v)
        return v

    @field_validator("session_dir", mode="before")
    @classmethod
    def parse_session_dir(cls, v):
        """Parse session directory path."""
        if isinstance(v, str):
            return Path(v)
        return v

    @property
    def session_file(self) -> Path:
        """Get session file path."""
        return self.session_dir / f"session_{self.account_id}.session"

    @classmethod
    def from_env(cls) -> "TelegramSourceConfig":
        """Load configuration from environment variables."""
        api_id = os.getenv("TELEGRAM_API_ID")
        if not api_id:
            raise ValueError("TELEGRAM_API_ID environment variable is required")
        
        api_hash = os.getenv("TELEGRAM_API_HASH")
        if not api_hash:
            raise ValueError("TELEGRAM_API_HASH environment variable is required")
        
        account_id = os.getenv("TELEGRAM_ACCOUNT_ID")
        if not account_id:
            raise ValueError("TELEGRAM_ACCOUNT_ID environment variable is required")
        
        channel_id = os.getenv("TELEGRAM_POCKETOPTION_CHANNEL_ID")
        if not channel_id:
            raise ValueError("TELEGRAM_POCKETOPTION_CHANNEL_ID environment variable is required")
        
        session_dir = os.getenv("TELEGRAM_SESSION_DIR", "/app/telegram/sessions")
        bot_url = os.getenv("POCKETOPTION_BOT_URL")
        dry_run = os.getenv("POCKETOPTION_DRY_RUN", "true").lower() in ("true", "1", "yes")

        return cls(
            api_id=int(api_id),
            api_hash=api_hash,
            account_id=account_id,
            pocketoption_channel_id=channel_id,
            session_dir=Path(session_dir),
            pocketoption_bot_url=bot_url,
            dry_run=dry_run,
        )


