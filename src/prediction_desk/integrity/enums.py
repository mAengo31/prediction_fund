"""Enums for deterministic integrity signals."""

from __future__ import annotations

from enum import StrEnum


class SignalCategory(StrEnum):
    PRICE_ANOMALY = "PRICE_ANOMALY"
    LIQUIDITY_ANOMALY = "LIQUIDITY_ANOMALY"
    DATA_FRESHNESS = "DATA_FRESHNESS"
    ORDERBOOK_STRUCTURE = "ORDERBOOK_STRUCTURE"
    RULE_CHANGE = "RULE_CHANGE"
    RULE_PRICE_COUPLING = "RULE_PRICE_COUPLING"
    DATA_QUALITY = "DATA_QUALITY"
    MANIPULATION_PROXY = "MANIPULATION_PROXY"
    UNKNOWN = "UNKNOWN"


class SignalSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class IntegrityActionHint(StrEnum):
    NONE = "NONE"
    ALLOW = "ALLOW"
    ALLOW_SMALLER_SIZE = "ALLOW_SMALLER_SIZE"
    PASSIVE_ONLY = "PASSIVE_ONLY"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NO_TRADE = "NO_TRADE"


class IntegrityRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
