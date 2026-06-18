"""Enums for the desk decision workbench."""

from __future__ import annotations

from enum import StrEnum


class ReviewPriorityBucket(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class ReviewStatus(StrEnum):
    NEW = "NEW"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"
    WATCHING = "WATCHING"


class RecommendedReviewAction(StrEnum):
    REVIEW_CONTRACT = "REVIEW_CONTRACT"
    REVIEW_DATA_GAP = "REVIEW_DATA_GAP"
    REVIEW_DIVERGENCE = "REVIEW_DIVERGENCE"
    REVIEW_INTEGRITY = "REVIEW_INTEGRITY"
    REVIEW_PRETRADE_BLOCK = "REVIEW_PRETRADE_BLOCK"
    REVIEW_RESEARCH_SIGNAL = "REVIEW_RESEARCH_SIGNAL"
    WATCH_ONLY = "WATCH_ONLY"
    NO_ACTION = "NO_ACTION"


class DeskReviewNoteType(StrEnum):
    OBSERVATION = "OBSERVATION"
    REVIEW_DECISION = "REVIEW_DECISION"
    RISK_NOTE = "RISK_NOTE"
    DATA_ISSUE = "DATA_ISSUE"
    STRATEGY_NOTE = "STRATEGY_NOTE"


class WorkbenchRunStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

