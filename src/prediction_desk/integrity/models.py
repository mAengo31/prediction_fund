"""Pydantic models for replay-safe fast-lane integrity signals."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from prediction_desk.integrity.enums import (
    IntegrityActionHint,
    IntegrityRunStatus,
    SignalCategory,
    SignalSeverity,
)

FEATURE_VERSION = "market_feature_snapshot_v1"
SIGNAL_VERSION = "integrity_signal_v1"
ASSESSMENT_VERSION = "integrity_assessment_v1"
RUNNER_VERSION = "integrity_runner_v1"


class IntegrityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketFeatureSnapshot(IntegrityModel):
    feature_snapshot_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    latest_price_snapshot_id: str | None = None
    previous_price_snapshot_id: str | None = None
    latest_liquidity_snapshot_id: str | None = None
    previous_liquidity_snapshot_id: str | None = None
    latest_quality_report_id: str | None = None
    latest_rule_snapshot_id: str | None = None
    latest_rule_snapshot_hash: str | None = None
    latest_rule_diff_id: str | None = None
    price: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None
    spread: Decimal | None = None
    spread_bps: Decimal | None = None
    total_bid_depth: Decimal | None = None
    total_ask_depth: Decimal | None = None
    total_depth: Decimal | None = None
    book_imbalance: Decimal | None = None
    is_empty_book: bool = False
    is_crossed_book: bool = False
    has_missing_bid_or_ask: bool = False
    market_data_quality_score: int | None = None
    market_data_quality_reason_codes: list[str] = Field(default_factory=list)
    freshness_seconds: int | None = None
    price_change_abs: Decimal | None = None
    price_change_pct: Decimal | None = None
    mid_change_abs: Decimal | None = None
    spread_change_abs: Decimal | None = None
    depth_change_pct: Decimal | None = None
    rule_changed_recently: bool = False
    rule_change_age_seconds: int | None = None
    input_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegritySignal(IntegrityModel):
    integrity_signal_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    feature_snapshot_id: str
    signal_name: str
    signal_version: str
    category: SignalCategory
    severity: SignalSeverity
    score: int = Field(ge=0, le=100)
    action_hint: IntegrityActionHint
    reason_code: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrityAssessment(IntegrityModel):
    integrity_assessment_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    feature_snapshot_id: str
    signal_ids: list[str] = Field(default_factory=list)
    overall_risk_score: int = Field(ge=0, le=100)
    price_anomaly_score: int = Field(ge=0, le=100)
    liquidity_anomaly_score: int = Field(ge=0, le=100)
    freshness_risk_score: int = Field(ge=0, le=100)
    orderbook_structure_score: int = Field(ge=0, le=100)
    rule_change_risk_score: int = Field(ge=0, le=100)
    rule_price_coupling_score: int = Field(ge=0, le=100)
    data_quality_risk_score: int = Field(ge=0, le=100)
    manipulation_proxy_score: int = Field(ge=0, le=100)
    severity: SignalSeverity
    action_hint: IntegrityActionHint
    reason_codes: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrityRun(IntegrityModel):
    integrity_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: IntegrityRunStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    interval_seconds: int | None = None
    asof_timestamp: datetime | None = None
    market_ids: list[str] = Field(default_factory=list)
    max_steps: int
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    assessments_created: int = 0
    signals_created: int = 0
    errors_count: int = 0


class IntegrityRunSummary(IntegrityModel):
    summary_id: str
    integrity_run_id: str
    created_at: datetime
    total_assessments: int
    total_signals: int
    severity_counts: dict[str, int] = Field(default_factory=dict)
    category_counts: dict[str, int] = Field(default_factory=dict)
    action_hint_counts: dict[str, int] = Field(default_factory=dict)
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    no_trade_rate: Decimal
    manual_review_rate: Decimal
    passive_only_rate: Decimal
    allow_smaller_size_rate: Decimal
    markets_scanned: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrityRunConfig(IntegrityModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    interval_seconds: int | None = None
    market_ids: list[str] | None = None
    max_steps: int = Field(default=10000, gt=0)
    force: bool = False
    thresholds: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scan_window(self) -> IntegrityRunConfig:
        if self.asof_timestamp is None:
            if self.start_time is None or self.end_time is None or self.interval_seconds is None:
                raise ValueError("Provide asof_timestamp or start_time/end_time/interval_seconds.")
            if self.start_time > self.end_time:
                raise ValueError("start_time must be before or equal to end_time.")
            if self.interval_seconds <= 0:
                raise ValueError("interval_seconds must be positive.")
        return self


class IntegrityRunResult(IntegrityModel):
    run: IntegrityRun
    assessments: list[IntegrityAssessment] = Field(default_factory=list)
    summary: IntegrityRunSummary


class IntegrityAnalysis(IntegrityModel):
    feature_snapshot: MarketFeatureSnapshot
    signals: list[IntegritySignal] = Field(default_factory=list)
    assessment: IntegrityAssessment


class IntegrityAnalyzeRequest(IntegrityModel):
    market_ids: list[str] | None = None
    asof_timestamp: datetime | None = None
    force: bool = False
    thresholds: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketIntegrityAnalyzeRequest(IntegrityModel):
    asof_timestamp: datetime | None = None
    force: bool = False
    thresholds: dict[str, Any] = Field(default_factory=dict)


def compute_feature_input_hash(feature: MarketFeatureSnapshot) -> str:
    return hash_payload(
        {
            "asof_timestamp": feature.asof_timestamp,
            "feature_version": FEATURE_VERSION,
            "freshness_seconds": feature.freshness_seconds,
            "latest_liquidity_snapshot_id": feature.latest_liquidity_snapshot_id,
            "latest_price_snapshot_id": feature.latest_price_snapshot_id,
            "latest_quality_report_id": feature.latest_quality_report_id,
            "latest_rule_diff_id": feature.latest_rule_diff_id,
            "latest_rule_snapshot_hash": feature.latest_rule_snapshot_hash,
            "latest_rule_snapshot_id": feature.latest_rule_snapshot_id,
            "market_data_quality_reason_codes": sorted(
                feature.market_data_quality_reason_codes
            ),
            "market_data_quality_score": feature.market_data_quality_score,
            "market_id": feature.market_id,
            "previous_liquidity_snapshot_id": feature.previous_liquidity_snapshot_id,
            "previous_price_snapshot_id": feature.previous_price_snapshot_id,
            "values": _feature_values(feature),
        }
    )


def compute_signal_input_hash(feature: MarketFeatureSnapshot, signal_name: str) -> str:
    return hash_payload(
        {
            "feature_input_hash": feature.input_hash,
            "signal_name": signal_name,
            "signal_version": SIGNAL_VERSION,
        }
    )


def compute_signal_output_hash(signal: IntegritySignal) -> str:
    return hash_payload(
        {
            "action_hint": signal.action_hint.value,
            "category": signal.category.value,
            "evidence": signal.evidence,
            "feature_snapshot_id": signal.feature_snapshot_id,
            "message": signal.message,
            "reason_code": signal.reason_code,
            "score": signal.score,
            "severity": signal.severity.value,
            "signal_name": signal.signal_name,
            "signal_version": signal.signal_version,
        }
    )


def compute_assessment_input_hash(
    feature: MarketFeatureSnapshot, signals: list[IntegritySignal]
) -> str:
    return hash_payload(
        {
            "assessment_version": ASSESSMENT_VERSION,
            "feature_input_hash": feature.input_hash,
            "signal_output_hashes": sorted(signal.output_hash for signal in signals),
        }
    )


def compute_assessment_output_hash(assessment: IntegrityAssessment) -> str:
    return hash_payload(
        {
            "action_hint": assessment.action_hint.value,
            "category_scores": {
                "data_quality_risk_score": assessment.data_quality_risk_score,
                "freshness_risk_score": assessment.freshness_risk_score,
                "liquidity_anomaly_score": assessment.liquidity_anomaly_score,
                "manipulation_proxy_score": assessment.manipulation_proxy_score,
                "orderbook_structure_score": assessment.orderbook_structure_score,
                "price_anomaly_score": assessment.price_anomaly_score,
                "rule_change_risk_score": assessment.rule_change_risk_score,
                "rule_price_coupling_score": assessment.rule_price_coupling_score,
            },
            "overall_risk_score": assessment.overall_risk_score,
            "reason_codes": sorted(assessment.reason_codes),
            "severity": assessment.severity.value,
            "signal_ids": sorted(assessment.signal_ids),
        }
    )


def hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _feature_values(feature: MarketFeatureSnapshot) -> dict[str, Any]:
    return {
        "ask": feature.ask,
        "bid": feature.bid,
        "book_imbalance": feature.book_imbalance,
        "depth_change_pct": feature.depth_change_pct,
        "has_missing_bid_or_ask": feature.has_missing_bid_or_ask,
        "is_crossed_book": feature.is_crossed_book,
        "is_empty_book": feature.is_empty_book,
        "mid": feature.mid,
        "mid_change_abs": feature.mid_change_abs,
        "price": feature.price,
        "price_change_abs": feature.price_change_abs,
        "price_change_pct": feature.price_change_pct,
        "rule_change_age_seconds": feature.rule_change_age_seconds,
        "rule_changed_recently": feature.rule_changed_recently,
        "spread": feature.spread,
        "spread_bps": feature.spread_bps,
        "spread_change_abs": feature.spread_change_abs,
        "total_ask_depth": feature.total_ask_depth,
        "total_bid_depth": feature.total_bid_depth,
        "total_depth": feature.total_depth,
    }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value
