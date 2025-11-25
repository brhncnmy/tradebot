"""Tests for symbol mapping utilities."""

from services.order_gateway.src.exchanges.symbol_utils import to_bingx_symbol


def test_to_bingx_symbol_btcusdt():
    """Test BTCUSDT -> BTC-USDT conversion."""
    assert to_bingx_symbol("BTCUSDT") == "BTC-USDT"


def test_to_bingx_symbol_lightusdt():
    """Test LIGHTUSDT -> LIGHT-USDT conversion."""
    assert to_bingx_symbol("LIGHTUSDT") == "LIGHT-USDT"


def test_to_bingx_symbol_usdc():
    """Test USDC quote asset conversion."""
    assert to_bingx_symbol("BTCUSDC") == "BTC-USDC"


def test_to_bingx_symbol_already_formatted():
    """Test that already formatted symbols are unchanged."""
    assert to_bingx_symbol("BTC-USDT") == "BTC-USDT"


def test_to_bingx_symbol_non_matching():
    """Test that non-matching symbols are unchanged."""
    assert to_bingx_symbol("UNKNOWN") == "UNKNOWN"
    assert to_bingx_symbol("BTC") == "BTC"


