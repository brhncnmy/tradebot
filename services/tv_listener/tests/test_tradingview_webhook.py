from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.tv_listener.src.main import app

client = TestClient(app)


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_valid_payload_forwarded(mock_client_class):
    """Test that a valid TradingView payload is forwarded to signal-orchestrator."""
    payload = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "entry_type": "market",
        "quantity": 0.001,
        "stop_loss": 28000.0,
        "take_profits": [
            {"price": 31000.0, "size_pct": 50},
            {"price": 32000.0, "size_pct": 50},
        ],
        "routing_profile": "default",
        "leverage": 10,
        "strategy_name": "tv_test_strategy",
    }
    
    # Capture the JSON payload sent to signal-orchestrator
    captured_json = {}
    
    # Mock httpx.AsyncClient.post
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    
    async def capture_post(url, json=None, timeout=None, **kwargs):
        captured_json["url"] = url
        captured_json["json"] = json
        return mock_response
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(side_effect=capture_post)
    mock_client_class.return_value = mock_client
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "forwarded"
    assert response.json()["upstream_status"] == 200
    
    # Verify the mock was called
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert call_args[0][0].endswith("/signals")
    
    # Verify the forwarded JSON payload has a string timestamp
    assert "json" in captured_json
    forwarded_payload = captured_json["json"]
    assert "timestamp" in forwarded_payload
    assert isinstance(forwarded_payload["timestamp"], str)
    assert forwarded_payload["timestamp"]  # non-empty string


def test_invalid_side_results_in_400():
    """Test that an invalid side value results in 400 error."""
    payload = {
        "symbol": "BTC-USDT",
        "side": "nonsense",
        "entry_type": "market",
        "quantity": 0.001,
    }
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 400
    assert "Invalid side" in response.json()["detail"]


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_symbol_normalization(mock_client_class):
    """Test that TradingView ticker symbols are normalized correctly."""
    payload = {
        "symbol": "BINANCE:LIGHTUSDT.P",
        "side": "buy",
        "entry_type": "market",
        "quantity": 0.001,
        "stop_loss": 28000.0,
        "take_profits": [],
        "routing_profile": "default",
        "leverage": 10,
        "strategy_name": "tv_test_strategy",
    }
    
    # Capture the JSON payload sent to signal-orchestrator
    captured_json = {}
    
    # Mock httpx.AsyncClient.post
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    
    async def capture_post(url, json=None, timeout=None, **kwargs):
        captured_json["url"] = url
        captured_json["json"] = json
        return mock_response
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(side_effect=capture_post)
    mock_client_class.return_value = mock_client
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 200
    assert response.json()["status"] == "forwarded"
    
    # Verify the forwarded JSON payload has normalized symbol
    assert "json" in captured_json
    forwarded_payload = captured_json["json"]
    assert forwarded_payload["symbol"] == "LIGHTUSDT"
    
    # Verify the original symbol is preserved in raw_payload
    assert "raw_payload" in forwarded_payload
    assert forwarded_payload["raw_payload"]["symbol"] == "BINANCE:LIGHTUSDT.P"

