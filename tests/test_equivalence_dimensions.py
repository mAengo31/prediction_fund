from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import MarketStatus, MarketType
from prediction_desk.domain.models import Event, Market, MarketRuleSnapshot, Outcome
from prediction_desk.equivalence.dimensions import (
    map_outcomes,
    score_ambiguity_compatibility,
    score_event_identity,
    score_outcome_structure,
    score_resolution_source_alignment,
    score_settlement_authority_alignment,
    score_temporal_alignment,
    score_threshold_alignment,
    score_timezone_alignment,
    score_title_similarity,
)
from prediction_desk.equivalence.enums import OutcomeRelation
from prediction_desk.resolution.ambiguity import assess_rule_ambiguity
from prediction_desk.resolution.parser import parse_resolution_predicate


def test_binary_outcome_mapping_detects_same_and_inverse() -> None:
    left = _market("left", "Will NYC record rain?")
    right = _market("right", "Will NYC record rain?")
    inverse = _market("inverse", "Will NYC not record rain?")
    left_outcomes = _outcomes("left")
    right_outcomes = _outcomes("right")

    same = map_outcomes(left_outcomes, right_outcomes, left, right)
    inverted = map_outcomes(left_outcomes, right_outcomes, left, inverse)

    assert {mapping.relation for mapping in same} == {OutcomeRelation.SAME}
    assert {mapping.relation for mapping in inverted} == {OutcomeRelation.INVERSE}


def test_title_event_and_outcome_structure_score_similar_pairs_higher() -> None:
    left = _market("left", "Will NYC record at least 1 inch of rain by September 30, 2026?")
    right = _market("right", "Will NYC record at least one inch of rain by September 30 2026?")
    unrelated = _market("unrelated", "Will LA reach 90 degrees on July 4, 2026?")

    assert score_title_similarity(left, right).score > score_title_similarity(left, unrelated).score
    assert score_event_identity(
        Event(
            event_id="e1",
            venue_id="v1",
            title="NYC rainfall September 2026",
            category="weather",
        ),
        Event(
            event_id="e2",
            venue_id="v2",
            title="NYC rainfall September 2026",
            category="weather",
        ),
        left,
        right,
    ).score > 70
    assert score_outcome_structure(left, right, _outcomes("left"), _outcomes("right")).score >= 90


def test_resolution_source_and_authority_mismatch_flags() -> None:
    left_rule = _rule("left_rule", "left", source="NWS", authority="CFTC")
    right_rule = _rule("right_rule", "right", source="Company filing", authority="Company")

    source = score_resolution_source_alignment(left_rule, right_rule, None, None)
    authority = score_settlement_authority_alignment(left_rule, right_rule, None, None)

    assert source.hard_flags["resolution_source_mismatch"]
    assert authority.hard_flags["settlement_authority_mismatch"]


def test_temporal_timezone_and_threshold_mismatch_flags() -> None:
    left_market = _market("left", "Will NYC record at least 1 inch by September 30, 2026?")
    right_market = _market("right", "Will NYC record at least 2 inches by October 31, 2026?")
    left_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="left_rule",
        market_id=left_market.market_id,
        captured_at=datetime(2026, 6, 1, tzinfo=UTC),
        raw_rule_text=(
            "Resolves Yes if rainfall is at least 1 inch by 11:59 PM ET "
            "on September 30, 2026."
        ),
        resolution_source="NWS",
        settlement_authority="Kalshi",
        time_zone="ET",
    )
    right_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="right_rule",
        market_id=right_market.market_id,
        captured_at=datetime(2026, 6, 1, tzinfo=UTC),
        raw_rule_text=(
            "Resolves Yes if rainfall is at least 2 inches by 11:59 PM PT "
            "on October 31, 2026."
        ),
        resolution_source="NWS",
        settlement_authority="Kalshi",
        time_zone="PT",
    )
    left_predicate = parse_resolution_predicate(left_market, left_rule)
    right_predicate = parse_resolution_predicate(right_market, right_rule)

    assert score_temporal_alignment(
        left_predicate,
        right_predicate,
        left_rule,
        right_rule,
    ).hard_flags["deadline_mismatch"]
    assert score_timezone_alignment(
        left_predicate,
        right_predicate,
        left_rule,
        right_rule,
    ).hard_flags["timezone_mismatch"]
    assert score_threshold_alignment(left_predicate, right_predicate).hard_flags[
        "threshold_mismatch"
    ]


def test_high_ambiguity_lowers_ambiguity_compatibility() -> None:
    clean_market = _market("clean", "Will NYC record at least 1 inch by September 30, 2026?")
    vague_market = _market("vague", "Will reports say something happened soon?")
    clean_rule = _rule("clean_rule", clean_market.market_id)
    vague_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="vague_rule",
        market_id=vague_market.market_id,
        captured_at=datetime(2026, 6, 1, tzinfo=UTC),
        raw_rule_text="Various reports may say this happened soon around September.",
    )
    clean = assess_rule_ambiguity(clean_market, clean_rule)
    vague = assess_rule_ambiguity(vague_market, vague_rule).model_copy(
        update={"overall_score": 90}
    )

    score = score_ambiguity_compatibility(clean, vague)

    assert score.score < 70
    assert score.hard_flags["high_ambiguity"]


def _market(market_id: str, title: str) -> Market:
    return Market(
        market_id=market_id,
        venue_id=f"venue_{market_id}",
        event_id=f"event_{market_id}",
        title=title,
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
    )


def _outcomes(market_id: str) -> list[Outcome]:
    return [
        Outcome(
            outcome_id=f"{market_id}_yes",
            market_id=market_id,
            label="Yes",
            payout=Decimal("1"),
        ),
        Outcome(
            outcome_id=f"{market_id}_no",
            market_id=market_id,
            label="No",
            payout=Decimal("0"),
        ),
    ]


def _rule(
    rule_snapshot_id: str,
    market_id: str,
    *,
    source: str = "NWS",
    authority: str = "Kalshi",
) -> MarketRuleSnapshot:
    return MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id=rule_snapshot_id,
        market_id=market_id,
        captured_at=datetime(2026, 6, 1, tzinfo=UTC),
        raw_rule_text=(
            "Resolves Yes if rainfall is at least 1 inch by 11:59 PM ET "
            "on September 30, 2026."
        ),
        resolution_source=source,
        settlement_authority=authority,
        time_zone="ET",
    )
