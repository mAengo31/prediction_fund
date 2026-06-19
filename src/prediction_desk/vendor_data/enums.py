"""Enums for vendor dataset sample evaluation."""

from __future__ import annotations

from enum import StrEnum


class VendorLicenseStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    SAMPLE_ONLY = "SAMPLE_ONLY"
    INTERNAL_RESEARCH = "INTERNAL_RESEARCH"
    COMMERCIAL_RESTRICTED = "COMMERCIAL_RESTRICTED"
    APPROVED = "APPROVED"


class VendorFileType(StrEnum):
    CSV = "CSV"
    JSON = "JSON"
    JSONL = "JSONL"
    PARQUET = "PARQUET"
    UNKNOWN = "UNKNOWN"


class VendorValidationStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class VendorImportDryRunStatus(StrEnum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


class VendorEvaluationStatus(StrEnum):
    PROMISING = "PROMISING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECT_SAMPLE = "REJECT_SAMPLE"
    HOLD = "HOLD"


class VendorSampleKind(StrEnum):
    MARKET_DATA = "market_data"
    ORDERBOOK = "orderbook"
    TRADES = "trades"
    PRICE_HISTORY = "price_history"
    MIXED = "mixed"
