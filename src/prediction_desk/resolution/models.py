"""Pydantic models for the resolution corpus."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.resolution.enums import (
    Comparator,
    ParseStatus,
    PredicateType,
    ResolutionSourceType,
)


class ResolutionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSpan(ResolutionModel):
    field_name: str
    text: str
    start_char: int | None = None
    end_char: int | None = None
    confidence_score: int = Field(ge=0, le=100)


class ResolutionSource(ResolutionModel):
    source_id: str
    canonical_name: str
    source_type: ResolutionSourceType
    url: str | None = None
    jurisdiction: str | None = None
    reliability_rank: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolutionPredicate(ResolutionModel):
    predicate_id: str
    market_id: str
    rule_snapshot_id: str
    captured_at: datetime
    predicate_type: PredicateType
    parse_status: ParseStatus
    subject: str | None = None
    condition: str | None = None
    threshold_value: Decimal | None = None
    threshold_unit: str | None = None
    comparator: Comparator | None = None
    time_window_start: datetime | None = None
    time_window_end: datetime | None = None
    time_zone: str | None = None
    resolution_source_id: str | None = None
    settlement_authority: str | None = None
    confidence_score: int = Field(ge=0, le=100)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    normalized_predicate_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AmbiguityAssessment(ResolutionModel):
    assessment_id: str
    market_id: str
    rule_snapshot_id: str
    captured_at: datetime
    overall_score: int = Field(ge=0, le=100)
    source_ambiguity_score: int = Field(ge=0, le=100)
    temporal_ambiguity_score: int = Field(ge=0, le=100)
    definition_ambiguity_score: int = Field(ge=0, le=100)
    measurement_ambiguity_score: int = Field(ge=0, le=100)
    actor_ambiguity_score: int = Field(ge=0, le=100)
    threshold_ambiguity_score: int = Field(ge=0, le=100)
    dispute_ambiguity_score: int = Field(ge=0, le=100)
    exceptional_case_ambiguity_score: int = Field(ge=0, le=100)
    venue_adjudication_ambiguity_score: int = Field(ge=0, le=100)
    reason_codes: list[str] = Field(default_factory=list)
    evidence_spans: list[EvidenceSpan] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuleSnapshotDiff(ResolutionModel):
    diff_id: str
    market_id: str
    from_rule_snapshot_id: str
    to_rule_snapshot_id: str
    created_at: datetime
    raw_text_changed: bool
    normalized_text_changed: bool
    resolution_source_changed: bool
    settlement_authority_changed: bool
    time_zone_changed: bool
    old_rule_hash: str
    new_rule_hash: str
    changed_terms: list[str] = Field(default_factory=list)
    added_text_fragments: list[str] = Field(default_factory=list)
    removed_text_fragments: list[str] = Field(default_factory=list)
    semantic_change_flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolutionAnalysis(ResolutionModel):
    market: Market
    rule_snapshot: MarketRuleSnapshot
    predicate: ResolutionPredicate
    ambiguity_assessment: AmbiguityAssessment
