"""Shared enums for TradingView command contract."""

from enum import Enum


class TvCommand(str, Enum):
    """Supported TradingView command types."""

    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    EXIT_LONG = "EXIT_LONG"
    EXIT_SHORT = "EXIT_SHORT"
    EXIT_LONG_ALL = "EXIT_LONG_ALL"
    EXIT_SHORT_ALL = "EXIT_SHORT_ALL"
    EXIT_LONG_PARTIAL = "EXIT_LONG_PARTIAL"
    EXIT_SHORT_PARTIAL = "EXIT_SHORT_PARTIAL"
    CANCEL_ALL = "CANCEL_ALL"

