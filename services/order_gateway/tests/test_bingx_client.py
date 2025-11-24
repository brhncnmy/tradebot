"""Tests for BingX client."""

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from common.models.order_request import AccountRef, OpenOrderRequest
from common.models.tv_command import TvCommand
from common.utils.config import AccountConfig
from services.order_gateway.src.exchanges.bingx_client import (
    build_signed_query,
    get_bingx_env,
    bingx_place_order,
)


def test_get_bingx_env_test():
    """Test test mode environment."""
    env = get_bingx_env("test")
    assert env.base_url == "https://open-api.bingx.com"
    assert env.order_path == "/openApi/swap/v2/trade/order/test"


def test_get_bingx_env_demo():
    """Test demo mode environment."""
    env = get_bingx_env("demo")
    assert env.base_url == "https://open-api-vst.bingx.com"
    assert env.order_path == "/openApi/swap/v2/trade/order"


def test_get_bingx_env_live():
    """Test live mode environment."""
    env = get_bingx_env("live")
    assert env.base_url == "https://open-api.bingx.com"
    assert env.order_path == "/openApi/swap/v2/trade/order"


def test_get_bingx_env_invalid():
    """Test invalid mode raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported BingX mode"):
        get_bingx_env("invalid")


def test_build_signed_query():
    """Test query string building and signing."""
    params = {"symbol": "BTC-USDT", "side": "BUY", "type": "MARKET", "quantity": 0.001}
    secret = "test_secret"
    
    query = build_signed_query(params, secret)
    
    # Check that all params are present
    assert "symbol=BTC-USDT" in query
    assert "side=BUY" in query
    assert "type=MARKET" in query
    assert "quantity=0.001" in query
    assert "timestamp=" in query
    assert "signature=" in query
    
    # Check signature is hex
    sig_part = query.split("signature=")[1]
    assert len(sig_part) == 64  # SHA256 hex digest length


@pytest.mark.asyncio
async def test_bingx_place_order_test_mode():
    """Test BingX order placement in test mode."""
    account_config = AccountConfig(
        account_id="test_account",
        exchange="bingx",
        mode="test",
        api_key_env="TEST_API_KEY",
        secret_key_env="TEST_SECRET_KEY",
    )
    
    order = OpenOrderRequest(
        account=AccountRef(exchange="bingx", account_id="test_account"),
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
    with patch.dict(os.environ, {"TEST_API_KEY": "test_key", "TEST_SECRET_KEY": "test_secret"}):
        # Create a mock response object
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                
            def json(self):
                return {"code": 0, "data": {"orderId": "12345"}}
                
            def raise_for_status(self):
                pass
        
        mock_response = MockResponse()
        captured_url = None
        captured_headers = None
        
        async def mock_post(url, headers, content, **kwargs):
            nonlocal captured_url, captured_headers
            captured_url = url
            captured_headers = headers
            # Verify URL contains test endpoint
            assert "/order/test" in url
            # Verify symbol is converted to BingX format
            assert "symbol=BTC-USDT" in url
            # Verify headers include API key
            assert "X-BX-APIKEY" in headers
            assert headers["X-BX-APIKEY"] == "test_key"
            # Verify signature is present
            assert "signature=" in url
            return mock_response
        
        with patch("services.order_gateway.src.exchanges.bingx_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client
            
            result = await bingx_place_order(account_config, order)
            
            assert result["code"] == 0
            assert result["data"]["orderId"] == "12345"


@pytest.mark.asyncio
async def test_bingx_place_order_missing_credentials():
    """Test that missing credentials raise ValueError."""
    account_config = AccountConfig(
        account_id="test_account",
        exchange="bingx",
        mode="test",
        api_key_env="MISSING_KEY",
        secret_key_env="MISSING_SECRET",
    )
    
    order = OpenOrderRequest(
        account=AccountRef(exchange="bingx", account_id="test_account"),
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
    
    # Ensure env vars are not set
    with patch.dict(os.environ, {}, clear=False):
        # Remove the keys if they exist
        os.environ.pop("MISSING_KEY", None)
        os.environ.pop("MISSING_SECRET", None)
        
        with pytest.raises(ValueError, match="Missing API credentials"):
            await bingx_place_order(account_config, order)


@pytest.mark.asyncio
async def test_bingx_place_order_demo_mode():
    """Test BingX order placement in demo mode (VST host)."""
    account_config = AccountConfig(
        account_id="demo_account",
        exchange="bingx",
        mode="demo",
        api_key_env="VST_API_KEY",
        secret_key_env="VST_SECRET_KEY",
    )
    
    order = OpenOrderRequest(
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
        # Create a mock response object
        class MockResponse:
            def __init__(self):
                self.status_code = 200
                
            def json(self):
                return {"code": 0, "data": {"orderId": "67890"}}
                
            def raise_for_status(self):
                pass
        
        mock_response = MockResponse()
        captured_url = None
        
        async def mock_post(url, headers, content, **kwargs):
            nonlocal captured_url
            captured_url = url
            # Verify URL uses VST host
            assert "open-api-vst.bingx.com" in url
            # Verify URL does NOT contain /order/test (demo uses /order)
            assert "/order/test" not in url
            assert "/order" in url
            # Verify symbol is converted to BingX format
            assert "symbol=BTC-USDT" in url
            # Verify headers include API key
            assert "X-BX-APIKEY" in headers
            assert headers["X-BX-APIKEY"] == "vst_key"
            # Verify signature is present
            assert "signature=" in url
            return mock_response
        
        with patch("services.order_gateway.src.exchanges.bingx_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = mock_post
            mock_client_class.return_value = mock_client
            
            result = await bingx_place_order(account_config, order)
            
            assert result["code"] == 0
            assert result["data"]["orderId"] == "67890"
            # Verify VST host was used
            assert "open-api-vst.bingx.com" in captured_url

