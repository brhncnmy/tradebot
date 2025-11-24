from typing import Optional
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

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
def test_route_signal_dry_run(mock_client_class):
    """Test that a signal is routed to order-gateway in DRY_RUN mode."""
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
def test_route_exit_short_signal(mock_client_class):
    """Test that EXIT_SHORT signal is routed to order-gateway."""
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
def test_route_exit_long_signal(mock_client_class):
    """Test that EXIT_LONG signal is routed to order-gateway."""
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
