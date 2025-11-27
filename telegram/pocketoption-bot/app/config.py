"""Configuration for pocketoption-bot service."""

import os
from typing import Optional

from pydantic import BaseModel, Field


class PocketOptionBotConfig(BaseModel):
    """PocketOption bot service configuration."""
    enabled: bool = Field(default=True, description="Enable PocketOption bot")
    dry_run: bool = Field(default=True, description="Enable DRY-RUN mode (no actual trades)")
    base_stake: float = Field(default=1.0, description="Base stake amount per trade")
    max_stake_per_trade: Optional[float] = Field(default=None, description="Maximum stake per trade (clamp if exceeded)")
    account_type: str = Field(default="DEMO", description="Account type: DEMO or LIVE")

    @classmethod
    def from_env(cls) -> "PocketOptionBotConfig":
        """Load configuration from environment variables."""
        enabled = os.getenv("POCKETOPTION_ENABLED", "true").lower() in ("true", "1", "yes")
        dry_run = os.getenv("POCKETOPTION_DRY_RUN", "true").lower() in ("true", "1", "yes")
        base_stake = float(os.getenv("POCKETOPTION_BASE_STAKE", "1.0"))
        max_stake_str = os.getenv("POCKETOPTION_MAX_STAKE_PER_TRADE")
        max_stake = float(max_stake_str) if max_stake_str else None
        account_type = os.getenv("POCKETOPTION_ACCOUNT_TYPE", "DEMO").upper()

        return cls(
            enabled=enabled,
            dry_run=dry_run,
            base_stake=base_stake,
            max_stake_per_trade=max_stake,
            account_type=account_type,
        )


# Global settings instance
_settings: Optional[PocketOptionBotConfig] = None


def get_settings() -> PocketOptionBotConfig:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = PocketOptionBotConfig.from_env()
    return _settings

