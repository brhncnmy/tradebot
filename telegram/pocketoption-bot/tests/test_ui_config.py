"""Tests for UI configuration."""

import os
from unittest.mock import patch

import pytest

from app.config import PocketOptionBotConfig, get_settings


def test_ui_config_defaults():
    """Test that UI config fields exist with correct defaults."""
    # Clear any existing settings instance
    import app.config
    app.config._settings = None
    
    # Test with minimal env (no UI vars set)
    with patch.dict(os.environ, {}, clear=False):
        settings = PocketOptionBotConfig.from_env()
        
        # Check UI defaults
        assert settings.ui_enabled is False
        assert settings.login_url == "https://pocketoption.com/en/login/"
        assert settings.username is None
        assert settings.password is None
        assert settings.headless is True
        assert settings.selector_username is None
        assert settings.selector_password is None
        assert settings.selector_login_button is None


def test_ui_config_from_env():
    """Test loading UI config from environment variables."""
    # Clear any existing settings instance
    import app.config
    app.config._settings = None
    
    env_vars = {
        "POCKETOPTION_UI_ENABLED": "true",
        "POCKETOPTION_LOGIN_URL": "https://test.example.com/login",
        "POCKETOPTION_USERNAME": "testuser",
        "POCKETOPTION_PASSWORD": "testpass",
        "POCKETOPTION_HEADLESS": "false",
        "POCKETOPTION_SELECTOR_USERNAME": "#username",
        "POCKETOPTION_SELECTOR_PASSWORD": "#password",
        "POCKETOPTION_SELECTOR_LOGIN_BUTTON": "#login-btn",
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        settings = PocketOptionBotConfig.from_env()
        
        assert settings.ui_enabled is True
        assert settings.login_url == "https://test.example.com/login"
        assert settings.username == "testuser"
        assert settings.password == "testpass"
        assert settings.headless is False
        assert settings.selector_username == "#username"
        assert settings.selector_password == "#password"
        assert settings.selector_login_button == "#login-btn"


def test_ui_config_existing_fields_unchanged():
    """Test that existing config fields are not affected by UI additions."""
    # Clear any existing settings instance
    import app.config
    app.config._settings = None
    
    with patch.dict(os.environ, {}, clear=False):
        settings = PocketOptionBotConfig.from_env()
        
        # Verify existing fields still work
        assert settings.enabled is True  # default
        assert settings.dry_run is True  # default
        assert settings.base_stake == 1.0
        assert settings.max_stake_per_trade is None
        assert settings.account_type == "DEMO"


def test_login_manual_wait_and_trading_root_defaults():
    """Test that login manual wait and trading root selector have correct defaults."""
    # Clear any existing settings instance
    import app.config
    app.config._settings = None
    
    with patch.dict(os.environ, {}, clear=False):
        settings = PocketOptionBotConfig.from_env()
        
        # Check defaults
        assert settings.login_manual_wait_seconds > 0
        assert isinstance(settings.login_manual_wait_seconds, int)
        assert settings.login_manual_wait_seconds == 45  # default value
        assert settings.selector_trading_root
        assert settings.selector_trading_root == "#bar-chart"  # default value

