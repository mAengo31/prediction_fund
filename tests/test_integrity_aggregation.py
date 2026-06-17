from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.integrity.aggregation import aggregate_integrity_signals
from prediction_desk.integrity.enums import IntegrityActionHint, SignalSeverity
from prediction_desk.integrity.models import MarketFeatureSnapshot
from prediction_desk.integrity.signals import generate_integrity_signals


def test_aggregation_picks_max_severity_and_most_restrictive_action() -> None:
    feature = _feature(is_empty_book=True, market_data_quality_score=65)
    signals = generate_integrity_signals(feature)

    assessment = aggregate_integrity_signals(feature, signals)

    assert assessment.severity == SignalSeverity.CRITICAL
    assert assessment.action_hint == IntegrityActionHint.NO_TRADE
    assert assessment.overall_risk_score == 100


def test_aggregation_deduplicates_reason_codes_deterministically() -> None:
    feature = _feature(spread=Decimal("0.12"))
    signals = generate_integrity_signals(feature)
    signals.append(signals[0])

    assessment = aggregate_integrity_signals(feature, signals)

    assert assessment.reason_codes == sorted(set(assessment.reason_codes))
    assert assessment.reason_codes == ["WIDE_SPREAD"]


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
        "total_depth": Decimal("20"),
        "is_empty_book": False,
        "is_crossed_book": False,
        "has_missing_bid_or_ask": False,
        "market_data_quality_reason_codes": [],
        "input_hash": "feature_hash",
    }
    values.update(overrides)
    return MarketFeatureSnapshot(**values)
