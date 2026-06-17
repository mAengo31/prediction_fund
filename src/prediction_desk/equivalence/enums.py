"""Enums for deterministic cross-venue contract equivalence."""

from __future__ import annotations

from enum import StrEnum


class EquivalenceStatus(StrEnum):
    EQUIVALENT = "EQUIVALENT"
    NEAR_EQUIVALENT = "NEAR_EQUIVALENT"
    RELATED = "RELATED"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ComparisonPermission(StrEnum):
    COMPARABLE = "COMPARABLE"
    COMPARABLE_WITH_HAIRCUT = "COMPARABLE_WITH_HAIRCUT"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    DO_NOT_COMPARE = "DO_NOT_COMPARE"


class OutcomeRelation(StrEnum):
    SAME = "SAME"
    INVERSE = "INVERSE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    NOT_EQUIVALENT = "NOT_EQUIVALENT"


class EquivalenceClassStatus(StrEnum):
    ACTIVE = "ACTIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    MIXED = "MIXED"
    RETIRED = "RETIRED"


class EquivalenceRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
