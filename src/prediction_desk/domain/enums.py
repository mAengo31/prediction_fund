"""Domain enumerations."""

from __future__ import annotations

from enum import StrEnum


class VenueType(StrEnum):
    CFTC_DCM = "CFTC_DCM"
    CRYPTO_CLOB = "CRYPTO_CLOB"
    OTHER = "OTHER"


class MarketType(StrEnum):
    BINARY = "BINARY"
    MULTI_OUTCOME = "MULTI_OUTCOME"
    SCALAR = "SCALAR"
    OTHER = "OTHER"


class MarketStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"
    SETTLED = "SETTLED"
    CANCELED = "CANCELED"


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class VerdictAction(StrEnum):
    ALLOW = "ALLOW"
    ALLOW_SMALLER_SIZE = "ALLOW_SMALLER_SIZE"
    PASSIVE_ONLY = "PASSIVE_ONLY"
    NO_TRADE = "NO_TRADE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
