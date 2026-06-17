"""Pydantic models for deterministic strategy research."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prediction_desk.pretrade.enums import StrategyContext, TradeIntentType, TradeSide
from prediction_desk.research.enums import (
    ResearchActionBias,
    ResearchFeatureFamily,
    ResearchFeatureSource,
    ResearchRunStatus,
    ResearchSignalType,
    ResearchStrategyFamily,
)

RESEARCH_STRATEGY_VERSION = "research_strategy_definition_v1"
RESEARCH_FEATURE_VERSION = "research_feature_snapshot_v1"
RESEARCH_SIGNAL_VERSION = "research_signal_v1"
RESEARCH_PROPOSAL_VERSION = "research_intent_proposal_v1"
RESEARCH_TRACE_VERSION = "research_decision_trace_v1"
RESEARCH_RUNNER_VERSION = "research_runner_v1"

BASELINE_STRATEGY_ID = "research_strategy_baseline_research_only_v1"
TRUST_ALLOW_STRATEGY_ID = "research_strategy_trust_verdict_allow_filter_v1"
INTEGRITY_PASS_STRATEGY_ID = "research_strategy_integrity_pass_filter_v1"
DIVERGENCE_STRATEGY_ID = "research_strategy_divergence_research_hypothesis_v1"
COMPOSITE_STRATEGY_ID = "research_strategy_composite_conservative_research_v1"


class ResearchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResearchStrategyDefinition(ResearchModel):
    strategy_id: str
    strategy_name: str
    strategy_version: str
    created_at: datetime
    is_active: bool = True
    family: ResearchStrategyFamily
    description: str | None = None
    requires_pretrade: bool = True
    allows_paper_simulation: bool = True
    default_requested_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    default_intent_type: str = TradeIntentType.RESEARCH_ONLY.value
    default_strategy_context: str = StrategyContext.RESEARCH.value
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchFeatureSnapshot(ResearchModel):
    research_feature_snapshot_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    feature_source: ResearchFeatureSource
    feature_family: ResearchFeatureFamily
    source_ref_ids: list[str] = Field(default_factory=list)
    values: dict[str, Any] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchSignal(ResearchModel):
    research_signal_id: str
    strategy_id: str
    strategy_name: str
    strategy_version: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    signal_type: ResearchSignalType
    signal_strength_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    action_bias: ResearchActionBias
    reason_codes: list[str] = Field(default_factory=list)
    source_feature_ids: list[str] = Field(default_factory=list)
    source_ref_ids: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchIntentProposal(ResearchModel):
    proposal_id: str
    strategy_id: str
    strategy_name: str
    strategy_version: str
    research_signal_id: str | None = None
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    side: TradeSide
    intent_type: str
    strategy_context: str
    requested_price: Decimal | None = None
    requested_size_units: Decimal = Field(gt=Decimal("0"))
    requested_notional_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    pretrade_required: bool = True
    paper_simulation_allowed: bool = True
    reason_codes: list[str] = Field(default_factory=list)
    source_signal_ids: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("requested_price")
    @classmethod
    def _probability_price(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not (Decimal("0") <= value <= Decimal("1")):
            raise ValueError("requested_price must be between 0 and 1")
        return value


class ResearchDecisionTrace(ResearchModel):
    trace_id: str
    research_run_id: str | None = None
    strategy_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    research_signal_id: str | None = None
    proposal_id: str | None = None
    trade_intent_id: str | None = None
    pretrade_decision_id: str | None = None
    paper_order_id: str | None = None
    paper_fill_ids: list[str] = Field(default_factory=list)
    paper_position_snapshot_id: str | None = None
    paper_portfolio_snapshot_id: str | None = None
    pretrade_action: str | None = None
    paper_order_status: str | None = None
    filled_size_units_simulated: Decimal = Decimal("0")
    avg_fill_price_simulated: Decimal | None = None
    reason_codes: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchRun(ResearchModel):
    research_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: ResearchRunStatus
    start_time: datetime
    end_time: datetime
    interval_seconds: int
    strategy_ids: list[str] = Field(default_factory=list)
    market_ids: list[str] = Field(default_factory=list)
    max_steps: int
    max_proposals: int
    enable_paper_simulation: bool = True
    paper_policy_id: str | None = None
    initial_cash_simulated: Decimal | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    signals_created: int = 0
    proposals_created: int = 0
    pretrade_checks_created: int = 0
    paper_orders_created: int = 0
    paper_fills_created: int = 0
    errors_count: int = 0


class ResearchRunSummary(ResearchModel):
    summary_id: str
    research_run_id: str
    created_at: datetime
    total_steps: int
    total_signals: int
    total_proposals: int
    total_pretrade_checks: int
    total_paper_orders: int
    total_paper_fills: int
    strategy_counts: dict[str, int] = Field(default_factory=dict)
    signal_type_counts: dict[str, int] = Field(default_factory=dict)
    pretrade_action_counts: dict[str, int] = Field(default_factory=dict)
    paper_order_status_counts: dict[str, int] = Field(default_factory=dict)
    reason_code_counts: dict[str, int] = Field(default_factory=dict)
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    total_requested_size_units: Decimal = Decimal("0")
    total_pretrade_allowed_size_units: Decimal = Decimal("0")
    total_filled_size_units_simulated: Decimal = Decimal("0")
    final_portfolio_equity_simulated: Decimal | None = None
    final_realized_pnl_simulated: Decimal | None = None
    final_unrealized_pnl_simulated: Decimal | None = None
    proposal_to_pretrade_pass_rate: Decimal = Decimal("0")
    paper_fill_rate: Decimal = Decimal("0")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchAttributionReport(ResearchModel):
    attribution_report_id: str
    research_run_id: str
    created_at: datetime
    by_strategy: dict[str, Any] = Field(default_factory=dict)
    by_market: dict[str, Any] = Field(default_factory=dict)
    by_venue: dict[str, Any] = Field(default_factory=dict)
    by_reason_code: dict[str, Any] = Field(default_factory=dict)
    by_signal_type: dict[str, Any] = Field(default_factory=dict)
    by_pretrade_action: dict[str, Any] = Field(default_factory=dict)
    by_paper_order_status: dict[str, Any] = Field(default_factory=dict)
    simulated_pnl_by_strategy: dict[str, Any] = Field(default_factory=dict)
    simulated_pnl_by_market: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchRunConfig(ResearchModel):
    name: str | None = None
    start_time: datetime
    end_time: datetime
    interval_seconds: int = Field(gt=0)
    strategy_ids: list[str] | None = None
    market_ids: list[str] | None = None
    max_steps: int = Field(default=10000, gt=0)
    max_proposals: int = Field(default=10000, gt=0)
    enable_paper_simulation: bool = True
    paper_policy_id: str | None = None
    initial_cash_simulated: Decimal | None = Decimal("1000")
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_window(self) -> ResearchRunConfig:
        if self.start_time > self.end_time:
            raise ValueError("start_time must be before or equal to end_time")
        return self


class ResearchRunRequest(ResearchModel):
    name: str | None = None
    start_time: datetime
    end_time: datetime
    interval_seconds: int = Field(default=3600, gt=0)
    strategy_ids: list[str] | None = None
    market_ids: list[str] | None = None
    max_steps: int = Field(default=10000, gt=0)
    max_proposals: int = Field(default=10000, gt=0)
    enable_paper_simulation: bool = True
    paper_policy_id: str | None = None
    initial_cash_simulated: Decimal | None = Decimal("1000")
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchRunResult(ResearchModel):
    run: ResearchRun
    signals: list[ResearchSignal] = Field(default_factory=list)
    proposals: list[ResearchIntentProposal] = Field(default_factory=list)
    traces: list[ResearchDecisionTrace] = Field(default_factory=list)
    summary: ResearchRunSummary
    attribution: ResearchAttributionReport


class ResearchFeatureBuildRequest(ResearchModel):
    market_id: str
    asof_timestamp: datetime | None = None
    include_sources: list[ResearchFeatureSource] | None = None
    force: bool = False


class ResearchSignalsGenerateRequest(ResearchModel):
    market_id: str
    asof_timestamp: datetime | None = None
    strategy_ids: list[str] | None = None
    force: bool = False


class ResearchProposalsGenerateRequest(ResearchModel):
    market_id: str
    asof_timestamp: datetime | None = None
    strategy_ids: list[str] | None = None
    force: bool = False


class ResearchProposalEvaluateRequest(ResearchModel):
    enable_paper_simulation: bool = True
    paper_policy_id: str | None = None


class ResearchLatestResponse(ResearchModel):
    signals: list[ResearchSignal] = Field(default_factory=list)
    proposals: list[ResearchIntentProposal] = Field(default_factory=list)
    traces: list[ResearchDecisionTrace] = Field(default_factory=list)


def compute_strategy_id(strategy_name: str, strategy_version: str) -> str:
    return f"research_strategy_{strategy_name}_{strategy_version}".replace("__", "_")


def compute_feature_input_hash(feature: ResearchFeatureSnapshot) -> str:
    return hash_payload(
        {
            "version": RESEARCH_FEATURE_VERSION,
            "market_id": feature.market_id,
            "asof_timestamp": feature.asof_timestamp,
            "feature_source": feature.feature_source.value,
            "feature_family": feature.feature_family.value,
            "source_ref_ids": sorted(feature.source_ref_ids),
        }
    )


def compute_feature_output_hash(feature: ResearchFeatureSnapshot) -> str:
    return hash_payload(
        {
            "version": RESEARCH_FEATURE_VERSION,
            "reason_codes": sorted(feature.reason_codes),
            "source_ref_ids": sorted(feature.source_ref_ids),
            "values": feature.values,
        }
    )


def compute_signal_input_hash(
    strategy: ResearchStrategyDefinition,
    market_id: str,
    asof_timestamp: datetime,
    feature_hashes: list[str],
    signal_type: ResearchSignalType,
) -> str:
    return hash_payload(
        {
            "version": RESEARCH_SIGNAL_VERSION,
            "strategy_id": strategy.strategy_id,
            "strategy_version": strategy.strategy_version,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp,
            "feature_hashes": sorted(feature_hashes),
            "signal_type": signal_type.value,
        }
    )


def compute_signal_output_hash(signal: ResearchSignal) -> str:
    return hash_payload(
        {
            "version": RESEARCH_SIGNAL_VERSION,
            "action_bias": signal.action_bias.value,
            "confidence_score": signal.confidence_score,
            "reason_codes": sorted(signal.reason_codes),
            "signal_strength_score": signal.signal_strength_score,
            "signal_type": signal.signal_type.value,
            "source_feature_ids": sorted(signal.source_feature_ids),
            "source_ref_ids": sorted(signal.source_ref_ids),
            "metadata": signal.metadata,
        }
    )


def compute_proposal_input_hash(
    strategy: ResearchStrategyDefinition,
    signal: ResearchSignal | None,
    market_id: str,
    asof_timestamp: datetime,
    source_signal_ids: list[str],
) -> str:
    return hash_payload(
        {
            "version": RESEARCH_PROPOSAL_VERSION,
            "strategy_id": strategy.strategy_id,
            "strategy_version": strategy.strategy_version,
            "signal_output_hash": signal.output_hash if signal else None,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp,
            "source_signal_ids": sorted(source_signal_ids),
        }
    )


def compute_proposal_output_hash(proposal: ResearchIntentProposal) -> str:
    return hash_payload(
        {
            "version": RESEARCH_PROPOSAL_VERSION,
            "intent_type": proposal.intent_type,
            "market_id": proposal.market_id,
            "outcome_id": proposal.outcome_id,
            "paper_simulation_allowed": proposal.paper_simulation_allowed,
            "pretrade_required": proposal.pretrade_required,
            "reason_codes": sorted(proposal.reason_codes),
            "requested_price": proposal.requested_price,
            "requested_size_units": proposal.requested_size_units,
            "side": proposal.side.value,
            "strategy_context": proposal.strategy_context,
            "venue_id": proposal.venue_id,
        }
    )


def compute_trace_input_hash(
    proposal: ResearchIntentProposal,
    pretrade_decision_id: str | None,
    paper_order_id: str | None,
    paper_fill_ids: list[str],
) -> str:
    return hash_payload(
        {
            "version": RESEARCH_TRACE_VERSION,
            "proposal_id": proposal.proposal_id,
            "proposal_output_hash": proposal.output_hash,
            "pretrade_decision_id": pretrade_decision_id,
            "paper_order_id": paper_order_id,
            "paper_fill_ids": sorted(paper_fill_ids),
        }
    )


def compute_trace_output_hash(trace: ResearchDecisionTrace) -> str:
    return hash_payload(
        {
            "version": RESEARCH_TRACE_VERSION,
            "avg_fill_price_simulated": trace.avg_fill_price_simulated,
            "filled_size_units_simulated": trace.filled_size_units_simulated,
            "paper_order_status": trace.paper_order_status,
            "pretrade_action": trace.pretrade_action,
            "reason_codes": sorted(trace.reason_codes),
        }
    )


def research_object_id(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}_{hash_payload(payload)[:24]}"


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
