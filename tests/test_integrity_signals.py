from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.integrity.enums import IntegrityActionHint, SignalCategory
from prediction_desk.integrity.models import MarketFeatureSnapshot
from prediction_desk.integrity.signals import generate_integrity_signals


def test_orderbook_structure_signals_fire() -> None:
    signals = generate_integrity_signals(
        _feature(is_empty_book=True, is_crossed_book=True)
    )

    assert {signal.signal_name for signal in signals} >= {"EMPTY_BOOK", "CROSSED_BOOK"}
    assert all(signal.action_hint == IntegrityActionHint.NO_TRADE for signal in signals[:2])


def test_liquidity_anomaly_signals_fire() -> None:
    signals = generate_integrity_signals(
        _feature(
            has_missing_bid_or_ask=True,
            spread=Decimal("0.22"),
            spread_change_abs=Decimal("0.06"),
            depth_change_pct=Decimal("-0.60"),
        )
    )

    names = {signal.signal_name for signal in signals}
    assert {"ONE_SIDED_BOOK", "WIDE_SPREAD", "SPREAD_WIDENING", "DEPTH_COLLAPSE"} <= names


def test_price_jump_and_stale_market_data_signals_fire() -> None:
    signals = generate_integrity_signals(
        _feature(price_change_abs=Decimal("0.11"), freshness_seconds=7200)
    )

    by_name = {signal.signal_name: signal for signal in signals}
    assert by_name["PRICE_JUMP"].action_hint == IntegrityActionHint.MANUAL_REVIEW
    assert by_name["STALE_MARKET_DATA"].action_hint == IntegrityActionHint.MANUAL_REVIEW


def test_extreme_book_imbalance_is_labeled_as_proxy_only() -> None:
    [signal] = generate_integrity_signals(_feature(book_imbalance=Decimal("0.90")))

    assert signal.category == SignalCategory.MANIPULATION_PROXY
    assert "heuristic" in signal.message
    assert "not proof of manipulation" in signal.message


def test_low_quality_and_rule_change_signals_fire() -> None:
    signals = generate_integrity_signals(
        _feature(
            market_data_quality_score=35,
            rule_changed_recently=True,
            price_change_abs=Decimal("0.06"),
        )
    )

    names = {signal.signal_name for signal in signals}
    assert {"LOW_DATA_QUALITY", "RULE_CHANGED_RECENTLY", "RULE_CHANGE_PRICE_COUPLING"} <= names


def test_signal_hashes_are_deterministic() -> None:
    feature = _feature(spread=Decimal("0.12"))

    first = generate_integrity_signals(feature)
    second = generate_integrity_signals(feature)

    assert [signal.output_hash for signal in first] == [signal.output_hash for signal in second]


def _feature(**overrides) -> MarketFeatureSnapshot:
    values = {
        "feature_snapshot_id": "feature_test",
        "market_id": "mkt_test",
        "asof_timestamp": datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        "generated_at": datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        "available_at": datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        "price": Decimal("0.50"),
        "bid": Decimal("0.45"),
        "ask": Decimal("0.55"),
        "mid": Decimal("0.50"),
        "spread": Decimal("0.02"),
        "total_bid_depth": Decimal("10"),
        "total_ask_depth": Decimal("10"),
        "total_depth": Decimal("20"),
        "is_empty_book": False,
        "is_crossed_book": False,
        "has_missing_bid_or_ask": False,
        "market_data_quality_reason_codes": [],
        "input_hash": "feature_hash",
    }
    values.update(overrides)
    return MarketFeatureSnapshot(**values)
