"""Pydantic models for replay-safe cross-venue divergence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prediction_desk.divergence.enums import (
    DivergenceActionHint,
    DivergenceRunStatus,
    DivergenceSignalCategory,
    DivergenceSignalSeverity,
    DivergenceStatus,
)

DIVERGENCE_SNAPSHOT_VERSION = "cross_venue_divergence_snapshot_v1"
DIVERGENCE_SIGNAL_VERSION = "cross_venue_divergence_signal_v1"
DIVERGENCE_ASSESSMENT_VERSION = "cross_venue_divergence_assessment_v1"
DIVERGENCE_RUNNER_VERSION = "cross_venue_divergence_runner_v1"


class DivergenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CrossVenueDivergenceSnapshot(DivergenceModel):
    divergence_snapshot_id: str
    equivalence_assessment_id: str
    outcome_mapping_id: str | None = None
    left_market_id: str
    right_market_id: str
    left_venue_id: str | None = None
    right_venue_id: str | None = None
    left_outcome_id: str | None = None
    right_outcome_id: str | None = None
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    equivalence_status: str
    comparison_permission: str
    equivalence_score: int | None = None
    equivalence_confidence_score: int | None = None
    outcome_relation: str | None = None
    left_price_snapshot_id: str | None = None
    right_price_snapshot_id: str | None = None
    left_liquidity_snapshot_id: str | None = None
    right_liquidity_snapshot_id: str | None = None
    left_quality_report_id: str | None = None
    right_quality_report_id: str | None = None
    left_integrity_assessment_id: str | None = None
    right_integrity_assessment_id: str | None = None
    left_price: Decimal | None = None
    right_price_raw: Decimal | None = None
    right_price_aligned: Decimal | None = None
    left_mid: Decimal | None = None
    right_mid_raw: Decimal | None = None
    right_mid_aligned: Decimal | None = None
    left_bid: Decimal | None = None
    left_ask: Decimal | None = None
    right_bid_raw: Decimal | None = None
    right_ask_raw: Decimal | None = None
    right_bid_aligned: Decimal | None = None
    right_ask_aligned: Decimal | None = None
    signed_mid_gap: Decimal | None = None
    absolute_mid_gap: Decimal | None = None
    signed_price_gap: Decimal | None = None
    absolute_price_gap: Decimal | None = None
    gap_bps: Decimal | None = None
    combined_spread: Decimal | None = None
    spread_adjusted_gap: Decimal | None = None
    left_spread: Decimal | None = None
    right_spread: Decimal | None = None
    left_total_depth: Decimal | None = None
    right_total_depth: Decimal | None = None
    min_total_depth: Decimal | None = None
    left_quality_score: int | None = None
    right_quality_score: int | None = None
    left_integrity_risk_score: int | None = None
    right_integrity_risk_score: int | None = None
    stale_side: str | None = None
    weaker_side: str | None = None
    comparable: bool = False
    comparable_with_haircut: bool = False
    manual_review_required: bool = False
    do_not_compare: bool = False
    missing_price_data: bool = False
    missing_liquidity_data: bool = False
    stale_data: bool = False
    low_quality_data: bool = False
    high_integrity_risk: bool = False
    wide_spread: bool = False
    one_sided_or_empty_book: bool = False
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceSignal(DivergenceModel):
    divergence_signal_id: str
    divergence_snapshot_id: str
    equivalence_assessment_id: str
    left_market_id: str
    right_market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    signal_name: str
    signal_version: str
    category: DivergenceSignalCategory
    severity: DivergenceSignalSeverity
    score: int = Field(ge=0, le=100)
    action_hint: DivergenceActionHint
    reason_code: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceAssessment(DivergenceModel):
    divergence_assessment_id: str
    divergence_snapshot_id: str
    equivalence_assessment_id: str
    outcome_mapping_id: str | None = None
    left_market_id: str
    right_market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    signal_ids: list[str] = Field(default_factory=list)
    overall_divergence_score: int = Field(ge=0, le=100)
    price_divergence_score: int = Field(ge=0, le=100)
    spread_adjusted_score: int = Field(ge=0, le=100)
    persistence_score: int = Field(ge=0, le=100)
    stale_side_score: int = Field(ge=0, le=100)
    low_liquidity_score: int = Field(ge=0, le=100)
    low_data_quality_score: int = Field(ge=0, le=100)
    integrity_context_score: int = Field(ge=0, le=100)
    equivalence_context_score: int = Field(ge=0, le=100)
    status: DivergenceStatus
    severity: DivergenceSignalSeverity
    action_hint: DivergenceActionHint
    reason_codes: list[str] = Field(default_factory=list)
    absolute_mid_gap: Decimal | None = None
    spread_adjusted_gap: Decimal | None = None
    gap_bps: Decimal | None = None
    comparison_permission: str
    equivalence_score: int | None = None
    equivalence_confidence_score: int | None = None
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceRun(DivergenceModel):
    divergence_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: DivergenceRunStatus
    asof_timestamp: datetime
    equivalence_assessment_ids: list[str] = Field(default_factory=list)
    market_ids: list[str] = Field(default_factory=list)
    max_pairs: int
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    snapshots_created: int = 0
    signals_created: int = 0
    assessments_created: int = 0
    errors_count: int = 0


class CrossVenueDivergenceRunSummary(DivergenceModel):
    summary_id: str
    divergence_run_id: str
    created_at: datetime
    total_snapshots: int
    total_signals: int
    total_assessments: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    action_hint_counts: dict[str, int] = Field(default_factory=dict)
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    watch_rate: Decimal
    material_divergence_rate: Decimal
    needs_review_rate: Decimal
    do_not_compare_rate: Decimal
    markets_compared: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceAnalysis(DivergenceModel):
    snapshot: CrossVenueDivergenceSnapshot
    signals: list[CrossVenueDivergenceSignal] = Field(default_factory=list)
    assessment: CrossVenueDivergenceAssessment


class DivergenceAnalyzeRequest(DivergenceModel):
    equivalence_assessment_id: str | None = None
    market_id: str | None = None
    asof_timestamp: datetime | None = None
    outcome_mapping_id: str | None = None
    force: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceRunConfig(DivergenceModel):
    name: str | None = None
    asof_timestamp: datetime
    equivalence_assessment_ids: list[str] | None = None
    market_ids: list[str] | None = None
    max_pairs: int = Field(default=10000, gt=0)
    force: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceRunRequest(DivergenceModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    equivalence_assessment_ids: list[str] | None = None
    market_ids: list[str] | None = None
    max_pairs: int = Field(default=10000, gt=0)
    force: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CrossVenueDivergenceRunResult(DivergenceModel):
    run: CrossVenueDivergenceRun
    analyses: list[CrossVenueDivergenceAnalysis] = Field(default_factory=list)
    summary: CrossVenueDivergenceRunSummary


def compute_snapshot_input_hash(snapshot: CrossVenueDivergenceSnapshot) -> str:
    return hash_payload(
        {
            "asof_timestamp": snapshot.asof_timestamp,
            "divergence_snapshot_version": DIVERGENCE_SNAPSHOT_VERSION,
            "equivalence_assessment_id": snapshot.equivalence_assessment_id,
            "comparison_permission": snapshot.comparison_permission,
            "equivalence_status": snapshot.equivalence_status,
            "left_integrity_assessment_id": snapshot.left_integrity_assessment_id,
            "left_liquidity_snapshot_id": snapshot.left_liquidity_snapshot_id,
            "left_market_id": snapshot.left_market_id,
            "left_price_snapshot_id": snapshot.left_price_snapshot_id,
            "left_quality_report_id": snapshot.left_quality_report_id,
            "outcome_mapping_id": snapshot.outcome_mapping_id,
            "outcome_relation": snapshot.outcome_relation,
            "right_integrity_assessment_id": snapshot.right_integrity_assessment_id,
            "right_liquidity_snapshot_id": snapshot.right_liquidity_snapshot_id,
            "right_market_id": snapshot.right_market_id,
            "right_price_snapshot_id": snapshot.right_price_snapshot_id,
            "right_quality_report_id": snapshot.right_quality_report_id,
            "aligned_values": _snapshot_aligned_values(snapshot),
        }
    )


def compute_snapshot_output_hash(snapshot: CrossVenueDivergenceSnapshot) -> str:
    return hash_payload(
        {
            "divergence_snapshot_version": DIVERGENCE_SNAPSHOT_VERSION,
            "flags": _snapshot_flags(snapshot),
            "values": _snapshot_gap_values(snapshot),
            "weaker_side": snapshot.weaker_side,
            "stale_side": snapshot.stale_side,
        }
    )


def compute_signal_input_hash(
    snapshot: CrossVenueDivergenceSnapshot,
    signal_name: str,
) -> str:
    return hash_payload(
        {
            "divergence_snapshot_input_hash": snapshot.input_hash,
            "signal_name": signal_name,
            "signal_version": DIVERGENCE_SIGNAL_VERSION,
        }
    )


def compute_signal_output_hash(signal: CrossVenueDivergenceSignal) -> str:
    return hash_payload(
        {
            "action_hint": signal.action_hint.value,
            "category": signal.category.value,
            "evidence": signal.evidence,
            "reason_code": signal.reason_code,
            "score": signal.score,
            "severity": signal.severity.value,
            "signal_name": signal.signal_name,
            "signal_version": signal.signal_version,
        }
    )


def compute_assessment_input_hash(
    snapshot: CrossVenueDivergenceSnapshot,
    signals: list[CrossVenueDivergenceSignal],
) -> str:
    return hash_payload(
        {
            "assessment_version": DIVERGENCE_ASSESSMENT_VERSION,
            "snapshot_output_hash": snapshot.output_hash,
            "signal_output_hashes": sorted(signal.output_hash for signal in signals),
        }
    )


def compute_assessment_output_hash(assessment: CrossVenueDivergenceAssessment) -> str:
    return hash_payload(
        {
            "action_hint": assessment.action_hint.value,
            "assessment_version": DIVERGENCE_ASSESSMENT_VERSION,
            "overall_divergence_score": assessment.overall_divergence_score,
            "reason_codes": sorted(assessment.reason_codes),
            "severity": assessment.severity.value,
            "status": assessment.status.value,
        }
    )


def hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _snapshot_aligned_values(snapshot: CrossVenueDivergenceSnapshot) -> dict[str, Any]:
    return {
        "left_ask": snapshot.left_ask,
        "left_bid": snapshot.left_bid,
        "left_mid": snapshot.left_mid,
        "left_price": snapshot.left_price,
        "right_ask_aligned": snapshot.right_ask_aligned,
        "right_bid_aligned": snapshot.right_bid_aligned,
        "right_mid_aligned": snapshot.right_mid_aligned,
        "right_price_aligned": snapshot.right_price_aligned,
    }


def _snapshot_gap_values(snapshot: CrossVenueDivergenceSnapshot) -> dict[str, Any]:
    return {
        "absolute_mid_gap": snapshot.absolute_mid_gap,
        "absolute_price_gap": snapshot.absolute_price_gap,
        "combined_spread": snapshot.combined_spread,
        "gap_bps": snapshot.gap_bps,
        "signed_mid_gap": snapshot.signed_mid_gap,
        "signed_price_gap": snapshot.signed_price_gap,
        "spread_adjusted_gap": snapshot.spread_adjusted_gap,
    }


def _snapshot_flags(snapshot: CrossVenueDivergenceSnapshot) -> dict[str, bool]:
    return {
        "comparable": snapshot.comparable,
        "comparable_with_haircut": snapshot.comparable_with_haircut,
        "do_not_compare": snapshot.do_not_compare,
        "high_integrity_risk": snapshot.high_integrity_risk,
        "low_quality_data": snapshot.low_quality_data,
        "manual_review_required": snapshot.manual_review_required,
        "missing_liquidity_data": snapshot.missing_liquidity_data,
        "missing_price_data": snapshot.missing_price_data,
        "one_sided_or_empty_book": snapshot.one_sided_or_empty_book,
        "stale_data": snapshot.stale_data,
        "wide_spread": snapshot.wide_spread,
    }

