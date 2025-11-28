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
    
    # UI automation settings
    ui_enabled: bool = Field(default=False, description="Enable UI automation")
    login_url: str = Field(default="https://pocketoption.com/en/login/", description="PocketOption login URL")
    username: Optional[str] = Field(default=None, description="PocketOption username")
    password: Optional[str] = Field(default=None, description="PocketOption password")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    
    # UI selectors (all optional, configured via env)
    selector_username: Optional[str] = Field(default=None, description="CSS selector for username input")
    selector_password: Optional[str] = Field(default=None, description="CSS selector for password input")
    selector_login_button: Optional[str] = Field(default=None, description="CSS selector for login button")
    
    # Trading UI selectors
    selector_asset_field: Optional[str] = Field(default=None, description="CSS selector for asset input/select field")
    selector_duration_field: Optional[str] = Field(default=None, description="CSS selector for duration input/select field")
    selector_direction_up: Optional[str] = Field(default=None, description="CSS selector for UP/HIGHER direction button")
    selector_direction_down: Optional[str] = Field(default=None, description="CSS selector for DOWN/LOWER direction button")
    selector_stake_field: Optional[str] = Field(default=None, description="CSS selector for stake/amount input field")
    selector_place_trade_button: Optional[str] = Field(default=None, description="CSS selector for place trade button")

    @classmethod
    def from_env(cls) -> "PocketOptionBotConfig":
        """Load configuration from environment variables."""
        enabled = os.getenv("POCKETOPTION_ENABLED", "true").lower() in ("true", "1", "yes")
        dry_run = os.getenv("POCKETOPTION_DRY_RUN", "true").lower() in ("true", "1", "yes")
        base_stake = float(os.getenv("POCKETOPTION_BASE_STAKE", "1.0"))
        max_stake_str = os.getenv("POCKETOPTION_MAX_STAKE_PER_TRADE")
        max_stake = float(max_stake_str) if max_stake_str else None
        account_type = os.getenv("POCKETOPTION_ACCOUNT_TYPE", "DEMO").upper()
        
        # UI automation settings
        ui_enabled = os.getenv("POCKETOPTION_UI_ENABLED", "false").lower() in ("true", "1", "yes")
        login_url = os.getenv("POCKETOPTION_LOGIN_URL", "https://pocketoption.com/en/login/")
        username = os.getenv("POCKETOPTION_USERNAME")
        password = os.getenv("POCKETOPTION_PASSWORD")
        headless = os.getenv("POCKETOPTION_HEADLESS", "true").lower() in ("true", "1", "yes")
        
        # UI selectors
        selector_username = os.getenv("POCKETOPTION_SELECTOR_USERNAME")
        selector_password = os.getenv("POCKETOPTION_SELECTOR_PASSWORD")
        selector_login_button = os.getenv("POCKETOPTION_SELECTOR_LOGIN_BUTTON")
        
        # Trading UI selectors
        selector_asset_field = os.getenv("POCKETOPTION_SELECTOR_ASSET_FIELD")
        selector_duration_field = os.getenv("POCKETOPTION_SELECTOR_DURATION_FIELD")
        selector_direction_up = os.getenv("POCKETOPTION_SELECTOR_DIRECTION_UP")
        selector_direction_down = os.getenv("POCKETOPTION_SELECTOR_DIRECTION_DOWN")
        selector_stake_field = os.getenv("POCKETOPTION_SELECTOR_STAKE_FIELD")
        selector_place_trade_button = os.getenv("POCKETOPTION_SELECTOR_PLACE_TRADE_BUTTON")

        return cls(
            enabled=enabled,
            dry_run=dry_run,
            base_stake=base_stake,
            max_stake_per_trade=max_stake,
            account_type=account_type,
            ui_enabled=ui_enabled,
            login_url=login_url,
            username=username,
            password=password,
            headless=headless,
            selector_username=selector_username,
            selector_password=selector_password,
            selector_login_button=selector_login_button,
            selector_asset_field=selector_asset_field,
            selector_duration_field=selector_duration_field,
            selector_direction_up=selector_direction_up,
            selector_direction_down=selector_direction_down,
            selector_stake_field=selector_stake_field,
            selector_place_trade_button=selector_place_trade_button,
        )


# Global settings instance
_settings: Optional[PocketOptionBotConfig] = None


def get_settings() -> PocketOptionBotConfig:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = PocketOptionBotConfig.from_env()
    return _settings

