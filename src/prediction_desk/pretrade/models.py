"""Pydantic models for deterministic pre-trade admissibility checks."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from prediction_desk.pretrade.enums import (
    ExposureSource,
    PreTradeAction,
    PreTradeRunStatus,
    RestrictionScopeType,
    RestrictionType,
    StrategyContext,
    TradeIntentType,
    TradeSide,
)

PRETRADE_POLICY_VERSION = "pretrade_policy_v1"
PRETRADE_INPUT_VERSION = "pretrade_input_snapshot_v1"
PRETRADE_DECISION_VERSION = "pretrade_decision_v1"
PRETRADE_RUNNER_VERSION = "pretrade_runner_v1"
DEFAULT_PRETRADE_POLICY_ID = "pretrade_policy_default_pretrade_policy_v1"
DEFAULT_PRETRADE_POLICY_NAME = "default_pretrade_policy"
DEFAULT_PRETRADE_POLICY_VERSION = "v1"


class PreTradeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TradeIntent(PreTradeModel):
    trade_intent_id: str
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    strategy_context: StrategyContext
    side: TradeSide
    intent_type: TradeIntentType
    requested_price: Decimal | None = None
    requested_size_units: Decimal = Field(gt=Decimal("0"))
    requested_notional_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    asof_timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("requested_price")
    @classmethod
    def _probability_price(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not (Decimal("0") <= value <= Decimal("1")):
            raise ValueError("requested_price must be between 0 and 1")
        return value


class PreTradePolicy(PreTradeModel):
    policy_id: str
    policy_name: str
    policy_version: str
    created_at: datetime
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    is_active: bool = True
    max_order_size_units: Decimal
    max_market_exposure_units: Decimal
    max_event_exposure_units: Decimal
    max_venue_exposure_units: Decimal
    max_strategy_exposure_units: Decimal | None = None
    allow_unknown_exposure: bool
    require_active_market: bool
    require_rule_snapshot: bool
    require_trust_verdict: bool
    require_market_data_quality: bool
    min_market_data_quality_score: int = Field(ge=0, le=100)
    max_resolution_risk_score: int = Field(ge=0, le=100)
    max_integrity_risk_score: int = Field(ge=0, le=100)
    max_divergence_score_without_review: int = Field(ge=0, le=100)
    max_staleness_seconds: int
    max_spread: Decimal | None = None
    max_spread_bps: Decimal | None = None
    allow_manual_review_markets: bool
    allow_comparable_with_haircut: bool
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketRestrictionRule(PreTradeModel):
    restriction_id: str
    created_at: datetime
    is_active: bool = True
    restriction_type: RestrictionType
    scope_type: RestrictionScopeType
    venue_id: str | None = None
    venue_name: str | None = None
    market_id: str | None = None
    event_id: str | None = None
    category: str | None = None
    title_pattern: str | None = None
    reason_code: str
    description: str | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExposureSnapshot(PreTradeModel):
    exposure_snapshot_id: str
    asof_timestamp: datetime
    created_at: datetime
    source: ExposureSource
    market_id: str | None = None
    event_id: str | None = None
    venue_id: str | None = None
    strategy_context: str | None = None
    market_exposure_units: Decimal = Field(ge=Decimal("0"))
    event_exposure_units: Decimal = Field(ge=Decimal("0"))
    venue_exposure_units: Decimal = Field(ge=Decimal("0"))
    strategy_exposure_units: Decimal | None = Field(default=None, ge=Decimal("0"))
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeInputSnapshot(PreTradeModel):
    input_snapshot_id: str
    trade_intent_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    market_status: str | None = None
    event_id: str | None = None
    venue_id: str | None = None
    latest_rule_snapshot_id: str | None = None
    latest_rule_snapshot_hash: str | None = None
    latest_trust_verdict_id: str | None = None
    latest_quality_report_id: str | None = None
    latest_integrity_assessment_id: str | None = None
    latest_equivalence_assessment_ids: list[str] = Field(default_factory=list)
    latest_divergence_assessment_ids: list[str] = Field(default_factory=list)
    latest_price_snapshot_id: str | None = None
    latest_liquidity_snapshot_id: str | None = None
    exposure_snapshot_id: str | None = None
    policy_id: str
    restriction_ids: list[str] = Field(default_factory=list)
    resolution_risk_score: int | None = Field(default=None, ge=0, le=100)
    market_data_quality_score: int | None = Field(default=None, ge=0, le=100)
    integrity_risk_score: int | None = Field(default=None, ge=0, le=100)
    max_divergence_score: int | None = Field(default=None, ge=0, le=100)
    comparable_market_count: int = 0
    manual_review_equivalence_count: int = 0
    do_not_compare_equivalence_count: int = 0
    divergence_watch_count: int = 0
    material_divergence_count: int = 0
    divergence_needs_review_count: int = 0
    divergence_do_not_compare_count: int = 0
    current_market_exposure_units: Decimal | None = None
    current_event_exposure_units: Decimal | None = None
    current_venue_exposure_units: Decimal | None = None
    current_strategy_exposure_units: Decimal | None = None
    input_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeDecision(PreTradeModel):
    pretrade_decision_id: str
    trade_intent_id: str
    input_snapshot_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    policy_id: str
    policy_name: str
    policy_version: str
    action: PreTradeAction
    allowed_size_multiplier: Decimal
    requested_size_units: Decimal
    max_allowed_size_units: Decimal
    final_allowed_size_units: Decimal
    passive_only: bool
    manual_review_required: bool
    hard_blocked: bool
    composite_risk_score: int = Field(ge=0, le=100)
    resolution_risk_score: int | None = Field(default=None, ge=0, le=100)
    market_data_quality_score: int | None = Field(default=None, ge=0, le=100)
    integrity_risk_score: int | None = Field(default=None, ge=0, le=100)
    max_divergence_score: int | None = Field(default=None, ge=0, le=100)
    exposure_risk_score: int | None = Field(default=None, ge=0, le=100)
    hard_blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeRun(PreTradeModel):
    pretrade_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: PreTradeRunStatus
    asof_timestamp: datetime
    policy_id: str | None = None
    market_ids: list[str] = Field(default_factory=list)
    max_checks: int
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    decisions_created: int = 0
    errors_count: int = 0


class PreTradeRunSummary(PreTradeModel):
    summary_id: str
    pretrade_run_id: str
    created_at: datetime
    total_decisions: int
    action_counts: dict[str, int] = Field(default_factory=dict)
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    no_trade_rate: Decimal
    manual_review_rate: Decimal
    passive_only_rate: Decimal
    allow_smaller_size_rate: Decimal
    allow_rate: Decimal
    hard_block_rate: Decimal
    total_requested_size_units: Decimal
    total_final_allowed_size_units: Decimal
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeCheckResponse(PreTradeModel):
    trade_intent: TradeIntent
    input_snapshot: PreTradeInputSnapshot
    decision: PreTradeDecision


class PreTradeCheckRequest(PreTradeModel):
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    strategy_context: StrategyContext = StrategyContext.RESEARCH
    side: TradeSide = TradeSide.BUY
    intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY
    requested_price: Decimal | None = None
    requested_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    requested_notional_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    asof_timestamp: datetime | None = None
    policy_id: str | None = None
    force_recompute_context: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeCheckMarketRequest(PreTradeModel):
    asof_timestamp: datetime | None = None
    policy_id: str | None = None
    strategy_context: StrategyContext = StrategyContext.RESEARCH
    requested_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))


class PreTradeRunConfig(PreTradeModel):
    name: str | None = None
    asof_timestamp: datetime
    policy_id: str | None = None
    market_ids: list[str] | None = None
    max_checks: int = Field(default=10000, gt=0)
    default_requested_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    strategy_context: StrategyContext = StrategyContext.RESEARCH
    intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeRunRequest(PreTradeModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    policy_id: str | None = None
    market_ids: list[str] | None = None
    max_checks: int = Field(default=10000, gt=0)
    default_requested_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    strategy_context: StrategyContext = StrategyContext.RESEARCH
    intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreTradeRunResult(PreTradeModel):
    run: PreTradeRun
    decisions: list[PreTradeDecision] = Field(default_factory=list)
    summary: PreTradeRunSummary


class MarketRestrictionRuleCreate(PreTradeModel):
    is_active: bool = True
    restriction_type: RestrictionType
    scope_type: RestrictionScopeType
    venue_id: str | None = None
    venue_name: str | None = None
    market_id: str | None = None
    event_id: str | None = None
    category: str | None = None
    title_pattern: str | None = None
    reason_code: str
    description: str | None = None
    effective_from: datetime | None = None
    effective_until: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExposureSnapshotCreate(PreTradeModel):
    asof_timestamp: datetime | None = None
    source: ExposureSource = ExposureSource.MANUAL
    market_id: str | None = None
    event_id: str | None = None
    venue_id: str | None = None
    strategy_context: str | None = None
    market_exposure_units: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    event_exposure_units: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    venue_exposure_units: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    strategy_exposure_units: Decimal | None = Field(default=None, ge=Decimal("0"))
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_trade_intent_id(intent: TradeIntent) -> str:
    return f"trade_intent_{hash_payload(_intent_hash_payload(intent))[:24]}"


def compute_input_hash(snapshot: PreTradeInputSnapshot) -> str:
    return hash_payload(
        {
            "version": PRETRADE_INPUT_VERSION,
            "trade_intent_id": snapshot.trade_intent_id,
            "market_id": snapshot.market_id,
            "asof_timestamp": snapshot.asof_timestamp,
            "market_status": snapshot.market_status,
            "latest_rule_snapshot_id": snapshot.latest_rule_snapshot_id,
            "latest_rule_snapshot_hash": snapshot.latest_rule_snapshot_hash,
            "latest_trust_verdict_id": snapshot.latest_trust_verdict_id,
            "latest_quality_report_id": snapshot.latest_quality_report_id,
            "latest_integrity_assessment_id": snapshot.latest_integrity_assessment_id,
            "latest_equivalence_assessment_ids": sorted(
                snapshot.latest_equivalence_assessment_ids
            ),
            "latest_divergence_assessment_ids": sorted(
                snapshot.latest_divergence_assessment_ids
            ),
            "latest_price_snapshot_id": snapshot.latest_price_snapshot_id,
            "latest_liquidity_snapshot_id": snapshot.latest_liquidity_snapshot_id,
            "exposure_snapshot_id": snapshot.exposure_snapshot_id,
            "policy_id": snapshot.policy_id,
            "restriction_ids": sorted(snapshot.restriction_ids),
            "scores": {
                "resolution_risk_score": snapshot.resolution_risk_score,
                "market_data_quality_score": snapshot.market_data_quality_score,
                "integrity_risk_score": snapshot.integrity_risk_score,
                "max_divergence_score": snapshot.max_divergence_score,
            },
            "exposure": {
                "market": snapshot.current_market_exposure_units,
                "event": snapshot.current_event_exposure_units,
                "venue": snapshot.current_venue_exposure_units,
                "strategy": snapshot.current_strategy_exposure_units,
            },
        }
    )


def compute_decision_output_hash(decision: PreTradeDecision) -> str:
    return hash_payload(
        {
            "version": PRETRADE_DECISION_VERSION,
            "action": decision.action.value,
            "allowed_size_multiplier": decision.allowed_size_multiplier,
            "requested_size_units": decision.requested_size_units,
            "max_allowed_size_units": decision.max_allowed_size_units,
            "final_allowed_size_units": decision.final_allowed_size_units,
            "passive_only": decision.passive_only,
            "manual_review_required": decision.manual_review_required,
            "hard_blocked": decision.hard_blocked,
            "composite_risk_score": decision.composite_risk_score,
            "exposure_risk_score": decision.exposure_risk_score,
            "hard_blockers": sorted(decision.hard_blockers),
            "warnings": sorted(decision.warnings),
            "reason_codes": sorted(decision.reason_codes),
            "input_hash": decision.input_hash,
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


def _intent_hash_payload(intent: TradeIntent) -> dict[str, Any]:
    return {
        "market_id": intent.market_id,
        "outcome_id": intent.outcome_id,
        "venue_id": intent.venue_id,
        "strategy_context": intent.strategy_context.value,
        "side": intent.side.value,
        "intent_type": intent.intent_type.value,
        "requested_price": intent.requested_price,
        "requested_size_units": intent.requested_size_units,
        "requested_notional_usd": intent.requested_notional_usd,
        "asof_timestamp": intent.asof_timestamp,
        "metadata": intent.metadata,
    }

