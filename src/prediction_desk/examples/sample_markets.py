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
from prediction_desk.resolution.enums import ResolutionSourceType
from prediction_desk.resolution.models import ResolutionSource

SAMPLE_ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class SampleMarketBundle:
    venue: Venue
    event: Event
    market: Market
    outcomes: tuple[Outcome, ...]
    rule_snapshot: MarketRuleSnapshot
    orderbook_snapshot: OrderBookSnapshot
    rule_snapshots: tuple[MarketRuleSnapshot, ...] = ()
    orderbook_snapshots: tuple[OrderBookSnapshot, ...] = ()


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
    vague_orderbook_early = OrderBookSnapshot(
        snapshot_id="ob_candidate_announcement_vague_2026_early",
        market_id=vague_market.market_id,
        captured_at=datetime(2026, 6, 16, 11, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.42"), quantity=Decimal("25"))],
        asks=[PriceLevel(price=Decimal("0.45"), quantity=Decimal("25"))],
        metadata={"fixture_kind": "ambiguous", "phase": "early_tight"},
    )
    vague_orderbook = OrderBookSnapshot(
        snapshot_id="ob_candidate_announcement_vague_2026_wide",
        market_id=vague_market.market_id,
        captured_at=asof_timestamp,
        bids=[PriceLevel(price=Decimal("0.40"), quantity=Decimal("20"))],
        asks=[PriceLevel(price=Decimal("0.65"), quantity=Decimal("10"))],
        metadata={"fixture_kind": "ambiguous"},
    )

    threshold_event = Event(
        event_id="event_cpi_threshold_2026_09",
        venue_id=venue.venue_id,
        title="September 2026 CPI threshold",
        category="economics",
        start_time=datetime(2026, 9, 1, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 10, 16, 12, 30, tzinfo=UTC),
        metadata={},
    )
    threshold_market = Market(
        market_id="mkt_cpi_yoy_at_least_3pct_2026_09",
        venue_id=venue.venue_id,
        event_id=threshold_event.event_id,
        title="Will September 2026 CPI year-over-year be at least 3.0%?",
        description="Clean scalar-threshold fixture with explicit source and deadline.",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
        created_time=asof_timestamp,
        close_time=datetime(2026, 10, 16, 12, 30, tzinfo=UTC),
        settlement_time=None,
        metadata={"fixture_kind": "clean_threshold"},
    )
    threshold_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_cpi_yoy_at_least_3pct_2026_09_v1",
        market_id=threshold_market.market_id,
        captured_at=asof_timestamp,
        raw_rule_text=(
            "This market resolves YES if the Bureau of Labor Statistics official CPI-U "
            "release reports year-over-year CPI at least 3.0 percent for September 2026. "
            "The final settlement source is the Bureau of Labor Statistics CPI-U release. "
            "The deadline for the referenced release is 8:30 AM ET on October 16, 2026. "
            "Settlement is determined by Prediction Desk Research."
        ),
        normalized_rule_text=(
            "YES if BLS official CPI-U YoY for September 2026 is >= 3.0 percent, "
            "deadline 2026-10-16 08:30 ET."
        ),
        resolution_source="Bureau of Labor Statistics CPI-U release",
        settlement_authority="Prediction Desk Research",
        time_zone="ET",
        metadata={"fixture_kind": "clean_threshold"},
    )
    threshold_orderbook = OrderBookSnapshot(
        snapshot_id="ob_cpi_yoy_at_least_3pct_2026_09_tight",
        market_id=threshold_market.market_id,
        captured_at=asof_timestamp,
        bids=[PriceLevel(price=Decimal("0.48"), quantity=Decimal("80"))],
        asks=[PriceLevel(price=Decimal("0.51"), quantity=Decimal("90"))],
        metadata={"fixture_kind": "clean_threshold"},
    )
    threshold_orderbook_wide = OrderBookSnapshot(
        snapshot_id="ob_cpi_yoy_at_least_3pct_2026_09_wide",
        market_id=threshold_market.market_id,
        captured_at=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.40"), quantity=Decimal("80"))],
        asks=[PriceLevel(price=Decimal("0.62"), quantity=Decimal("90"))],
        metadata={"fixture_kind": "clean_threshold", "phase": "wide_spread"},
    )

    vague_deadline_event = Event(
        event_id="event_vague_deadline_policy_2026",
        venue_id=venue.venue_id,
        title="Vague policy deadline",
        category="policy",
        start_time=None,
        end_time=None,
        metadata={},
    )
    vague_deadline_market = Market(
        market_id="mkt_vague_deadline_before_end_september_2026",
        venue_id=venue.venue_id,
        event_id=vague_deadline_event.event_id,
        title="Will the agency publish guidance before the end of September?",
        description="Fixture with vague end-of-month deadline and no time zone.",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
        created_time=asof_timestamp,
        close_time=None,
        settlement_time=None,
        metadata={"fixture_kind": "vague_deadline"},
    )
    vague_deadline_rule = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_vague_deadline_before_end_september_2026_v1",
        market_id=vague_deadline_market.market_id,
        captured_at=asof_timestamp,
        raw_rule_text=(
            "This market resolves YES if official sources indicate the agency publishes "
            "guidance before the end of September. Reports from credible sources may be "
            "used if unclear."
        ),
        normalized_rule_text=None,
        resolution_source=None,
        settlement_authority=None,
        time_zone=None,
        metadata={"fixture_kind": "vague_deadline"},
    )
    vague_deadline_orderbook_early = OrderBookSnapshot(
        snapshot_id="ob_vague_deadline_before_end_september_2026_tight",
        market_id=vague_deadline_market.market_id,
        captured_at=datetime(2026, 6, 16, 11, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.36"), quantity=Decimal("25"))],
        asks=[PriceLevel(price=Decimal("0.39"), quantity=Decimal("25"))],
        metadata={"fixture_kind": "vague_deadline", "phase": "early_tight"},
    )
    vague_deadline_orderbook = OrderBookSnapshot(
        snapshot_id="ob_vague_deadline_before_end_september_2026_empty_side",
        market_id=vague_deadline_market.market_id,
        captured_at=asof_timestamp,
        bids=[PriceLevel(price=Decimal("0.35"), quantity=Decimal("25"))],
        asks=[],
        metadata={"fixture_kind": "vague_deadline", "phase": "empty_side"},
    )

    rule_change_event = Event(
        event_id="event_rate_cut_rule_change_2026",
        venue_id=venue.venue_id,
        title="Central bank rate cut rule change",
        category="economics",
        start_time=datetime(2026, 6, 1, 0, 0, tzinfo=UTC),
        end_time=datetime(2026, 9, 30, 23, 59, tzinfo=UTC),
        metadata={},
    )
    rule_change_market = Market(
        market_id="mkt_rate_cut_rule_change_2026",
        venue_id=venue.venue_id,
        event_id=rule_change_event.event_id,
        title="Will the central bank cut rates by September 2026?",
        description="Fixture with two rule snapshots for deterministic diffing.",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
        created_time=asof_timestamp,
        close_time=datetime(2026, 9, 30, 23, 59, tzinfo=UTC),
        settlement_time=None,
        metadata={"fixture_kind": "rule_change"},
    )
    rule_change_v1 = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_rate_cut_rule_change_2026_v1",
        market_id=rule_change_market.market_id,
        captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        raw_rule_text=(
            "This market resolves YES if the central bank announces a policy rate cut "
            "by September 15, 2026. The resolution source is the central bank press "
            "release. Settlement is determined by Prediction Desk Research."
        ),
        normalized_rule_text=(
            "YES if central bank announces a policy rate cut by 2026-09-15 from press release."
        ),
        resolution_source="Central bank press release",
        settlement_authority="Prediction Desk Research",
        time_zone="ET",
        metadata={"fixture_kind": "rule_change", "version": 1},
    )
    rule_change_v2 = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_rate_cut_rule_change_2026_v2",
        market_id=rule_change_market.market_id,
        captured_at=datetime(2026, 6, 17, 12, 0, tzinfo=UTC),
        raw_rule_text=(
            "This market resolves YES if the central bank announces a policy rate cut "
            "on or before September 30, 2026. The final settlement source is the central "
            "bank policy statement. Any dispute is resolved by Prediction Desk Research "
            "as the final settlement authority."
        ),
        normalized_rule_text=(
            "YES if central bank announces a policy rate cut on or before 2026-09-30 "
            "from policy statement."
        ),
        resolution_source="Central bank policy statement",
        settlement_authority="Prediction Desk Research",
        time_zone="ET",
        metadata={"fixture_kind": "rule_change", "version": 2},
    )
    rule_change_orderbook_v1 = OrderBookSnapshot(
        snapshot_id="ob_rate_cut_rule_change_2026_v1",
        market_id=rule_change_market.market_id,
        captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.44"), quantity=Decimal("75"))],
        asks=[PriceLevel(price=Decimal("0.47"), quantity=Decimal("70"))],
        metadata={"fixture_kind": "rule_change", "version": 1},
    )
    rule_change_orderbook = OrderBookSnapshot(
        snapshot_id="ob_rate_cut_rule_change_2026_v2",
        market_id=rule_change_market.market_id,
        captured_at=datetime(2026, 6, 17, 12, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.50"), quantity=Decimal("75"))],
        asks=[PriceLevel(price=Decimal("0.56"), quantity=Decimal("70"))],
        metadata={"fixture_kind": "rule_change", "version": 2},
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
            orderbook_snapshots=(vague_orderbook_early, vague_orderbook),
        ),
        SampleMarketBundle(
            venue=venue,
            event=threshold_event,
            market=threshold_market,
            outcomes=_binary_outcomes(threshold_market.market_id),
            rule_snapshot=threshold_rule,
            orderbook_snapshot=threshold_orderbook,
            orderbook_snapshots=(threshold_orderbook, threshold_orderbook_wide),
        ),
        SampleMarketBundle(
            venue=venue,
            event=vague_deadline_event,
            market=vague_deadline_market,
            outcomes=_binary_outcomes(vague_deadline_market.market_id),
            rule_snapshot=vague_deadline_rule,
            orderbook_snapshot=vague_deadline_orderbook,
            orderbook_snapshots=(vague_deadline_orderbook_early, vague_deadline_orderbook),
        ),
        SampleMarketBundle(
            venue=venue,
            event=rule_change_event,
            market=rule_change_market,
            outcomes=_binary_outcomes(rule_change_market.market_id),
            rule_snapshot=rule_change_v2,
            orderbook_snapshot=rule_change_orderbook,
            rule_snapshots=(rule_change_v1, rule_change_v2),
            orderbook_snapshots=(rule_change_orderbook_v1, rule_change_orderbook),
        ),
    )


def load_sample_data(repo: PredictionMarketRepository) -> tuple[SampleMarketBundle, ...]:
    bundles = sample_markets()
    for source in _sample_sources():
        repo.save_resolution_source(source)
    for bundle in bundles:
        repo.save_venue(bundle.venue)
        repo.save_event(bundle.event)
        repo.create_market(bundle.market)
        for outcome in bundle.outcomes:
            repo.save_outcome(outcome)
        snapshots = bundle.rule_snapshots or (bundle.rule_snapshot,)
        for snapshot in snapshots:
            repo.save_rule_snapshot(snapshot)
        orderbooks = bundle.orderbook_snapshots or (bundle.orderbook_snapshot,)
        for orderbook in orderbooks:
            repo.save_orderbook_snapshot(orderbook)
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


def _sample_sources() -> tuple[ResolutionSource, ...]:
    return (
        ResolutionSource(
            source_id="source_noaa_daily_climate_summary_sfo",
            canonical_name="NOAA daily climate summary for station SFO",
            source_type=ResolutionSourceType.WEATHER,
            url=None,
            jurisdiction="US",
            reliability_rank=1,
            metadata={"fixture": True},
        ),
        ResolutionSource(
            source_id="source_bls_cpi_u_release",
            canonical_name="Bureau of Labor Statistics CPI-U release",
            source_type=ResolutionSourceType.GOVERNMENT,
            url=None,
            jurisdiction="US",
            reliability_rank=1,
            metadata={"fixture": True},
        ),
        ResolutionSource(
            source_id="source_central_bank_policy_statement",
            canonical_name="Central bank policy statement",
            source_type=ResolutionSourceType.REGULATOR,
            url=None,
            jurisdiction=None,
            reliability_rank=1,
            metadata={"fixture": True},
        ),
        ResolutionSource(
            source_id="source_central_bank_press_release",
            canonical_name="Central bank press release",
            source_type=ResolutionSourceType.REGULATOR,
            url=None,
            jurisdiction=None,
            reliability_rank=2,
            metadata={"fixture": True},
        ),
    )
