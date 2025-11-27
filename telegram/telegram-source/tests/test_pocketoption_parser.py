"""Tests for PocketOption message parser."""

import pytest
from unittest.mock import Mock

from app.models.pocketoption import PocketOptionDirection
from app.parsers.pocketoption import PocketOptionParser


class MockMessage:
    """Mock Telethon message for testing."""
    
    def __init__(self, text: str, message_id: int = 12345, chat_id: int = -1001234567890):
        self.text = text
        self.id = message_id
        self.chat_id = chat_id


def test_parse_valid_signal():
    """Test parsing a valid PocketOption signal message."""
    parser = PocketOptionParser()
    
    message_text = """PO SIGNAL
Asset: EURUSD
Direction: CALL
Duration: 1m
Amount: 5$
Strategy: LondonBreakout"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.asset == "EURUSD"
    assert signal.direction == PocketOptionDirection.CALL
    assert signal.duration_seconds == 60
    assert signal.stake == 5.0
    assert signal.strategy == "LondonBreakout"
    assert signal.raw_message_id == 12345
    assert signal.raw_channel_id == -1001234567890
    assert signal.raw_text == message_text


def test_parse_signal_without_strategy():
    """Test parsing a signal without strategy field."""
    parser = PocketOptionParser()
    
    message_text = """PO SIGNAL
Asset: BTCUSD
Direction: PUT
Duration: 2m
Amount: 10$"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.asset == "BTCUSD"
    assert signal.direction == PocketOptionDirection.PUT
    assert signal.duration_seconds == 120
    assert signal.stake == 10.0
    assert signal.strategy is None


def test_parse_signal_different_durations():
    """Test parsing signals with different duration values."""
    parser = PocketOptionParser()
    
    test_cases = [
        ("1m", 60),
        ("2m", 120),
        ("5m", 300),
        ("10m", 600),
    ]
    
    for duration_str, expected_seconds in test_cases:
        message_text = f"""PO SIGNAL
Asset: EURUSD
Direction: CALL
Duration: {duration_str}
Amount: 5$"""
        
        message = MockMessage(message_text)
        signal = parser.parse(message)
        
        assert signal is not None, f"Failed to parse duration {duration_str}"
        assert signal.duration_seconds == expected_seconds, f"Wrong duration for {duration_str}"


def test_parse_signal_different_amount_formats():
    """Test parsing signals with different amount formats."""
    parser = PocketOptionParser()
    
    test_cases = [
        ("5$", 5.0),
        ("$5", 5.0),
        ("5.0", 5.0),
        ("10.5", 10.5),
        ("Amount: 20$", 20.0),
    ]
    
    for amount_str, expected_stake in test_cases:
        message_text = f"""PO SIGNAL
Asset: EURUSD
Direction: CALL
Duration: 1m
{amount_str}"""
        
        message = MockMessage(message_text)
        signal = parser.parse(message)
        
        assert signal is not None, f"Failed to parse amount {amount_str}"
        assert signal.stake == expected_stake, f"Wrong stake for {amount_str}"


def test_parse_signal_different_directions():
    """Test parsing signals with different direction values."""
    parser = PocketOptionParser()
    
    test_cases = [
        ("CALL", PocketOptionDirection.CALL),
        ("PUT", PocketOptionDirection.PUT),
        ("UP", PocketOptionDirection.UP),
        ("DOWN", PocketOptionDirection.DOWN),
    ]
    
    for direction_str, expected_direction in test_cases:
        message_text = f"""PO SIGNAL
Asset: EURUSD
Direction: {direction_str}
Duration: 1m
Amount: 5$"""
        
        message = MockMessage(message_text)
        signal = parser.parse(message)
        
        assert signal is not None, f"Failed to parse direction {direction_str}"
        assert signal.direction == expected_direction, f"Wrong direction for {direction_str}"


def test_parse_signal_case_insensitive():
    """Test that parsing is case-insensitive."""
    parser = PocketOptionParser()
    
    message_text = """po signal
asset: eurusd
direction: call
duration: 1m
amount: 5$"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is not None
    assert signal.asset == "EURUSD"  # Should be uppercase
    assert signal.direction == PocketOptionDirection.CALL


def test_parse_signal_missing_asset():
    """Test parsing fails when asset is missing."""
    parser = PocketOptionParser()
    
    message_text = """PO SIGNAL
Direction: CALL
Duration: 1m
Amount: 5$"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_signal_missing_direction():
    """Test parsing fails when direction is missing."""
    parser = PocketOptionParser()
    
    message_text = """PO SIGNAL
Asset: EURUSD
Duration: 1m
Amount: 5$"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_signal_missing_duration():
    """Test parsing fails when duration is missing."""
    parser = PocketOptionParser()
    
    message_text = """PO SIGNAL
Asset: EURUSD
Direction: CALL
Amount: 5$"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_signal_missing_amount():
    """Test parsing fails when amount is missing."""
    parser = PocketOptionParser()
    
    message_text = """PO SIGNAL
Asset: EURUSD
Direction: CALL
Duration: 1m"""
    
    message = MockMessage(message_text)
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_signal_empty_message():
    """Test parsing fails for empty message."""
    parser = PocketOptionParser()
    
    message = MockMessage("")
    signal = parser.parse(message)
    
    assert signal is None


def test_parse_signal_none_text():
    """Test parsing fails when message has no text."""
    parser = PocketOptionParser()
    
    message = MockMessage("")
    message.text = None
    signal = parser.parse(message)
    
    assert signal is None


