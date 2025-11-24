from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from services.tv_listener.src.main import app

client = TestClient(app)


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_valid_payload_forwarded(mock_client_class):
    """Test that a valid TradingView payload is forwarded to signal-orchestrator."""
    payload = {
        "command": "ENTER_LONG",
        "symbol": "BTC-USDT",
        "order_type": "market",
        "quantity": 0.001,
        "stop_loss": 28000.0,
        "take_profits": [
            {"price": 31000.0, "size_pct": 50},
            {"price": 32000.0, "size_pct": 50},
        ],
        "routing_profile": "default",
        "leverage": 10,
        "margin_type": "ISOLATED",
        "strategy_name": "tv_test_strategy",
        "timestamp": 1732387200000,
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
    
    # Verify the forwarded JSON payload has expected fields
    assert "json" in captured_json
    forwarded_payload = captured_json["json"]
    assert "timestamp" in forwarded_payload
    assert isinstance(forwarded_payload["timestamp"], str)
    assert forwarded_payload["timestamp"]  # non-empty string
    assert forwarded_payload["command"] == "ENTER_LONG"
    assert forwarded_payload["margin_type"] == "ISOLATED"
    assert forwarded_payload["tp_close_pct"] is None
    assert forwarded_payload["raw_payload"]


def test_invalid_command_results_in_400():
    """Test that an invalid command value results in 400 error."""
    payload = {
        "command": "DO_SOMETHING",
        "symbol": "BTC-USDT",
        "order_type": "market",
        "quantity": 0.001,
    }
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 400
    assert "Unsupported command" in response.json()["detail"]


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_symbol_normalization(mock_client_class):
    """Test that TradingView ticker symbols are normalized correctly."""
    payload = {
        "command": "ENTER_LONG",
        "symbol": "BINANCE:LIGHTUSDT.P",
        "order_type": "market",
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
    
    # Verify the original symbol is preserved in raw_payload text
    assert "raw_payload" in forwarded_payload
    import json

    raw_data = json.loads(forwarded_payload["raw_payload"])
    assert raw_data["symbol"] == "BINANCE:LIGHTUSDT.P"


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_legacy_payload_with_side_buy(mock_client_class):
    """Test that legacy payload with side='buy' (no command) is accepted and normalized."""
    payload = {
        "symbol": "BTC-USDT",
        "side": "buy",  # Legacy format
        "entry_type": "market",  # Legacy field name
        "quantity": 0.001,
        "stop_loss": None,  # Nullable
        "take_profits": None,  # Nullable
        "routing_profile": "default",
        "leverage": 10,
        "strategy_name": "test_strategy",
    }
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 200
    # Verify command was derived from side
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["command"] == "ENTER_LONG"  # Derived from side="buy"


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_legacy_payload_with_side_sell(mock_client_class):
    """Test that legacy payload with side='sell' is normalized to SHORT."""
    payload = {
        "symbol": "BTC-USDT",
        "side": "sell",
        "entry_type": "market",
        "quantity": 0.001,
    }
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 200
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    assert forwarded_json["command"] == "ENTER_SHORT"  # Derived from side="sell"


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_payload_with_null_stop_loss_and_take_profits(mock_client_class):
    """Test that null stop_loss and take_profits are accepted."""
    payload = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "entry_type": "market",
        "quantity": 0.001,
        "stop_loss": None,
        "take_profits": None,
    }
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 200  # Should not return 422


@patch("services.tv_listener.src.main.httpx.AsyncClient")
def test_command_defaults_to_enter_when_omitted(mock_client_class):
    """Test that command defaults to ENTER when omitted."""
    payload = {
        "symbol": "BTC-USDT",
        "side": "buy",
        "entry_type": "market",
        "quantity": 0.001,
    }
    # Note: no "command" field
    
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"ok": True}
    
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client_class.return_value = mock_client
    
    response = client.post("/webhook/tradingview", json=payload)
    
    assert response.status_code == 200
    call_args = mock_client.post.call_args
    forwarded_json = call_args[1]["json"]
    # Command should be derived as ENTER_LONG from side="buy"
    assert forwarded_json["command"] == "ENTER_LONG"

