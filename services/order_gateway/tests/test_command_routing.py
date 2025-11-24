"""Tests for order-gateway command routing."""

from fastapi.testclient import TestClient

from common.models.order_request import AccountRef, OpenOrderRequest
from common.models.tv_command import TvCommand
from services.order_gateway.src.main import ActionType, map_command_to_action, app


client = TestClient(app)


def test_map_command_to_action_enter_long():
    """Verify ENTER_LONG commands map to open-position actions."""
    request = OpenOrderRequest(
        account=AccountRef(exchange="bingx", account_id="bingx_vst_demo"),
        symbol="HBARUSDT",
        side="long",
        entry_type="market",
        quantity=123.0,
        command=TvCommand.ENTER_LONG,
        take_profits=[],
        margin_type="ISOLATED",
    )

    action = map_command_to_action(request)

    assert action.action_type == ActionType.OPEN_POSITION
    assert action.side == "long"
    assert action.quantity == 123.0
    assert action.margin_type == "ISOLATED"


def test_cancel_all_returns_ack_response():
    """Ensure CANCEL_ALL commands are accepted but not executed yet."""
    payload = {
        "account": {"exchange": "bingx", "account_id": "bingx_vst_demo"},
        "symbol": "HBARUSDT",
        "entry_type": "market",
        "command": "CANCEL_ALL",
        "take_profits": [],
    }

    response = client.post("/orders/open", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == ActionType.CLOSE_ALL_POSITIONS.value
    assert "not implemented yet" in data["note"]

