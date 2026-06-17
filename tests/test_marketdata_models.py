from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.marketdata.enums import MarketPriceSource
from prediction_desk.marketdata.models import MarketPriceSnapshot, compute_market_price_hash


def test_market_price_snapshot_hash_is_deterministic() -> None:
    snapshot = _price_snapshot(price=Decimal("0.50"))

    first_hash = compute_market_price_hash(snapshot)
    second_hash = compute_market_price_hash(snapshot.model_copy())

    assert first_hash == second_hash


def test_market_price_snapshot_hash_changes_when_price_changes() -> None:
    first = _price_snapshot(price=Decimal("0.50"))
    second = _price_snapshot(price=Decimal("0.51"))

    assert compute_market_price_hash(first) != compute_market_price_hash(second)


def _price_snapshot(*, price: Decimal) -> MarketPriceSnapshot:
    return MarketPriceSnapshot(
        price_snapshot_id="price_test",
        market_id="mkt_test",
        outcome_id=None,
        venue_id="venue_test",
        venue_name="Venue Test",
        source=MarketPriceSource.MANUAL_FIXTURE,
        observed_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        captured_at=datetime(2026, 6, 16, 12, 5, tzinfo=UTC),
        available_at=datetime(2026, 6, 16, 12, 5, tzinfo=UTC),
        price=price,
        bid=price - Decimal("0.01"),
        ask=price + Decimal("0.01"),
        mid=price,
        spread=Decimal("0.02"),
        last_trade_price=None,
        volume=None,
        open_interest=None,
        source_payload_id=None,
        orderbook_snapshot_id=None,
        external_market_id="external_test",
        external_outcome_id=None,
        data_hash="pending",
        metadata={},
    )
