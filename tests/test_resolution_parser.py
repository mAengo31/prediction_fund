from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import MarketStatus, MarketType
from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.resolution.enums import (
    Comparator,
    ParseStatus,
    PredicateType,
    ResolutionSourceType,
)
from prediction_desk.resolution.models import ResolutionSource
from prediction_desk.resolution.parser import parse_resolution_predicate


def test_parser_handles_missing_rule_text() -> None:
    market = _market("mkt_empty_rule")
    snapshot = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_empty",
        market_id=market.market_id,
        captured_at=datetime(2026, 6, 16, tzinfo=UTC),
        raw_rule_text="",
    )

    predicate = parse_resolution_predicate(market, snapshot)

    assert predicate.parse_status is ParseStatus.FAILED
    assert predicate.predicate_type is PredicateType.UNKNOWN
    assert predicate.confidence_score == 0


def test_parser_classifies_clean_binary_rule() -> None:
    market = _market("mkt_binary_event", title="Will the bill pass?")
    snapshot = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_binary_event",
        market_id=market.market_id,
        captured_at=datetime(2026, 6, 16, tzinfo=UTC),
        raw_rule_text=(
            "This market resolves YES if the bill passes Congress. The official source is "
            "the Congressional record. Settlement is determined by Prediction Desk Research."
        ),
        resolution_source="Congressional record",
        settlement_authority="Prediction Desk Research",
        time_zone="ET",
    )

    predicate = parse_resolution_predicate(market, snapshot)

    assert predicate.parse_status is not ParseStatus.FAILED
    assert predicate.predicate_type is PredicateType.BINARY_EVENT
    assert predicate.subject == market.title


def test_parser_classifies_scalar_threshold_and_extracts_threshold() -> None:
    _, _, threshold, *_ = sample_markets()

    predicate = parse_resolution_predicate(threshold.market, threshold.rule_snapshot)

    assert predicate.predicate_type is PredicateType.SCALAR_THRESHOLD
    assert predicate.comparator is Comparator.GREATER_THAN_OR_EQUAL
    assert predicate.threshold_value == Decimal("3.0")
    assert predicate.threshold_unit == "percent"


def test_parser_extracts_explicit_deadline_and_timezone() -> None:
    _, _, threshold, *_ = sample_markets()

    predicate = parse_resolution_predicate(threshold.market, threshold.rule_snapshot)

    assert predicate.time_window_end == datetime(2026, 10, 16, 8, 30, tzinfo=UTC)
    assert predicate.time_zone == "ET"
    assert any(span.field_name == "time_window_end" for span in predicate.evidence_spans)


def test_parser_uses_rule_snapshot_resolution_source_when_present() -> None:
    clean, *_ = sample_markets()
    source = ResolutionSource(
        source_id="source_noaa",
        canonical_name="NOAA daily climate summary for station SFO",
        source_type=ResolutionSourceType.WEATHER,
    )

    predicate = parse_resolution_predicate(
        clean.market,
        clean.rule_snapshot,
        known_sources=[source],
    )

    assert predicate.resolution_source_id == source.source_id
    assert "source=NOAA daily climate summary for station SFO" in (
        predicate.normalized_predicate_text or ""
    )


def _market(market_id: str, title: str = "Will the event occur?") -> Market:
    return Market(
        market_id=market_id,
        venue_id="venue",
        event_id="event",
        title=title,
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
    )
