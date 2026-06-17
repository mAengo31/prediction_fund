"""Market-data enumerations."""

from __future__ import annotations

from enum import StrEnum


class MarketPriceSource(StrEnum):
    ORDERBOOK_DERIVED = "ORDERBOOK_DERIVED"
    VENUE_LAST_PRICE = "VENUE_LAST_PRICE"
    VENUE_MID_PRICE = "VENUE_MID_PRICE"
    VENUE_PRICE_HISTORY = "VENUE_PRICE_HISTORY"
    TRADE_DERIVED = "TRADE_DERIVED"
    MANUAL_FIXTURE = "MANUAL_FIXTURE"
    UNKNOWN = "UNKNOWN"


class MarketDataQualitySeverity(StrEnum):
    OK = "OK"
    WARNING = "WARNING"
    ERROR = "ERROR"
    UNKNOWN = "UNKNOWN"
