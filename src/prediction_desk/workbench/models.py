"""Pydantic models for desk-facing review queues and cards."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prediction_desk.workbench.enums import (
    DeskReviewNoteType,
    RecommendedReviewAction,
    ReviewPriorityBucket,
    ReviewStatus,
    WorkbenchRunStatus,
)

WORKBENCH_VERSION = "desk_workbench_v1"
DECISION_CARD_VERSION = "market_decision_card_v1"
COMPARISON_CARD_VERSION = "cross_venue_comparison_card_v1"
QUEUE_ITEM_VERSION = "market_review_queue_item_v1"


class WorkbenchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DeskWatchlist(WorkbenchModel):
    watchlist_id: str
    name: str
    description: str | None = None
    created_at: datetime
    is_active: bool = True
    market_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketReviewQueueItem(WorkbenchModel):
    queue_item_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    queue_name: str
    priority_score: int = Field(ge=0, le=100)
    priority_bucket: ReviewPriorityBucket
    review_status: ReviewStatus = ReviewStatus.NEW
    primary_reason_code: str
    reason_codes: list[str] = Field(default_factory=list)
    evidence_ref_ids: list[str] = Field(default_factory=list)
    latest_quality_report_id: str | None = None
    latest_integrity_assessment_id: str | None = None
    latest_equivalence_assessment_ids: list[str] = Field(default_factory=list)
    latest_divergence_assessment_ids: list[str] = Field(default_factory=list)
    latest_pretrade_decision_id: str | None = None
    latest_research_signal_ids: list[str] = Field(default_factory=list)
    latest_paper_order_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketDecisionCard(WorkbenchModel):
    decision_card_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    title: str
    venue_name: str | None = None
    market_status: str | None = None
    category: str | None = None
    latest_price: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    spread: Decimal | None = None
    liquidity_summary: dict[str, Any] = Field(default_factory=dict)
    data_quality_summary: dict[str, Any] = Field(default_factory=dict)
    rule_summary: dict[str, Any] = Field(default_factory=dict)
    integrity_summary: dict[str, Any] = Field(default_factory=dict)
    equivalence_summary: dict[str, Any] = Field(default_factory=dict)
    divergence_summary: dict[str, Any] = Field(default_factory=dict)
    pretrade_summary: dict[str, Any] = Field(default_factory=dict)
    paper_summary: dict[str, Any] = Field(default_factory=dict)
    research_summary: dict[str, Any] = Field(default_factory=dict)
    scenario_summary: dict[str, Any] = Field(default_factory=dict)
    data_gap_summary: dict[str, Any] = Field(default_factory=dict)
    review_priority_score: int = Field(ge=0, le=100)
    review_reason_codes: list[str] = Field(default_factory=list)
    recommended_next_review_action: RecommendedReviewAction
    source_ref_ids: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueComparisonCard(WorkbenchModel):
    comparison_card_id: str
    equivalence_assessment_id: str
    divergence_assessment_id: str | None = None
    asof_timestamp: datetime
    left_market_id: str
    right_market_id: str
    equivalence_status: str
    comparison_permission: str
    equivalence_score: int | None = Field(default=None, ge=0, le=100)
    divergence_status: str | None = None
    divergence_score: int | None = Field(default=None, ge=0, le=100)
    aligned_price_summary: dict[str, Any] = Field(default_factory=dict)
    liquidity_comparison: dict[str, Any] = Field(default_factory=dict)
    data_quality_comparison: dict[str, Any] = Field(default_factory=dict)
    rule_comparison: dict[str, Any] = Field(default_factory=dict)
    integrity_comparison: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    recommended_next_review_action: RecommendedReviewAction
    source_ref_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeskReviewNote(WorkbenchModel):
    note_id: str
    created_at: datetime
    market_id: str | None = None
    queue_item_id: str | None = None
    decision_card_id: str | None = None
    comparison_card_id: str | None = None
    author: str | None = None
    note_type: DeskReviewNoteType
    text: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("text")
    @classmethod
    def _require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("note text required")
        return value


class WorkbenchRun(WorkbenchModel):
    workbench_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: WorkbenchRunStatus
    asof_timestamp: datetime
    market_ids: list[str] = Field(default_factory=list)
    queues_built: int = 0
    cards_built: int = 0
    comparison_cards_built: int = 0
    errors_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkbenchRunSummary(WorkbenchModel):
    summary_id: str
    workbench_run_id: str
    created_at: datetime
    total_queue_items: int = 0
    total_decision_cards: int = 0
    total_comparison_cards: int = 0
    priority_counts: dict[str, int] = Field(default_factory=dict)
    review_action_counts: dict[str, int] = Field(default_factory=dict)
    top_reason_codes: dict[str, int] = Field(default_factory=dict)
    markets_reviewed: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkbenchRunConfig(WorkbenchModel):
    name: str | None = None
    asof_timestamp: datetime
    market_ids: list[str] | None = None
    queue_name: str = "default_review_queue"
    build_queue: bool = True
    build_cards: bool = True
    build_comparison_cards: bool = True
    limit: int = Field(default=500, gt=0, le=10000)
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkbenchRunRequest(WorkbenchModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    market_ids: list[str] | None = None
    queue_name: str = "default_review_queue"
    build_queue: bool = True
    build_cards: bool = True
    build_comparison_cards: bool = True
    limit: int = Field(default=500, gt=0, le=10000)
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkbenchRunResult(WorkbenchModel):
    run: WorkbenchRun
    queue_items: list[MarketReviewQueueItem] = Field(default_factory=list)
    decision_cards: list[MarketDecisionCard] = Field(default_factory=list)
    comparison_cards: list[CrossVenueComparisonCard] = Field(default_factory=list)
    summary: WorkbenchRunSummary


class WorkbenchQueueBuildRequest(WorkbenchModel):
    asof_timestamp: datetime | None = None
    market_ids: list[str] | None = None
    queue_name: str = "default_review_queue"
    limit: int = Field(default=500, gt=0, le=1000)
    force: bool = False


class WorkbenchDecisionCardRequest(WorkbenchModel):
    asof_timestamp: datetime | None = None
    force: bool = False


class WorkbenchComparisonCardRequest(WorkbenchModel):
    asof_timestamp: datetime | None = None
    force: bool = False


class DeskReviewNoteCreate(WorkbenchModel):
    market_id: str | None = None
    queue_item_id: str | None = None
    decision_card_id: str | None = None
    comparison_card_id: str | None = None
    author: str | None = None
    note_type: DeskReviewNoteType = DeskReviewNoteType.OBSERVATION
    text: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_reference(self) -> DeskReviewNoteCreate:
        if not any(
            [
                self.market_id,
                self.queue_item_id,
                self.decision_card_id,
                self.comparison_card_id,
            ]
        ):
            raise ValueError("at least one note reference is required")
        return self


def default_watchlists(created_at: datetime) -> list[DeskWatchlist]:
    definitions = [
        (
            "public_read_polymarket_v1",
            "Polymarket public-read markets discovered in staging or fixture collection.",
            ["public_read", "polymarket"],
        ),
        (
            "public_read_kalshi_v1",
            "Kalshi public-read markets discovered in staging or fixture collection.",
            ["public_read", "kalshi"],
        ),
        ("high_priority_review_v1", "Markets requiring high-priority desk review.", ["review"]),
        ("data_gap_review_v1", "Markets with coverage or freshness gaps.", ["data_gap"]),
        ("divergence_review_v1", "Comparable markets with divergence context.", ["divergence"]),
        ("pretrade_blocked_v1", "Markets with recent pre-trade block context.", ["pretrade"]),
    ]
    return [
        DeskWatchlist(
            watchlist_id=workbench_object_id(
                "desk_watchlist",
                {"version": WORKBENCH_VERSION, "name": name},
            ),
            name=name,
            description=description,
            created_at=created_at,
            is_active=True,
            market_ids=[],
            tags=tags,
            metadata={"workbench_version": WORKBENCH_VERSION},
        )
        for name, description, tags in definitions
    ]


def workbench_object_id(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}_{hash_payload(payload)[:24]}"


def hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_decision_card_input_hash(
    market_id: str,
    asof_timestamp: datetime,
    source_ref_ids: list[str],
) -> str:
    return hash_payload(
        {
            "version": DECISION_CARD_VERSION,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp,
            "source_ref_ids": sorted(source_ref_ids),
        }
    )


def compute_decision_card_output_hash(card: MarketDecisionCard) -> str:
    return hash_payload(
        {
            "version": DECISION_CARD_VERSION,
            "review_priority_score": card.review_priority_score,
            "review_reason_codes": sorted(card.review_reason_codes),
            "recommended_next_review_action": card.recommended_next_review_action.value,
            "summaries": {
                "liquidity": card.liquidity_summary,
                "quality": card.data_quality_summary,
                "rule": card.rule_summary,
                "integrity": card.integrity_summary,
                "equivalence": card.equivalence_summary,
                "divergence": card.divergence_summary,
                "pretrade": card.pretrade_summary,
                "paper": card.paper_summary,
                "research": card.research_summary,
                "scenario": card.scenario_summary,
                "data_gap": card.data_gap_summary,
            },
        }
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, Decimal | datetime):
        return str(value)
    return value

