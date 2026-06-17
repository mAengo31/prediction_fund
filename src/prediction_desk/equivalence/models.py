"""Pydantic models for cross-venue contract equivalence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from prediction_desk.equivalence.enums import (
    ComparisonPermission,
    EquivalenceClassStatus,
    EquivalenceRunStatus,
    EquivalenceStatus,
    OutcomeRelation,
)

EQUIVALENCE_ASSESSMENT_VERSION = "market_equivalence_assessment_v1"
EQUIVALENCE_CANDIDATE_VERSION = "equivalence_candidate_v1"
EQUIVALENCE_CLASS_VERSION = "equivalence_class_v1"
EQUIVALENCE_RUNNER_VERSION = "equivalence_runner_v1"


class EquivalenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DimensionScore(EquivalenceModel):
    score: int = Field(ge=0, le=100)
    reason_codes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    hard_flags: dict[str, bool] = Field(default_factory=dict)


class MarketEquivalenceAssessment(EquivalenceModel):
    equivalence_assessment_id: str
    left_market_id: str
    right_market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    left_rule_snapshot_id: str | None = None
    right_rule_snapshot_id: str | None = None
    left_rule_snapshot_hash: str | None = None
    right_rule_snapshot_hash: str | None = None
    left_resolution_predicate_id: str | None = None
    right_resolution_predicate_id: str | None = None
    left_ambiguity_assessment_id: str | None = None
    right_ambiguity_assessment_id: str | None = None
    left_venue_id: str | None = None
    right_venue_id: str | None = None
    status: EquivalenceStatus
    comparison_permission: ComparisonPermission
    overall_score: int = Field(ge=0, le=100)
    confidence_score: int = Field(ge=0, le=100)
    title_similarity_score: int = Field(ge=0, le=100)
    event_identity_score: int = Field(ge=0, le=100)
    outcome_structure_score: int = Field(ge=0, le=100)
    outcome_mapping_score: int = Field(ge=0, le=100)
    predicate_similarity_score: int = Field(ge=0, le=100)
    resolution_source_score: int = Field(ge=0, le=100)
    settlement_authority_score: int = Field(ge=0, le=100)
    temporal_alignment_score: int = Field(ge=0, le=100)
    threshold_alignment_score: int = Field(ge=0, le=100)
    timezone_alignment_score: int = Field(ge=0, le=100)
    ambiguity_compatibility_score: int = Field(ge=0, le=100)
    venue_rule_compatibility_score: int = Field(ge=0, le=100)
    same_venue: bool
    same_event_likely: bool
    same_outcome_universe_likely: bool
    inverse_outcome_likely: bool
    resolution_source_mismatch: bool
    settlement_authority_mismatch: bool
    deadline_mismatch: bool
    timezone_mismatch: bool
    threshold_mismatch: bool
    high_ambiguity: bool
    insufficient_rule_data: bool
    reason_codes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutcomeEquivalenceMapping(EquivalenceModel):
    outcome_mapping_id: str
    equivalence_assessment_id: str
    left_market_id: str
    right_market_id: str
    left_outcome_id: str | None = None
    right_outcome_id: str | None = None
    left_label: str | None = None
    right_label: str | None = None
    relation: OutcomeRelation
    score: int = Field(ge=0, le=100)
    evidence: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EquivalenceCandidate(EquivalenceModel):
    candidate_id: str
    left_market_id: str
    right_market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    candidate_score: int = Field(ge=0, le=100)
    candidate_reasons: list[str] = Field(default_factory=list)
    left_venue_id: str | None = None
    right_venue_id: str | None = None
    title_similarity_score: int = Field(ge=0, le=100)
    category_match: bool
    shared_tokens: list[str] = Field(default_factory=list)
    input_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EquivalenceClass(EquivalenceModel):
    equivalence_class_id: str
    asof_timestamp: datetime
    created_at: datetime
    status: EquivalenceClassStatus
    representative_title: str | None = None
    market_ids: list[str] = Field(default_factory=list)
    assessment_ids: list[str] = Field(default_factory=list)
    min_pair_score: int = Field(ge=0, le=100)
    average_pair_score: Decimal
    confidence_score: int = Field(ge=0, le=100)
    comparison_permission: ComparisonPermission
    reason_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EquivalenceRun(EquivalenceModel):
    equivalence_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: EquivalenceRunStatus
    asof_timestamp: datetime
    market_ids: list[str] = Field(default_factory=list)
    venue_names: list[str] = Field(default_factory=list)
    max_pairs: int
    min_candidate_score: int
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    candidates_created: int = 0
    assessments_created: int = 0
    classes_created: int = 0
    errors_count: int = 0


class EquivalenceRunSummary(EquivalenceModel):
    summary_id: str
    equivalence_run_id: str
    created_at: datetime
    total_candidates: int
    total_assessments: int
    total_classes: int
    status_counts: dict[str, int] = Field(default_factory=dict)
    permission_counts: dict[str, int] = Field(default_factory=dict)
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    comparable_rate: Decimal
    manual_review_rate: Decimal
    do_not_compare_rate: Decimal
    markets_compared: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class EquivalenceAssessmentResponse(EquivalenceModel):
    assessment: MarketEquivalenceAssessment
    outcome_mappings: list[OutcomeEquivalenceMapping] = Field(default_factory=list)


class EquivalenceAssessRequest(EquivalenceModel):
    left_market_id: str
    right_market_id: str
    asof_timestamp: datetime | None = None
    force: bool = False
    config: dict[str, Any] = Field(default_factory=dict)


class EquivalenceCandidatesRequest(EquivalenceModel):
    market_ids: list[str] | None = None
    venue_names: list[str] | None = None
    asof_timestamp: datetime | None = None
    min_candidate_score: int = Field(default=40, ge=0, le=100)
    max_pairs: int = Field(default=10000, gt=0)
    force: bool = False


class EquivalenceRunConfig(EquivalenceModel):
    name: str | None = None
    asof_timestamp: datetime
    market_ids: list[str] | None = None
    venue_names: list[str] | None = None
    min_candidate_score: int = Field(default=40, ge=0, le=100)
    max_pairs: int = Field(default=10000, gt=0)
    build_classes: bool = True
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_scan(self) -> EquivalenceRunConfig:
        if self.max_pairs <= 0:
            raise ValueError("max_pairs must be positive.")
        return self


class EquivalenceRunRequest(EquivalenceModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    market_ids: list[str] | None = None
    venue_names: list[str] | None = None
    min_candidate_score: int = Field(default=40, ge=0, le=100)
    max_pairs: int = Field(default=10000, gt=0)
    build_classes: bool = True
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EquivalenceRunResult(EquivalenceModel):
    run: EquivalenceRun
    candidates: list[EquivalenceCandidate] = Field(default_factory=list)
    assessments: list[MarketEquivalenceAssessment] = Field(default_factory=list)
    classes: list[EquivalenceClass] = Field(default_factory=list)
    summary: EquivalenceRunSummary


def compute_candidate_input_hash(candidate: EquivalenceCandidate) -> str:
    return hash_payload(
        {
            "asof_timestamp": candidate.asof_timestamp,
            "candidate_version": EQUIVALENCE_CANDIDATE_VERSION,
            "category_match": candidate.category_match,
            "left_market_id": candidate.left_market_id,
            "right_market_id": candidate.right_market_id,
            "shared_tokens": sorted(candidate.shared_tokens),
            "title_similarity_score": candidate.title_similarity_score,
        }
    )


def compute_assessment_input_hash(
    assessment: MarketEquivalenceAssessment,
    outcome_mappings: list[OutcomeEquivalenceMapping],
) -> str:
    return hash_payload(
        {
            "assessment_version": EQUIVALENCE_ASSESSMENT_VERSION,
            "asof_timestamp": assessment.asof_timestamp,
            "left_ambiguity_assessment_id": assessment.left_ambiguity_assessment_id,
            "left_market_id": assessment.left_market_id,
            "left_resolution_predicate_id": assessment.left_resolution_predicate_id,
            "left_rule_snapshot_hash": assessment.left_rule_snapshot_hash,
            "left_rule_snapshot_id": assessment.left_rule_snapshot_id,
            "outcome_mappings": [
                {
                    "left_outcome_id": mapping.left_outcome_id,
                    "relation": mapping.relation.value,
                    "right_outcome_id": mapping.right_outcome_id,
                    "score": mapping.score,
                }
                for mapping in sorted(
                    outcome_mappings,
                    key=lambda item: (
                        item.left_outcome_id or "",
                        item.right_outcome_id or "",
                        item.relation.value,
                    ),
                )
            ],
            "right_ambiguity_assessment_id": assessment.right_ambiguity_assessment_id,
            "right_market_id": assessment.right_market_id,
            "right_resolution_predicate_id": assessment.right_resolution_predicate_id,
            "right_rule_snapshot_hash": assessment.right_rule_snapshot_hash,
            "right_rule_snapshot_id": assessment.right_rule_snapshot_id,
            "scores": _assessment_scores(assessment),
        }
    )


def compute_assessment_output_hash(assessment: MarketEquivalenceAssessment) -> str:
    return hash_payload(
        {
            "assessment_version": EQUIVALENCE_ASSESSMENT_VERSION,
            "comparison_permission": assessment.comparison_permission.value,
            "confidence_score": assessment.confidence_score,
            "hard_flags": _assessment_hard_flags(assessment),
            "overall_score": assessment.overall_score,
            "reason_codes": sorted(assessment.reason_codes),
            "status": assessment.status.value,
        }
    )


def compute_class_id_payload(equivalence_class: EquivalenceClass) -> dict[str, Any]:
    return {
        "assessment_ids": sorted(equivalence_class.assessment_ids),
        "asof_timestamp": equivalence_class.asof_timestamp,
        "class_version": EQUIVALENCE_CLASS_VERSION,
        "market_ids": sorted(equivalence_class.market_ids),
    }


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


def _assessment_scores(assessment: MarketEquivalenceAssessment) -> dict[str, int]:
    return {
        "ambiguity_compatibility_score": assessment.ambiguity_compatibility_score,
        "event_identity_score": assessment.event_identity_score,
        "outcome_mapping_score": assessment.outcome_mapping_score,
        "outcome_structure_score": assessment.outcome_structure_score,
        "predicate_similarity_score": assessment.predicate_similarity_score,
        "resolution_source_score": assessment.resolution_source_score,
        "settlement_authority_score": assessment.settlement_authority_score,
        "temporal_alignment_score": assessment.temporal_alignment_score,
        "threshold_alignment_score": assessment.threshold_alignment_score,
        "timezone_alignment_score": assessment.timezone_alignment_score,
        "title_similarity_score": assessment.title_similarity_score,
        "venue_rule_compatibility_score": assessment.venue_rule_compatibility_score,
    }


def _assessment_hard_flags(assessment: MarketEquivalenceAssessment) -> dict[str, bool]:
    return {
        "deadline_mismatch": assessment.deadline_mismatch,
        "high_ambiguity": assessment.high_ambiguity,
        "insufficient_rule_data": assessment.insufficient_rule_data,
        "resolution_source_mismatch": assessment.resolution_source_mismatch,
        "settlement_authority_mismatch": assessment.settlement_authority_mismatch,
        "threshold_mismatch": assessment.threshold_mismatch,
        "timezone_mismatch": assessment.timezone_mismatch,
    }
