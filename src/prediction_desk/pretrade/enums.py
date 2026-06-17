"""Pre-trade admissibility enumerations."""

from __future__ import annotations

from enum import StrEnum


class StrategyContext(StrEnum):
    SINGLE_MARKET = "SINGLE_MARKET"
    CROSS_VENUE_COMPARISON = "CROSS_VENUE_COMPARISON"
    MARKET_MAKING = "MARKET_MAKING"
    RESEARCH = "RESEARCH"
    UNKNOWN = "UNKNOWN"


class TradeSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"


class TradeIntentType(StrEnum):
    PASSIVE_LIMIT = "PASSIVE_LIMIT"
    AGGRESSIVE_LIMIT = "AGGRESSIVE_LIMIT"
    MARKET_LIKE = "MARKET_LIKE"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    UNKNOWN = "UNKNOWN"


class RestrictionType(StrEnum):
    NO_TRADE = "NO_TRADE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PASSIVE_ONLY = "PASSIVE_ONLY"
    SIZE_LIMIT = "SIZE_LIMIT"


class RestrictionScopeType(StrEnum):
    GLOBAL = "GLOBAL"
    VENUE = "VENUE"
    EVENT = "EVENT"
    MARKET = "MARKET"
    CATEGORY = "CATEGORY"
    TITLE_PATTERN = "TITLE_PATTERN"


class ExposureSource(StrEnum):
    MANUAL = "MANUAL"
    SIMULATED = "SIMULATED"
    REPLAY = "REPLAY"
    UNKNOWN = "UNKNOWN"


class PreTradeAction(StrEnum):
    ALLOW = "ALLOW"
    ALLOW_SMALLER_SIZE = "ALLOW_SMALLER_SIZE"
    PASSIVE_ONLY = "PASSIVE_ONLY"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NO_TRADE = "NO_TRADE"


class PreTradeRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

