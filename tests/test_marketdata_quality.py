from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from prediction_desk.domain.models import MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.ingestion.enums import VenueMappingStatus
from prediction_desk.ingestion.models import VenueMarketMapping
from prediction_desk.marketdata.enums import MarketDataQualitySeverity, MarketPriceSource
from prediction_desk.marketdata.models import MarketLiquiditySnapshot, MarketPriceSnapshot
from prediction_desk.marketdata.quality import build_quality_report

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_quality_report_flags_wide_spread() -> None:
    report = build_quality_report(
        market_id="mkt_test",
        asof_timestamp=ASOF,
        created_at=ASOF,
        price_snapshot=_price(price=Decimal("0.50")),
        liquidity_snapshot=_liquidity(spread=Decimal("0.20")),
        orderbook_snapshot=_orderbook(),
        rule_snapshot=_rule(),
        venue_mapping=_mapping(),
        freshness_threshold_seconds=3600,
        wide_spread_threshold=Decimal("0.10"),
    )

    assert report.wide_spread
    assert "WIDE_SPREAD" in report.reason_codes
    assert report.severity is MarketDataQualitySeverity.WARNING


def test_quality_report_flags_stale_and_missing_rule_snapshot() -> None:
    report = build_quality_report(
        market_id="mkt_test",
        asof_timestamp=ASOF + timedelta(hours=2),
        created_at=ASOF + timedelta(hours=2),
        price_snapshot=_price(price=Decimal("0.50")),
        liquidity_snapshot=_liquidity(spread=Decimal("0.02")),
        orderbook_snapshot=_orderbook(),
        rule_snapshot=None,
        venue_mapping=_mapping(),
        freshness_threshold_seconds=3600,
        wide_spread_threshold=Decimal("0.10"),
    )

    assert report.stale_market_data
    assert "STALE_MARKET_DATA" in report.reason_codes
    assert "NO_RULE_SNAPSHOT" in report.reason_codes


def test_quality_report_flags_out_of_bounds_price() -> None:
    report = build_quality_report(
        market_id="mkt_test",
        asof_timestamp=ASOF,
        created_at=ASOF,
        price_snapshot=_price(price=Decimal("1.20")),
        liquidity_snapshot=_liquidity(spread=Decimal("0.02")),
        orderbook_snapshot=_orderbook(),
        rule_snapshot=_rule(),
        venue_mapping=_mapping(),
        freshness_threshold_seconds=3600,
        wide_spread_threshold=Decimal("0.10"),
    )

    assert report.out_of_bounds_price
    assert "OUT_OF_BOUNDS_PRICE" in report.reason_codes
    assert report.severity is MarketDataQualitySeverity.ERROR


def _price(*, price: Decimal) -> MarketPriceSnapshot:
    return MarketPriceSnapshot(
        price_snapshot_id="price_test",
        market_id="mkt_test",
        outcome_id=None,
        venue_id="venue_test",
        venue_name="Venue Test",
        source=MarketPriceSource.MANUAL_FIXTURE,
        observed_at=ASOF,
        captured_at=ASOF,
        available_at=ASOF,
        price=price,
        bid=price,
        ask=price,
        mid=price,
        spread=Decimal("0"),
        last_trade_price=None,
        volume=None,
        open_interest=None,
        source_payload_id=None,
        orderbook_snapshot_id=None,
        external_market_id=None,
        external_outcome_id=None,
        data_hash="hash",
        metadata={},
    )


def _liquidity(*, spread: Decimal) -> MarketLiquiditySnapshot:
    return MarketLiquiditySnapshot(
        liquidity_snapshot_id="liquidity_test",
        market_id="mkt_test",
        venue_id="venue_test",
        venue_name="Venue Test",
        observed_at=ASOF,
        captured_at=ASOF,
        available_at=ASOF,
        best_bid=Decimal("0.50"),
        best_ask=Decimal("0.50") + spread,
        mid_price=Decimal("0.50") + spread / Decimal("2"),
        spread=spread,
        spread_bps=Decimal("100"),
        bid_depth=Decimal("10"),
        ask_depth=Decimal("10"),
        total_bid_depth=Decimal("10"),
        total_ask_depth=Decimal("10"),
        book_imbalance=Decimal("0"),
        is_empty_book=False,
        is_crossed_book=False,
        source_payload_id=None,
        orderbook_snapshot_id="ob_test",
        data_hash="hash",
        metadata={},
    )


def _orderbook() -> OrderBookSnapshot:
    return OrderBookSnapshot(
        snapshot_id="ob_test",
        market_id="mkt_test",
        captured_at=ASOF,
        bids=[],
        asks=[],
        metadata={},
    )


def _rule() -> MarketRuleSnapshot:
    return MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_test",
        market_id="mkt_test",
        captured_at=ASOF,
        raw_rule_text="Resolve from official source by June 16, 2026 at 12:00 UTC.",
        normalized_rule_text=None,
        resolution_source="Official source",
        settlement_authority="Prediction Desk",
        time_zone="UTC",
    )


def _mapping() -> VenueMarketMapping:
    return VenueMarketMapping(
        mapping_id="mapping_test",
        venue_id="venue_test",
        venue_name="Venue Test",
        external_event_id=None,
        external_market_id="external_test",
        external_symbol=None,
        canonical_event_id=None,
        canonical_market_id="mkt_test",
        external_url=None,
        first_seen_at=ASOF,
        last_seen_at=ASOF,
        status=VenueMappingStatus.ACTIVE,
        metadata={},
    )
