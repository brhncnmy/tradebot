"""Tests for BingX positionSide mapping."""

import pytest

from common.models.tv_command import TvCommand
from services.order_gateway.src.exchanges.bingx_client import _map_position_side


def test_map_position_side_long():
    """Test positionSide mapping for long positions."""
    assert _map_position_side("long") == "LONG"
    assert _map_position_side("LONG") == "LONG"
    assert _map_position_side("buy") == "LONG"
    assert _map_position_side("BUY") == "LONG"


def test_map_position_side_short():
    """Test positionSide mapping for short positions."""
    assert _map_position_side("short") == "SHORT"
    assert _map_position_side("SHORT") == "SHORT"
    assert _map_position_side("sell") == "SHORT"
    assert _map_position_side("SELL") == "SHORT"


def test_map_position_side_invalid():
    """Test that invalid side raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported side for positionSide"):
        _map_position_side("invalid")
    
    with pytest.raises(ValueError, match="Unsupported side for positionSide"):
        _map_position_side("")


@pytest.mark.asyncio
async def test_bingx_order_includes_position_side():
    """Test that BingX order params include positionSide."""
    import os
    from unittest.mock import AsyncMock, patch
    
    from common.models.order_request import AccountRef, OpenOrderRequest
    from common.utils.config import AccountConfig
    from services.order_gateway.src.exchanges.bingx_client import bingx_place_order
    
    account_config = AccountConfig(
        account_id="demo_account",
        exchange="bingx",
        mode="demo",
        api_key_env="VST_API_KEY",
        secret_key_env="VST_SECRET_KEY",
    )
    
    # Test long position
    order_long = OpenOrderRequest(
        account=AccountRef(exchange="bingx", account_id="demo_account"),
        symbol="BTCUSDT",
        side="long",
        entry_type="market",
        quantity=0.001,
        command=TvCommand.ENTER_LONG,
        take_profits=[],
        stop_loss=None,
        leverage=None,
        meta={},
    )
    
    # Mock environment variables
    with patch.dict(os.environ, {"VST_API_KEY": "vst_key", "VST_SECRET_KEY": "vst_secret"}):
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                
            def json(self):
                return {"code": 0, "data": {"orderId": "12345"}}
                
            def raise_for_status(self):
                pass
        
        mock_response = MockResponse()
        captured_url = None
        
        async def mock_post(url, headers, content, **kwargs):
            nonlocal captured_url
            captured_url = url
            # Verify positionSide is present in URL
            assert "positionSide=LONG" in url
            return mock_response
        
        with patch("services.order_gateway.src.exchanges.bingx_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client
            
            await bingx_place_order(account_config, order_long)
            
            # Verify positionSide=LONG is in the request
            assert "positionSide=LONG" in captured_url
    
    # Test short position
    order_short = OpenOrderRequest(
        account=AccountRef(exchange="bingx", account_id="demo_account"),
        symbol="BTCUSDT",
        side="short",
        entry_type="market",
        quantity=0.001,
        command=TvCommand.ENTER_SHORT,
        take_profits=[],
        stop_loss=None,
        leverage=None,
        meta={},
    )
    
    with patch.dict(os.environ, {"VST_API_KEY": "vst_key", "VST_SECRET_KEY": "vst_secret"}):
        captured_url = None
        
        async def mock_post_short(url, headers, content, **kwargs):
            nonlocal captured_url
            captured_url = url
            # Verify positionSide is present in URL
            assert "positionSide=SHORT" in url
            return mock_response
        
        with patch("services.order_gateway.src.exchanges.bingx_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = mock_post_short
            mock_client_class.return_value = mock_client
            
            await bingx_place_order(account_config, order_short)
            
            # Verify positionSide=SHORT is in the request
            assert "positionSide=SHORT" in captured_url

