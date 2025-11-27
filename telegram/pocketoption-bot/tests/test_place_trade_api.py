"""Tests for /place_trade API endpoint."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def default_settings():
    """Patch settings with defaults."""
    with patch("app.main.get_settings") as mock_get_settings:
        from app.config import PocketOptionBotConfig
        mock_get_settings.return_value = PocketOptionBotConfig(
            enabled=True,
            dry_run=True,
            base_stake=1.0,
            max_stake_per_trade=None,
            account_type="DEMO",
        )
        yield mock_get_settings


def test_health_endpoint(client):
    """Test /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "enabled" in data
    assert "dry_run" in data


def test_place_trade_prepare(client, default_settings):
    """Test POST /place_trade with PREPARE signal."""
    payload = {
        "signal_type": "PREPARE",
        "asset": "GBP/USD OTC",
        "duration_minutes": None,
        "direction": None,
        "amount_multiplier": None,
        "raw_message_id": 12345,
        "raw_channel_id": -1002019935922,
        "raw_text": "Prepare a currency GBP/USD OTC",
    }
    
    response = client.post("/place_trade", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "accepted"
    assert "prepare" in data["reason"].lower()
    assert data["dry_run"] is True
    assert data["enabled"] is True


def test_place_trade_entry_lower(client, default_settings):
    """Test POST /place_trade with ENTRY signal (LOWER direction)."""
    payload = {
        "signal_type": "ENTRY",
        "asset": "GBP/USD OTC",
        "duration_minutes": 5,
        "direction": "LOWER",
        "amount_multiplier": None,
        "raw_message_id": 12346,
        "raw_channel_id": -1002019935922,
        "raw_text": "GBP/USD OTC 5 min LOWER 📉",
    }
    
    response = client.post("/place_trade", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "accepted"
    assert "dry-run" in data["reason"].lower() or "dry_run" in data["reason"].lower()
    assert data["dry_run"] is True
    assert data["enabled"] is True


def test_place_trade_entry_down(client, default_settings):
    """Test POST /place_trade with ENTRY signal (DOWN direction)."""
    payload = {
        "signal_type": "ENTRY",
        "asset": "EUR/USD",
        "duration_minutes": 10,
        "direction": "DOWN",
        "amount_multiplier": None,
        "raw_message_id": 12347,
        "raw_channel_id": -1002019935922,
        "raw_text": "EUR/USD 10 min DOWN",
    }
    
    response = client.post("/place_trade", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "accepted"
    assert data["dry_run"] is True


def test_place_trade_repeat_x2(client, default_settings):
    """Test POST /place_trade with REPEAT_X2 signal."""
    payload = {
        "signal_type": "REPEAT_X2",
        "asset": None,
        "duration_minutes": None,
        "direction": None,
        "amount_multiplier": 2.0,
        "raw_message_id": 12348,
        "raw_channel_id": -1002019935922,
        "raw_text": "🏪 Repeat/ Amount x2\nExpiration & Direction same",
    }
    
    response = client.post("/place_trade", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "accepted"
    assert "repeat" in data["reason"].lower()
    assert data["dry_run"] is True
    assert data["enabled"] is True


def test_place_trade_invalid_signal_type(client, default_settings):
    """Test POST /place_trade with invalid signal type."""
    payload = {
        "signal_type": "INVALID_TYPE",
        "asset": "GBP/USD OTC",
        "duration_minutes": 5,
        "direction": "LOWER",
        "amount_multiplier": None,
        "raw_message_id": 12349,
        "raw_channel_id": -1002019935922,
        "raw_text": "Invalid signal",
    }
    
    response = client.post("/place_trade", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_place_trade_missing_required_fields(client, default_settings):
    """Test POST /place_trade with missing required fields."""
    payload = {
        "signal_type": "ENTRY",
        # Missing required fields like raw_message_id, raw_channel_id, raw_text
    }
    
    response = client.post("/place_trade", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_place_trade_disabled_bot(client):
    """Test POST /place_trade when bot is disabled."""
    with patch("app.main.get_settings") as mock_get_settings:
        from app.config import PocketOptionBotConfig
        mock_get_settings.return_value = PocketOptionBotConfig(
            enabled=False,
            dry_run=True,
            base_stake=1.0,
            max_stake_per_trade=None,
            account_type="DEMO",
        )
        
        # Recreate executor with disabled config
        from app.service.trade_executor import TradeExecutor
        executor = TradeExecutor(mock_get_settings.return_value)
        
        with patch("app.main.executor", executor):
            payload = {
                "signal_type": "ENTRY",
                "asset": "GBP/USD OTC",
                "duration_minutes": 5,
                "direction": "LOWER",
                "amount_multiplier": None,
                "raw_message_id": 12350,
                "raw_channel_id": -1002019935922,
                "raw_text": "GBP/USD OTC 5 min LOWER",
            }
            
            response = client.post("/place_trade", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "skipped"
            assert data["enabled"] is False
            assert "disabled" in data["reason"].lower()


def test_place_trade_max_stake_clamping(client):
    """Test POST /place_trade with max_stake_per_trade clamping."""
    with patch("app.main.get_settings") as mock_get_settings:
        from app.config import PocketOptionBotConfig
        mock_get_settings.return_value = PocketOptionBotConfig(
            enabled=True,
            dry_run=True,
            base_stake=10.0,
            max_stake_per_trade=5.0,
            account_type="DEMO",
        )
        
        from app.service.trade_executor import TradeExecutor
        executor = TradeExecutor(mock_get_settings.return_value)
        
        with patch("app.main.executor", executor):
            payload = {
                "signal_type": "ENTRY",
                "asset": "GBP/USD OTC",
                "duration_minutes": 5,
                "direction": "LOWER",
                "amount_multiplier": None,
                "raw_message_id": 12351,
                "raw_channel_id": -1002019935922,
                "raw_text": "GBP/USD OTC 5 min LOWER",
            }
            
            response = client.post("/place_trade", json=payload)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "accepted"

