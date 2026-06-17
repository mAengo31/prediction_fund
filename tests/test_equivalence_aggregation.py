from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.domain.enums import MarketStatus, MarketType
from prediction_desk.domain.models import Market
from prediction_desk.equivalence.aggregation import aggregate_equivalence_dimensions
from prediction_desk.equivalence.enums import (
    ComparisonPermission,
    EquivalenceStatus,
    OutcomeRelation,
)
from prediction_desk.equivalence.models import DimensionScore, OutcomeEquivalenceMapping


def test_aggregation_classifies_clean_pair_as_equivalent() -> None:
    assessment = aggregate_equivalence_dimensions(
        left_market=_market("left"),
        right_market=_market("right"),
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
        dimensions=_dimensions(95),
        outcome_mappings=[_mapping(OutcomeRelation.SAME, 100)],
        left_rule_snapshot=None,
        right_rule_snapshot=None,
        left_predicate=None,
        right_predicate=None,
        left_ambiguity=None,
        right_ambiguity=None,
    )

    assert assessment.status == EquivalenceStatus.EQUIVALENT
    assert assessment.comparison_permission == ComparisonPermission.COMPARABLE
    assert assessment.overall_score >= 85


def test_aggregation_hard_mismatch_blocks_comparison() -> None:
    dimensions = _dimensions(90)
    dimensions["temporal_alignment"] = DimensionScore(
        score=10,
        reason_codes=["DEADLINE_MISMATCH"],
        hard_flags={"deadline_mismatch": True},
    )

    assessment = aggregate_equivalence_dimensions(
        left_market=_market("left"),
        right_market=_market("right"),
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
        dimensions=dimensions,
        outcome_mappings=[_mapping(OutcomeRelation.SAME, 100)],
        left_rule_snapshot=None,
        right_rule_snapshot=None,
        left_predicate=None,
        right_predicate=None,
        left_ambiguity=None,
        right_ambiguity=None,
    )

    assert assessment.status == EquivalenceStatus.NOT_EQUIVALENT
    assert assessment.comparison_permission == ComparisonPermission.DO_NOT_COMPARE
    assert assessment.deadline_mismatch


def _market(market_id: str) -> Market:
    return Market(
        market_id=market_id,
        venue_id=f"venue_{market_id}",
        event_id=f"event_{market_id}",
        title="Will NYC record at least 1 inch of rain by September 30, 2026?",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
    )


def _dimensions(score: int) -> dict[str, DimensionScore]:
    return {
        "title_similarity": DimensionScore(score=score),
        "event_identity": DimensionScore(score=score),
        "outcome_structure": DimensionScore(score=score),
        "predicate_similarity": DimensionScore(score=score),
        "resolution_source": DimensionScore(score=score),
        "settlement_authority": DimensionScore(score=score),
        "temporal_alignment": DimensionScore(score=score),
        "threshold_alignment": DimensionScore(score=score),
        "timezone_alignment": DimensionScore(score=score),
        "ambiguity_compatibility": DimensionScore(score=score),
        "venue_rule_compatibility": DimensionScore(score=score),
    }


def _mapping(relation: OutcomeRelation, score: int) -> OutcomeEquivalenceMapping:
    del relation
    return OutcomeEquivalenceMapping(
        outcome_mapping_id="mapping",
        equivalence_assessment_id="pending",
        left_market_id="left",
        right_market_id="right",
        left_outcome_id="left_yes",
        right_outcome_id="right_yes",
        left_label="Yes",
        right_label="Yes",
        relation=OutcomeRelation.SAME,
        score=score,
        evidence={},
    )
