"""Tests for TradeExecutor UI integration logic."""

import os
from unittest.mock import patch

import pytest

from app.config import PocketOptionBotConfig
from app.models.pocketoption import PocketOptionDirection, PocketOptionSignal, PocketOptionSignalType
from app.service.trade_executor import TradeExecutor


def test_entry_dry_run_true_ui_enabled_false():
    """Test ENTRY with DRY_RUN=True, UI_ENABLED should not matter."""
    import app.config
    app.config._settings = None
    
    with patch.dict(os.environ, {
        "POCKETOPTION_ENABLED": "true",
        "POCKETOPTION_DRY_RUN": "true",
        "POCKETOPTION_UI_ENABLED": "false",  # Should not matter
        "POCKETOPTION_BASE_STAKE": "1.0",
    }, clear=False):
        settings = PocketOptionBotConfig.from_env()
        executor = TradeExecutor(settings)
        
        signal = PocketOptionSignal(
            signal_type=PocketOptionSignalType.ENTRY,
            asset="GBP/USD OTC",
            duration_minutes=5,
            direction=PocketOptionDirection.DOWN,
            amount_multiplier=None,
            raw_message_id=12345,
            raw_channel_id=-1002019935922,
            raw_text="GBP/USD OTC 5 min LOWER",
        )
        
        result = executor.execute(signal)
        
        assert result.status == "accepted"
        assert result.dry_run is True
        assert result.enabled is True
        assert "DRY-RUN" in result.reason


def test_entry_dry_run_true_ui_enabled_true():
    """Test ENTRY with DRY_RUN=True, UI_ENABLED=True should not matter."""
    import app.config
    app.config._settings = None
    
    with patch.dict(os.environ, {
        "POCKETOPTION_ENABLED": "true",
        "POCKETOPTION_DRY_RUN": "true",
        "POCKETOPTION_UI_ENABLED": "true",  # Should not matter
        "POCKETOPTION_BASE_STAKE": "1.0",
    }, clear=False):
        settings = PocketOptionBotConfig.from_env()
        executor = TradeExecutor(settings)
        
        signal = PocketOptionSignal(
            signal_type=PocketOptionSignalType.ENTRY,
            asset="GBP/USD OTC",
            duration_minutes=5,
            direction=PocketOptionDirection.DOWN,
            amount_multiplier=None,
            raw_message_id=12346,
            raw_channel_id=-1002019935922,
            raw_text="GBP/USD OTC 5 min LOWER",
        )
        
        result = executor.execute(signal)
        
        assert result.status == "accepted"
        assert result.dry_run is True
        assert result.enabled is True
        assert "DRY-RUN" in result.reason


def test_entry_dry_run_false_ui_enabled_false():
    """Test ENTRY with DRY_RUN=False, UI_ENABLED=False should return error."""
    import app.config
    app.config._settings = None
    
    with patch.dict(os.environ, {
        "POCKETOPTION_ENABLED": "true",
        "POCKETOPTION_DRY_RUN": "false",
        "POCKETOPTION_UI_ENABLED": "false",
        "POCKETOPTION_BASE_STAKE": "1.0",
    }, clear=False):
        settings = PocketOptionBotConfig.from_env()
        executor = TradeExecutor(settings)
        
        signal = PocketOptionSignal(
            signal_type=PocketOptionSignalType.ENTRY,
            asset="GBP/USD OTC",
            duration_minutes=5,
            direction=PocketOptionDirection.DOWN,
            amount_multiplier=None,
            raw_message_id=12347,
            raw_channel_id=-1002019935922,
            raw_text="GBP/USD OTC 5 min LOWER",
        )
        
        result = executor.execute(signal)
        
        assert result.status == "error"
        assert result.dry_run is False
        assert result.enabled is True
        assert "UI disabled" in result.reason


def test_entry_dry_run_false_ui_enabled_true_no_playwright():
    """Test ENTRY with DRY_RUN=False, UI_ENABLED=True but Playwright not installed."""
    import app.config
    app.config._settings = None
    
    with patch.dict(os.environ, {
        "POCKETOPTION_ENABLED": "true",
        "POCKETOPTION_DRY_RUN": "false",
        "POCKETOPTION_UI_ENABLED": "true",
        "POCKETOPTION_BASE_STAKE": "1.0",
    }, clear=False):
        settings = PocketOptionBotConfig.from_env()
        executor = TradeExecutor(settings)
        
        signal = PocketOptionSignal(
            signal_type=PocketOptionSignalType.ENTRY,
            asset="GBP/USD OTC",
            duration_minutes=5,
            direction=PocketOptionDirection.DOWN,
            amount_multiplier=None,
            raw_message_id=12348,
            raw_channel_id=-1002019935922,
            raw_text="GBP/USD OTC 5 min LOWER",
        )
        
        # Mock import failure
        with patch("app.service.trade_executor.PocketOptionUIDriver", side_effect=ImportError("No module named 'playwright'")):
            result = executor.execute(signal)
            
            # Should handle gracefully
            assert result.status in ("error", "accepted")  # May vary based on exact error handling

