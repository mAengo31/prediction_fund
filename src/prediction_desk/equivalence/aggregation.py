"""Aggregate equivalence dimension scores into a contract comparison assessment."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.equivalence.dimensions import inverse_outcome_likely, outcome_mapping_score
from prediction_desk.equivalence.enums import ComparisonPermission, EquivalenceStatus
from prediction_desk.equivalence.models import (
    DimensionScore,
    MarketEquivalenceAssessment,
    OutcomeEquivalenceMapping,
    compute_assessment_input_hash,
    compute_assessment_output_hash,
)
from prediction_desk.resolution.models import AmbiguityAssessment, ResolutionPredicate

_WEIGHTS: dict[str, Decimal] = {
    "title_similarity": Decimal("8"),
    "event_identity": Decimal("8"),
    "outcome_structure": Decimal("10"),
    "outcome_mapping": Decimal("10"),
    "predicate_similarity": Decimal("12"),
    "resolution_source": Decimal("10"),
    "settlement_authority": Decimal("7"),
    "temporal_alignment": Decimal("10"),
    "threshold_alignment": Decimal("10"),
    "timezone_alignment": Decimal("5"),
    "ambiguity_compatibility": Decimal("5"),
    "venue_rule_compatibility": Decimal("5"),
}


def aggregate_equivalence_dimensions(
    *,
    left_market: Market,
    right_market: Market,
    asof_timestamp: datetime,
    dimensions: dict[str, DimensionScore],
    outcome_mappings: list[OutcomeEquivalenceMapping],
    left_rule_snapshot: MarketRuleSnapshot | None,
    right_rule_snapshot: MarketRuleSnapshot | None,
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
    left_ambiguity: AmbiguityAssessment | None,
    right_ambiguity: AmbiguityAssessment | None,
    metadata: dict[str, Any] | None = None,
) -> MarketEquivalenceAssessment:
    scores = _scores(dimensions, outcome_mappings)
    flags = _hard_flags(dimensions)
    reason_codes = sorted(
        {
            reason
            for score in dimensions.values()
            for reason in score.reason_codes
        }
    )
    evidence = {
        name: {
            "score": score.score,
            "evidence": score.evidence,
            "hard_flags": score.hard_flags,
        }
        for name, score in sorted(dimensions.items())
    }
    overall_score = _weighted_score(scores)
    status = _status(overall_score, flags)
    permission = _permission(status)
    if status == EquivalenceStatus.NOT_EQUIVALENT:
        overall_score = min(overall_score, 45)
    if flags["insufficient_rule_data"] and status not in {
        EquivalenceStatus.NOT_EQUIVALENT,
        EquivalenceStatus.NEEDS_REVIEW,
    }:
        status = EquivalenceStatus.NEEDS_REVIEW
        permission = ComparisonPermission.MANUAL_REVIEW
        overall_score = min(overall_score, 69)
    confidence_score = _confidence_score(scores, flags)

    assessment = MarketEquivalenceAssessment(
        equivalence_assessment_id="pending",
        left_market_id=left_market.market_id,
        right_market_id=right_market.market_id,
        asof_timestamp=asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=asof_timestamp,
        left_rule_snapshot_id=(
            left_rule_snapshot.rule_snapshot_id if left_rule_snapshot else None
        ),
        right_rule_snapshot_id=(
            right_rule_snapshot.rule_snapshot_id if right_rule_snapshot else None
        ),
        left_rule_snapshot_hash=left_rule_snapshot.rule_hash if left_rule_snapshot else None,
        right_rule_snapshot_hash=right_rule_snapshot.rule_hash if right_rule_snapshot else None,
        left_resolution_predicate_id=(
            left_predicate.predicate_id if left_predicate else None
        ),
        right_resolution_predicate_id=(
            right_predicate.predicate_id if right_predicate else None
        ),
        left_ambiguity_assessment_id=left_ambiguity.assessment_id if left_ambiguity else None,
        right_ambiguity_assessment_id=right_ambiguity.assessment_id if right_ambiguity else None,
        left_venue_id=left_market.venue_id,
        right_venue_id=right_market.venue_id,
        status=status,
        comparison_permission=permission,
        overall_score=overall_score,
        confidence_score=confidence_score,
        title_similarity_score=scores["title_similarity"],
        event_identity_score=scores["event_identity"],
        outcome_structure_score=scores["outcome_structure"],
        outcome_mapping_score=scores["outcome_mapping"],
        predicate_similarity_score=scores["predicate_similarity"],
        resolution_source_score=scores["resolution_source"],
        settlement_authority_score=scores["settlement_authority"],
        temporal_alignment_score=scores["temporal_alignment"],
        threshold_alignment_score=scores["threshold_alignment"],
        timezone_alignment_score=scores["timezone_alignment"],
        ambiguity_compatibility_score=scores["ambiguity_compatibility"],
        venue_rule_compatibility_score=scores["venue_rule_compatibility"],
        same_venue=left_market.venue_id == right_market.venue_id,
        same_event_likely=scores["event_identity"] >= 70,
        same_outcome_universe_likely=scores["outcome_structure"] >= 70,
        inverse_outcome_likely=inverse_outcome_likely(outcome_mappings),
        resolution_source_mismatch=flags["resolution_source_mismatch"],
        settlement_authority_mismatch=flags["settlement_authority_mismatch"],
        deadline_mismatch=flags["deadline_mismatch"],
        timezone_mismatch=flags["timezone_mismatch"],
        threshold_mismatch=flags["threshold_mismatch"],
        high_ambiguity=flags["high_ambiguity"],
        insufficient_rule_data=flags["insufficient_rule_data"],
        reason_codes=reason_codes,
        evidence=evidence,
        input_hash="pending",
        output_hash="pending",
        metadata={
            "aggregation": "weighted_dimension_average_capped_by_hard_flags",
            "weights": {key: str(value) for key, value in _WEIGHTS.items()},
            **(metadata or {}),
        },
    )
    input_hash = compute_assessment_input_hash(assessment, outcome_mappings)
    output_hash = compute_assessment_output_hash(
        assessment.model_copy(update={"input_hash": input_hash})
    )
    return assessment.model_copy(
        update={
            "equivalence_assessment_id": f"equivalence_assessment_{output_hash[:24]}",
            "input_hash": input_hash,
            "output_hash": output_hash,
        }
    )


def _scores(
    dimensions: dict[str, DimensionScore],
    outcome_mappings: list[OutcomeEquivalenceMapping],
) -> dict[str, int]:
    values = {
        "title_similarity": dimensions["title_similarity"].score,
        "event_identity": dimensions["event_identity"].score,
        "outcome_structure": dimensions["outcome_structure"].score,
        "outcome_mapping": outcome_mapping_score(outcome_mappings),
        "predicate_similarity": dimensions["predicate_similarity"].score,
        "resolution_source": dimensions["resolution_source"].score,
        "settlement_authority": dimensions["settlement_authority"].score,
        "temporal_alignment": dimensions["temporal_alignment"].score,
        "threshold_alignment": dimensions["threshold_alignment"].score,
        "timezone_alignment": dimensions["timezone_alignment"].score,
        "ambiguity_compatibility": dimensions["ambiguity_compatibility"].score,
        "venue_rule_compatibility": dimensions["venue_rule_compatibility"].score,
    }
    return {key: max(0, min(100, int(value))) for key, value in values.items()}


def _hard_flags(dimensions: dict[str, DimensionScore]) -> dict[str, bool]:
    flags = {
        "deadline_mismatch": False,
        "high_ambiguity": False,
        "insufficient_rule_data": False,
        "resolution_source_mismatch": False,
        "settlement_authority_mismatch": False,
        "threshold_mismatch": False,
        "timezone_mismatch": False,
    }
    for score in dimensions.values():
        for key in flags:
            flags[key] = flags[key] or bool(score.hard_flags.get(key))
    return flags


def _weighted_score(scores: dict[str, int]) -> int:
    weighted_sum = sum(Decimal(scores[key]) * weight for key, weight in _WEIGHTS.items())
    denominator = sum(_WEIGHTS.values())
    return round(weighted_sum / denominator)


def _status(overall_score: int, flags: dict[str, bool]) -> EquivalenceStatus:
    hard_mismatch = (
        flags["deadline_mismatch"]
        or flags["resolution_source_mismatch"]
        or flags["settlement_authority_mismatch"]
        or flags["threshold_mismatch"]
    )
    if hard_mismatch:
        return EquivalenceStatus.NOT_EQUIVALENT
    if flags["high_ambiguity"] or flags["insufficient_rule_data"]:
        return EquivalenceStatus.NEEDS_REVIEW
    if overall_score >= 85:
        return EquivalenceStatus.EQUIVALENT
    if overall_score >= 70:
        return EquivalenceStatus.NEAR_EQUIVALENT
    if overall_score >= 50:
        return EquivalenceStatus.RELATED
    return EquivalenceStatus.NOT_EQUIVALENT


def _permission(status: EquivalenceStatus) -> ComparisonPermission:
    if status == EquivalenceStatus.EQUIVALENT:
        return ComparisonPermission.COMPARABLE
    if status == EquivalenceStatus.NEAR_EQUIVALENT:
        return ComparisonPermission.COMPARABLE_WITH_HAIRCUT
    if status in {EquivalenceStatus.RELATED, EquivalenceStatus.NEEDS_REVIEW}:
        return ComparisonPermission.MANUAL_REVIEW
    return ComparisonPermission.DO_NOT_COMPARE


def _confidence_score(scores: dict[str, int], flags: dict[str, bool]) -> int:
    evidence_scores = [
        scores["predicate_similarity"],
        scores["resolution_source"],
        scores["temporal_alignment"],
        scores["threshold_alignment"],
        scores["ambiguity_compatibility"],
    ]
    confidence = round(sum(evidence_scores) / len(evidence_scores))
    if flags["insufficient_rule_data"]:
        confidence = min(confidence, 55)
    if flags["high_ambiguity"]:
        confidence = min(confidence, 45)
    return max(0, min(100, confidence))
