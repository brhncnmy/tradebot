"""Tests for PocketOption message parser."""

import pytest
from unittest.mock import Mock

from app.models.pocketoption import PocketOptionDirection, PocketOptionSignalType
from app.parsers.pocketoption import PocketOptionParser


class MockMessage:
    """Mock Telethon message for testing."""
    
    def __init__(self, text: str, message_id: int = 12345, chat_id: int = -1001234567890):
        self.text = text
        self.id = message_id
        self.chat_id = chat_id


def test_parse_prepare_signal():
    """Test parsing a PREPARE signal message."""
    parser = PocketOptionParser()
    
    message_text = "Prepare a currency GBP/USD OTC"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.signal_type == PocketOptionSignalType.PREPARE
    assert signal.asset == "GBP/USD OTC"
    assert signal.duration_minutes is None
    assert signal.direction is None
    assert signal.amount_multiplier is None
    assert signal.raw_message_id == 12345
    assert signal.raw_channel_id == -1001234567890
    assert signal.raw_text == message_text


def test_parse_entry_signal_lower():
    """Test parsing an ENTRY signal with LOWER direction."""
    parser = PocketOptionParser()
    
    message_text = "GBP/USD OTC 5 min LOWER 📉"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.signal_type == PocketOptionSignalType.ENTRY
    assert signal.asset == "GBP/USD OTC"
    assert signal.duration_minutes == 5
    assert signal.direction == PocketOptionDirection.DOWN
    assert signal.amount_multiplier is None
    assert signal.raw_message_id == 12345
    assert signal.raw_channel_id == -1001234567890
    assert signal.raw_text == message_text


def test_parse_entry_signal_higher():
    """Test parsing an ENTRY signal with HIGHER direction."""
    parser = PocketOptionParser()
    
    message_text = "EUR/USD 10 min HIGHER 📈"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.signal_type == PocketOptionSignalType.ENTRY
    assert signal.asset == "EUR/USD"
    assert signal.duration_minutes == 10
    assert signal.direction == PocketOptionDirection.UP
    assert signal.amount_multiplier is None


def test_parse_repeat_x2_signal():
    """Test parsing a REPEAT_X2 signal."""
    parser = PocketOptionParser()
    
    message_text = """🏪 Repeat/ Amount x2
Expiration & Direction same"""
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.signal_type == PocketOptionSignalType.REPEAT_X2
    assert signal.amount_multiplier == 2.0
    assert signal.asset is None
    assert signal.duration_minutes is None
    assert signal.direction is None
    assert signal.raw_message_id == 12345
    assert signal.raw_channel_id == -1001234567890
    assert signal.raw_text == message_text


def test_parse_repeat_x2_single_line():
    """Test parsing a REPEAT_X2 signal in single line."""
    parser = PocketOptionParser()
    
    message_text = "Repeat/ Amount x2"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.signal_type == PocketOptionSignalType.REPEAT_X2
    assert signal.amount_multiplier == 2.0


def test_parse_profit_message_ignored():
    """Test that profit messages are ignored."""
    parser = PocketOptionParser()
    
    message_text = "profit 👍"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_loss_message_ignored():
    """Test that loss messages are ignored."""
    parser = PocketOptionParser()
    
    message_text = "loss 👎"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_unrelated_message_ignored():
    """Test that unrelated messages are ignored."""
    parser = PocketOptionParser()
    
    message_text = "This is a random message that doesn't match any pattern"
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_empty_message():
    """Test parsing fails for empty message."""
    parser = PocketOptionParser()
    
    message = MockMessage("")
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_none_text():
    """Test parsing fails when message has no text."""
    parser = PocketOptionParser()
    
    message = MockMessage("")
    message.text = None
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_entry_different_durations():
    """Test parsing ENTRY signals with different durations."""
    parser = PocketOptionParser()
    
    test_cases = [
        ("GBP/USD 1 min LOWER", 1),
        ("EUR/USD 5 min HIGHER", 5),
        ("BTC/USD 10 min LOWER", 10),
        ("ETH/USD 15 min HIGHER", 15),
    ]
    
    for message_text, expected_duration in test_cases:
        message = MockMessage(message_text)
        signal = parser.parse(message)
        
        assert signal is not None, f"Failed to parse: {message_text}"
        assert signal.signal_type == PocketOptionSignalType.ENTRY, f"Wrong type for: {message_text}"
        assert signal.duration_minutes == expected_duration, f"Wrong duration for: {message_text}"


def test_parse_entry_different_assets():
    """Test parsing ENTRY signals with different asset formats."""
    parser = PocketOptionParser()
    
    test_cases = [
        ("GBP/USD OTC 5 min LOWER", "GBP/USD OTC"),
        ("EUR/USD 5 min HIGHER", "EUR/USD"),
        ("BTC/USD 5 min LOWER", "BTC/USD"),
    ]
    
    for message_text, expected_asset in test_cases:
        message = MockMessage(message_text)
        signal = parser.parse(message)
        
        assert signal is not None, f"Failed to parse: {message_text}"
        assert signal.asset == expected_asset, f"Wrong asset for: {message_text}"
