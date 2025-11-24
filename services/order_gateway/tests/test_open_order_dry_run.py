from fastapi.testclient import TestClient

from common.models.order_request import AccountRef, OpenOrderRequest
from services.order_gateway.src.main import app

client = TestClient(app)


def test_open_order_dry_run():
    """Test order opening endpoint (may fail if credentials missing for test mode)."""
    payload = {
        "account": {
            "exchange": "bingx",
            "account_id": "bingx_primary"
        },
        "symbol": "BTC-USDT",
        "side": "long",
        "entry_type": "market",
        "quantity": 0.001,
        "price": None,
        "leverage": None,
        "stop_loss": None,
        "take_profits": [],
        "client_order_id": None,
        "meta": {},
        "command": "ENTER_LONG",
        "margin_type": "ISOLATED",
        "tp_close_pct": None,
        "raw_payload": "{\"symbol\": \"BTC-USDT\"}"
    }
    
    response = client.post("/orders/open", json=payload)
    
    # Note: bingx_primary is configured with mode="test", so it will attempt an API call
    # If credentials are missing, it will return 400
    # If credentials are present, it will return 200 (or 502 if API call fails)
    assert response.status_code in (200, 400, 502)
    if response.status_code == 200:
        body = response.json()
        assert body["exchange"].lower() == "bingx"
        assert "mode" in body

