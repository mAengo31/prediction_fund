from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import MarketStatus, MarketType, VenueType
from prediction_desk.domain.models import Market, OrderBookSnapshot, PriceLevel, Venue
from prediction_desk.marketdata.orderbook import (
    derive_liquidity_snapshot_from_orderbook,
    derive_price_snapshot_from_orderbook,
)


def test_orderbook_derivation_computes_best_prices_depth_and_imbalance() -> None:
    market = _market()
    venue = _venue()
    orderbook = OrderBookSnapshot(
        snapshot_id="ob_test",
        market_id=market.market_id,
        captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        bids=[
            PriceLevel(price=Decimal("0.50"), quantity=Decimal("20")),
            PriceLevel(price=Decimal("0.52"), quantity=Decimal("100")),
        ],
        asks=[
            PriceLevel(price=Decimal("0.55"), quantity=Decimal("120")),
            PriceLevel(price=Decimal("0.57"), quantity=Decimal("10")),
        ],
        metadata={"source_payload_id": "payload_test"},
    )

    price = derive_price_snapshot_from_orderbook(market, orderbook, venue)
    liquidity = derive_liquidity_snapshot_from_orderbook(market, orderbook, venue)

    assert price.bid == Decimal("0.52")
    assert price.ask == Decimal("0.55")
    assert price.mid == Decimal("0.535")
    assert price.spread == Decimal("0.03")
    assert liquidity.best_bid == Decimal("0.52")
    assert liquidity.best_ask == Decimal("0.55")
    assert liquidity.bid_depth == Decimal("100")
    assert liquidity.ask_depth == Decimal("120")
    assert liquidity.total_bid_depth == Decimal("120")
    assert liquidity.total_ask_depth == Decimal("130")
    assert liquidity.book_imbalance == Decimal("-0.04")


def test_one_sided_book_produces_no_mid_or_spread() -> None:
    market = _market()
    venue = _venue()
    orderbook = OrderBookSnapshot(
        snapshot_id="ob_one_sided",
        market_id=market.market_id,
        captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.52"), quantity=Decimal("100"))],
        asks=[],
        metadata={},
    )

    liquidity = derive_liquidity_snapshot_from_orderbook(market, orderbook, venue)

    assert liquidity.best_bid == Decimal("0.52")
    assert liquidity.best_ask is None
    assert liquidity.mid_price is None
    assert liquidity.spread is None


def test_empty_and_crossed_books_are_flagged() -> None:
    market = _market()
    venue = _venue()
    empty = OrderBookSnapshot(
        snapshot_id="ob_empty",
        market_id=market.market_id,
        captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        bids=[],
        asks=[],
        metadata={},
    )
    crossed = OrderBookSnapshot(
        snapshot_id="ob_crossed",
        market_id=market.market_id,
        captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.60"), quantity=Decimal("10"))],
        asks=[PriceLevel(price=Decimal("0.55"), quantity=Decimal("10"))],
        metadata={},
    )

    assert derive_liquidity_snapshot_from_orderbook(market, empty, venue).is_empty_book
    assert derive_liquidity_snapshot_from_orderbook(market, crossed, venue).is_crossed_book


def _venue() -> Venue:
    return Venue(
        venue_id="venue_test",
        name="Venue Test",
        jurisdiction=None,
        venue_type=VenueType.OTHER,
        metadata={},
    )


def _market() -> Market:
    return Market(
        market_id="mkt_test",
        venue_id="venue_test",
        event_id="event_test",
        title="Test market",
        description=None,
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
        created_time=None,
        close_time=None,
        settlement_time=None,
        metadata={"external_market_id": "external_test"},
    )
