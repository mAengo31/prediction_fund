"""Ingestion enumerations for read-only venue payloads."""

from __future__ import annotations

from enum import StrEnum


class VenueEndpointType(StrEnum):
    MARKET_LIST = "MARKET_LIST"
    MARKET_DETAIL = "MARKET_DETAIL"
    EVENT_LIST = "EVENT_LIST"
    EVENT_DETAIL = "EVENT_DETAIL"
    ORDERBOOK = "ORDERBOOK"
    PRICE_HISTORY = "PRICE_HISTORY"
    TRADE_HISTORY = "TRADE_HISTORY"
    SERIES_LIST = "SERIES_LIST"
    SERIES_DETAIL = "SERIES_DETAIL"
    UNKNOWN = "UNKNOWN"


class VenueMappingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RESOLVED = "RESOLVED"
    FAILED_NORMALIZATION = "FAILED_NORMALIZATION"
    IGNORED = "IGNORED"


class IngestionRunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class IngestionMode(StrEnum):
    FIXTURE = "FIXTURE"
    MANUAL_PUBLIC_FETCH = "MANUAL_PUBLIC_FETCH"


class IngestionSource(StrEnum):
    KALSHI = "KALSHI"
    POLYMARKET = "POLYMARKET"
    OTHER = "OTHER"


class IngestionCursorStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
    COMPLETE = "COMPLETE"
