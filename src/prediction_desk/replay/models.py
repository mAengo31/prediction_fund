"""Pydantic models for point-in-time replay."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from prediction_desk.replay.enums import ReplayRunStatus


class ReplayModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReplayRunConfig(ReplayModel):
    name: str | None = None
    policy_name: str
    start_time: datetime
    end_time: datetime
    interval_seconds: int = Field(gt=0)
    market_ids: list[str] | None = None
    max_steps: int = Field(default=10000, gt=0)
    persist_steps: bool = True
    force_recompute_verdicts: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_window(self) -> ReplayRunConfig:
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        return self


class ReplayRun(ReplayModel):
    run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: ReplayRunStatus
    policy_name: str
    policy_version: str
    start_time: datetime
    end_time: datetime
    interval_seconds: int
    market_ids: list[str] = Field(default_factory=list)
    max_steps: int
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayStep(ReplayModel):
    step_id: str
    run_id: str
    market_id: str
    asof_timestamp: datetime
    market_status: str | None = None
    rule_snapshot_id: str | None = None
    rule_snapshot_hash: str | None = None
    orderbook_snapshot_id: str | None = None
    resolution_predicate_id: str | None = None
    ambiguity_assessment_id: str | None = None
    trust_verdict_id: str | None = None
    action: str
    allowed_size_multiplier: Decimal
    price_integrity_score: int | None = None
    resolution_risk_score: int | None = None
    liquidity_risk_score: int | None = None
    cross_venue_consistency_score: int | None = None
    information_freshness_score: int | None = None
    manipulation_risk_score: int | None = None
    reason_codes: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayRunSummary(ReplayModel):
    summary_id: str
    run_id: str
    created_at: datetime
    total_steps: int
    errored_steps: int
    action_counts: dict[str, int] = Field(default_factory=dict)
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    no_trade_rate: Decimal
    manual_review_rate: Decimal
    passive_only_rate: Decimal
    allow_rate: Decimal
    allowed_exposure_units: Decimal
    blocked_exposure_units: Decimal
    markets_replayed: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayDecision(ReplayModel):
    action: str
    allowed_size_multiplier: Decimal
    reason_codes: list[str] = Field(default_factory=list)
    trust_verdict_id: str | None = None
    scores: dict[str, int | None] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReplayRunResult(ReplayModel):
    run: ReplayRun
    steps: list[ReplayStep] = Field(default_factory=list)
    summary: ReplayRunSummary


class ReplayRunResponse(ReplayModel):
    run: ReplayRun
    summary: ReplayRunSummary
