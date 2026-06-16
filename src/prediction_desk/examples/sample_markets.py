"""Deterministic sample markets for local development."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import MarketStatus, MarketType, VenueType
from prediction_desk.domain.models import (
    Event,
    Market,
    MarketRuleSnapshot,
    OrderBookSnapshot,
    Outcome,
    PriceLevel,
    Venue,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository

SAMPLE_ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class SampleMarketBundle:
    venue: Venue
    event: Event
    market: Market
    outcomes: tuple[Outcome, ...]
    rule_snapshot: MarketRuleSnapshot
    orderbook_snapshot: OrderBookSnapshot


def sample_markets(asof_timestamp: datetime = SAMPLE_ASOF) -> tuple[SampleMarketBundle, ...]:
    venue = Venue(
        venue_id="sample_research_venue",
        name="Sample Research Venue",
        jurisdiction="US",
        venue_type=VenueType.OTHER,
        metadata={"fixture": True},
    )

    clean_event = Event(
        event_id="event_sfo_rain_2026_09_01",
        venue_id=venue.venue_id,
        title="SFO rainfall on 2026-09-01",
        category="weather",
        start_time=datetime(2026, 9, 1, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 9, 2, 0, 0, tzinfo=UTC),
        metadata={},
    )
    clean_market = Market(
        market_id="mkt_sfo_rain_2026_09_01",
        venue_id=venue.venue_id,
        event_id=clean_event.event_id,
        title="Will SFO record at least 1.00 inch of rain on 2026-09-01?",
        description="Clean binary weather fixture with explicit resolution terms.",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
        created_time=asof_timestamp,
        close_time=datetime(2026, 9, 1, 23, 59, tzinfo=UTC),
        settlement_time=None,
        metadata={"fixture_kind": "clean"},
    )
    clean_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_sfo_rain_2026_09_01_v1",
        market_id=clean_market.market_id,
        captured_at=asof_timestamp,
        raw_rule_text=(
            "This market resolves YES if the NOAA daily climate summary for station SFO "
            "records total precipitation greater than or equal to 1.00 inch for the local "
            "calendar day 2026-09-01. The source is the NOAA daily climate summary for "
            "station SFO. Settlement uses America/Los_Angeles time."
        ),
        normalized_rule_text=(
            "YES if NOAA station SFO precipitation >= 1.00 inch on 2026-09-01, "
            "America/Los_Angeles calendar day."
        ),
        resolution_source="NOAA daily climate summary for station SFO",
        settlement_authority="Prediction Desk Research",
        time_zone="America/Los_Angeles",
        metadata={"fixture_kind": "clean"},
    )
    clean_orderbook = OrderBookSnapshot(
        snapshot_id="ob_sfo_rain_2026_09_01_v1",
        market_id=clean_market.market_id,
        captured_at=asof_timestamp,
        bids=[PriceLevel(price=Decimal("0.52"), quantity=Decimal("100"))],
        asks=[PriceLevel(price=Decimal("0.55"), quantity=Decimal("120"))],
        metadata={"fixture_kind": "clean"},
    )

    vague_event = Event(
        event_id="event_candidate_announcement_2026",
        venue_id=venue.venue_id,
        title="Candidate announcement timing",
        category="politics",
        start_time=None,
        end_time=None,
        metadata={},
    )
    vague_market = Market(
        market_id="mkt_candidate_announcement_vague_2026",
        venue_id=venue.venue_id,
        event_id=vague_event.event_id,
        title="Will the candidate announce soon?",
        description="Ambiguous binary fixture with vague rules.",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
        created_time=asof_timestamp,
        close_time=None,
        settlement_time=None,
        metadata={"fixture_kind": "ambiguous"},
    )
    vague_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_candidate_announcement_vague_2026_v1",
        market_id=vague_market.market_id,
        captured_at=asof_timestamp,
        raw_rule_text=(
            "This market resolves YES if the candidate is expected to announce soon, around "
            "the campaign launch window, by September, or before the end of the month. "
            "Resolution may rely on various sources, and/or credible reports."
        ),
        normalized_rule_text=None,
        resolution_source=None,
        settlement_authority=None,
        time_zone=None,
        metadata={"fixture_kind": "ambiguous"},
    )
    vague_orderbook = OrderBookSnapshot(
        snapshot_id="ob_candidate_announcement_vague_2026_v1",
        market_id=vague_market.market_id,
        captured_at=asof_timestamp,
        bids=[PriceLevel(price=Decimal("0.40"), quantity=Decimal("20"))],
        asks=[PriceLevel(price=Decimal("0.65"), quantity=Decimal("10"))],
        metadata={"fixture_kind": "ambiguous"},
    )

    return (
        SampleMarketBundle(
            venue=venue,
            event=clean_event,
            market=clean_market,
            outcomes=_binary_outcomes(clean_market.market_id),
            rule_snapshot=clean_rule,
            orderbook_snapshot=clean_orderbook,
        ),
        SampleMarketBundle(
            venue=venue,
            event=vague_event,
            market=vague_market,
            outcomes=_binary_outcomes(vague_market.market_id),
            rule_snapshot=vague_rule,
            orderbook_snapshot=vague_orderbook,
        ),
    )


def load_sample_data(repo: PredictionMarketRepository) -> tuple[SampleMarketBundle, ...]:
    bundles = sample_markets()
    for bundle in bundles:
        repo.save_venue(bundle.venue)
        repo.save_event(bundle.event)
        repo.create_market(bundle.market)
        for outcome in bundle.outcomes:
            repo.save_outcome(outcome)
        repo.save_rule_snapshot(bundle.rule_snapshot)
        repo.save_orderbook_snapshot(bundle.orderbook_snapshot)
    return bundles


def _binary_outcomes(market_id: str) -> tuple[Outcome, Outcome]:
    return (
        Outcome(
            outcome_id=f"{market_id}_yes",
            market_id=market_id,
            label="YES",
            payout=Decimal("1"),
            metadata={},
        ),
        Outcome(
            outcome_id=f"{market_id}_no",
            market_id=market_id,
            label="NO",
            payout=Decimal("1"),
            metadata={},
        ),
    )
