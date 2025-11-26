import importlib
import os
from typing import Optional
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from common.utils import config as config_module
from services.signal_orchestrator.src.main import app

client = TestClient(app)


class DummyResponse:
    """Synchronous response mock for httpx.AsyncClient.post."""
    
    def __init__(self, status_code: int = 200, json_data: Optional[dict] = None):
        self.status_code = status_code
        self._json_data = json_data or {}
    
    def json(self) -> dict:
        """Synchronous json() method like httpx.Response."""
        return self._json_data
    
    def raise_for_status(self):
        """Raise for non-2xx status codes."""
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_route_signal_dry_run(mock_client_class, monkeypatch):
    """Test that a signal is routed to order-gateway in DRY_RUN mode."""
    # Enable account 1 for default routing
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    importlib.reload(config_module)
    
    payload = {
        "command": "ENTER_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTC-USDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": "ISOLATED",
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": 28000.0,
        "take_profits": [],
        "routing_profile": "default",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTC-USDT\"}",
    }
    
    # Create DummyResponse
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "DRY_RUN",
            "order_id": "dryrun-test-order-id"
        }
    )
    
    # Setup mock client with async context manager support
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 1
    
    # Verify the mock was called
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0].endswith("/orders/open")
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["command"] == "ENTER_LONG"
    assert forwarded_json["margin_type"] == "ISOLATED"


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_route_exit_short_signal(mock_client_class, monkeypatch):
    """Test that EXIT_SHORT signal is routed to order-gateway."""
    # Enable account 1 for default routing
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    importlib.reload(config_module)
    
    payload = {
        "command": "EXIT_SHORT",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "NTRNUSDT",
        "side": "short",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 5794.02,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "default",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"NTRNUSDT\", \"code\": \"short exit\"}",
        "code": "short exit",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-exit-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 1
    
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["command"] == "EXIT_SHORT"
    assert forwarded_json["symbol"] == "NTRNUSDT"
    assert forwarded_json["quantity"] == 5794.02


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_route_exit_long_signal(mock_client_class, monkeypatch):
    """Test that EXIT_LONG signal is routed to order-gateway."""
    # Enable account 1 for default routing
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    importlib.reload(config_module)
    
    payload = {
        "command": "EXIT_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "default",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\", \"code\": \"long exit\"}",
        "code": "long exit",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-exit-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["command"] == "EXIT_LONG"
    assert forwarded_json["symbol"] == "BTCUSDT"
    assert forwarded_json["side"] == "long"


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_route_signal_to_multiple_accounts(mock_client_class, monkeypatch):
    """Test that a signal is routed to multiple accounts when both accounts are configured."""
    # Enable both accounts
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    monkeypatch.setenv("BINGX_2_API_KEY", "key_2")
    monkeypatch.setenv("BINGX_2_API_SECRET", "secret_2")
    importlib.reload(config_module)
    
    payload = {
        "command": "ENTER_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "demo_1_2",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\"}",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 2  # Should route to both accounts
    
    # Verify the mock was called twice (once for each account)
    assert mock_client.post.call_count == 2
    
    # Verify both calls have the same order parameters
    calls = mock_client.post.call_args_list
    assert len(calls) == 2
    
    # Both calls should have the same command and symbol
    for call in calls:
        forwarded_json = call[1]["json"]
        assert forwarded_json["command"] == "ENTER_LONG"
        assert forwarded_json["symbol"] == "BTCUSDT"
        assert forwarded_json["quantity"] == 0.001
    
    # Cleanup: remove env vars and reload
    monkeypatch.delenv("BINGX_1_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_1_API_SECRET", raising=False)
    monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    importlib.reload(config_module)


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_routing_profile_demo_1(mock_client_class, monkeypatch):
    """Test that routing_profile=demo_1 routes only to bingx_1 account."""
    # Enable account 1, disable account 2
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    importlib.reload(config_module)
    
    payload = {
        "command": "ENTER_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "demo_1",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\"}",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 1
    
    # Verify only one call was made (to bingx_1 only)
    assert mock_client.post.call_count == 1
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["account"]["account_id"] == "bingx_1"


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_routing_profile_demo_2_with_credentials(mock_client_class, monkeypatch):
    """Test that routing_profile=demo_2 routes to bingx_2 when configured."""
    # Enable account 2, disable account 1
    monkeypatch.delenv("BINGX_1_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_1_API_SECRET", raising=False)
    monkeypatch.setenv("BINGX_2_API_KEY", "key_2")
    monkeypatch.setenv("BINGX_2_API_SECRET", "secret_2")
    importlib.reload(config_module)
    
    payload = {
        "command": "ENTER_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "demo_2",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\"}",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 1
    
    # Verify call was made to bingx_2 account
    assert mock_client.post.call_count == 1
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["account"]["account_id"] == "bingx_2"
    
    # Cleanup
    monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    importlib.reload(config_module)


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_routing_profile_demo_1_2_with_both_configured(mock_client_class, monkeypatch):
    """Test that routing_profile=demo_1_2 routes to both accounts when both are configured."""
    # Enable both accounts
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    monkeypatch.setenv("BINGX_2_API_KEY", "key_2")
    monkeypatch.setenv("BINGX_2_API_SECRET", "secret_2")
    importlib.reload(config_module)
    
    payload = {
        "command": "ENTER_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "demo_1_2",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\"}",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 2
    
    # Verify two calls were made (one to each account)
    assert mock_client.post.call_count == 2
    calls = mock_client.post.call_args_list
    account_ids = [call[1]["json"]["account"]["account_id"] for call in calls]
    assert "bingx_1" in account_ids
    assert "bingx_2" in account_ids
    
    # Cleanup
    monkeypatch.delenv("BINGX_1_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_1_API_SECRET", raising=False)
    monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    importlib.reload(config_module)


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_routing_profile_demo_1_2_without_account_2(mock_client_class, monkeypatch):
    """Test that routing_profile=demo_1_2 falls back to bingx_1 when bingx_2 is not configured."""
    # Enable account 1, disable account 2
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    monkeypatch.delenv("BINGX_2_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_2_API_SECRET", raising=False)
    importlib.reload(config_module)
    
    payload = {
        "command": "ENTER_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "demo_1_2",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\"}",
    }
    
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "status": "accepted",
            "mode": "demo",
            "order_id": "test-order-id"
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    # Should route to bingx_1 only (bingx_2 unavailable)
    assert response_data["routed_accounts"] == 1
    
    # Verify only one call was made (to bingx_1)
    assert mock_client.post.call_count == 1
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["account"]["account_id"] == "bingx_1"


@patch("services.signal_orchestrator.src.main.httpx.AsyncClient")
def test_no_position_response_treated_as_noop(mock_client_class, monkeypatch):
    """Test that order-gateway returning HTTP 200 with order_status=no_position is treated as INFO, not ERROR."""
    # Enable account 1
    monkeypatch.setenv("BINGX_1_API_KEY", "key_1")
    monkeypatch.setenv("BINGX_1_API_SECRET", "secret_1")
    importlib.reload(config_module)
    
    payload = {
        "command": "EXIT_LONG",
        "source": "tradingview",
        "strategy_name": "tv_test_strategy",
        "symbol": "BTCUSDT",
        "side": "long",
        "entry_type": "market",
        "entry_price": None,
        "quantity": 0.001,
        "leverage": 10,
        "margin_type": None,
        "tp_close_pct": None,
        "risk_per_trade_pct": None,
        "stop_loss": None,
        "take_profits": [],
        "routing_profile": "demo_1",
        "timestamp": None,
        "raw_payload": "{\"symbol\": \"BTCUSDT\"}",
    }
    
    # Mock order-gateway returning HTTP 200 with no_position status
    dummy_response = DummyResponse(
        status_code=200,
        json_data={
            "ok": True,
            "exchange": "bingx",
            "mode": "demo",
            "account_id": "bingx_1",
            "order_status": "no_position",
            "api_code": 101205,
            "api_msg": "No position to close",
        }
    )
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=dummy_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/signals", json=payload)
    
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "processed"
    assert response_data["routed_accounts"] == 1
    
    # Verify the mock was called
    assert mock_client.post.call_count == 1
    
    # Cleanup
    monkeypatch.delenv("BINGX_1_API_KEY", raising=False)
    monkeypatch.delenv("BINGX_1_API_SECRET", raising=False)
    importlib.reload(config_module)
