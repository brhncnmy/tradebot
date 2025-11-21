from fastapi.testclient import TestClient

from common.models.order_request import AccountRef, OpenOrderRequest
from services.order_gateway.src.main import app

client = TestClient(app)


def test_open_order_dry_run():
    """Test order opening in DRY_RUN mode."""
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
        "meta": {}
    }
    
    response = client.post("/orders/open", json=payload)
    
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "DRY_RUN"
    assert body["exchange"].lower() == "bingx"
    assert body["order_id"].startswith("dryrun-")

