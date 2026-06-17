from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.divergence.enums import (
    DivergenceActionHint,
    DivergenceSignalCategory,
    DivergenceSignalSeverity,
)
from prediction_desk.divergence.models import CrossVenueDivergenceSnapshot
from prediction_desk.divergence.signals import generate_divergence_signals

ASOF = datetime(2026, 6, 16, 12, 20, tzinfo=UTC)


def test_do_not_compare_context_signal_fires() -> None:
    snapshot = _snapshot(do_not_compare=True, comparison_permission="DO_NOT_COMPARE")

    signals = generate_divergence_signals(snapshot)

    assert signals[0].signal_name == "DO_NOT_COMPARE_CONTEXT"
    assert signals[0].action_hint == DivergenceActionHint.DO_NOT_COMPARE


def test_manual_review_equivalence_context_signal_fires() -> None:
    snapshot = _snapshot(
        manual_review_required=True,
        comparison_permission="MANUAL_REVIEW",
        absolute_mid_gap=Decimal("0.04"),
    )

    signals = generate_divergence_signals(snapshot)

    assert any(signal.signal_name == "MANUAL_REVIEW_EQUIVALENCE_CONTEXT" for signal in signals)


def test_watch_material_and_critical_price_gap_signals_do_not_use_forbidden_words() -> None:
    snapshot = _snapshot(absolute_mid_gap=Decimal("0.11"))

    signals = generate_divergence_signals(snapshot)
    price_signal = next(
        signal for signal in signals if signal.signal_name == "EQUIVALENT_PRICE_GAP"
    )

    assert price_signal.severity == DivergenceSignalSeverity.CRITICAL
    assert price_signal.action_hint == DivergenceActionHint.MANUAL_REVIEW
    forbidden_terms = ("arbit" + "rage", "pro" + "fit")
    assert all(term not in price_signal.message.lower() for term in forbidden_terms)


def test_spread_adjusted_stale_low_quality_liquidity_and_integrity_signals_fire() -> None:
    snapshot = _snapshot(
        absolute_mid_gap=Decimal("0.06"),
        spread_adjusted_gap=Decimal("0.03"),
        stale_side="left",
        low_quality_data=True,
        left_quality_score=50,
        right_quality_score=90,
        high_integrity_risk=True,
        left_integrity_risk_score=75,
        one_sided_or_empty_book=True,
    )

    signals = generate_divergence_signals(snapshot)
    names = {signal.signal_name for signal in signals}

    assert "SPREAD_ADJUSTED_DIVERGENCE" in names
    assert "STALE_SIDE_DIVERGENCE" in names
    assert "LOW_LIQUIDITY_DIVERGENCE" in names
    assert "LOW_DATA_QUALITY_DIVERGENCE" in names
    assert "HIGH_INTEGRITY_RISK_DIVERGENCE" in names
    assert any(signal.category == DivergenceSignalCategory.INTEGRITY_CONTEXT for signal in signals)


def test_comparable_with_haircut_signal_fires() -> None:
    snapshot = _snapshot(
        comparable=False,
        comparable_with_haircut=True,
        comparison_permission="COMPARABLE_WITH_HAIRCUT",
        absolute_mid_gap=Decimal("0.04"),
    )

    signals = generate_divergence_signals(snapshot)

    assert any(signal.signal_name == "COMPARABLE_WITH_HAIRCUT_DIVERGENCE" for signal in signals)


def _snapshot(**updates: object) -> CrossVenueDivergenceSnapshot:
    data = {
        "divergence_snapshot_id": "snapshot_test",
        "equivalence_assessment_id": "equivalence_test",
        "left_market_id": "left",
        "right_market_id": "right",
        "asof_timestamp": ASOF,
        "generated_at": ASOF,
        "available_at": ASOF,
        "equivalence_status": "EQUIVALENT",
        "comparison_permission": "COMPARABLE",
        "equivalence_score": 90,
        "equivalence_confidence_score": 90,
        "outcome_relation": "SAME",
        "left_price": Decimal("0.50"),
        "right_price_raw": Decimal("0.56"),
        "right_price_aligned": Decimal("0.56"),
        "left_mid": Decimal("0.50"),
        "right_mid_raw": Decimal("0.56"),
        "right_mid_aligned": Decimal("0.56"),
        "left_bid": Decimal("0.49"),
        "left_ask": Decimal("0.51"),
        "right_bid_raw": Decimal("0.55"),
        "right_ask_raw": Decimal("0.57"),
        "right_bid_aligned": Decimal("0.55"),
        "right_ask_aligned": Decimal("0.57"),
        "signed_mid_gap": Decimal("-0.06"),
        "absolute_mid_gap": Decimal("0.06"),
        "signed_price_gap": Decimal("-0.06"),
        "absolute_price_gap": Decimal("0.06"),
        "gap_bps": Decimal("1200"),
        "combined_spread": Decimal("0.04"),
        "spread_adjusted_gap": Decimal("0.04"),
        "left_spread": Decimal("0.02"),
        "right_spread": Decimal("0.02"),
        "left_total_depth": Decimal("100"),
        "right_total_depth": Decimal("100"),
        "min_total_depth": Decimal("100"),
        "left_quality_score": 90,
        "right_quality_score": 90,
        "left_integrity_risk_score": 10,
        "right_integrity_risk_score": 10,
        "comparable": True,
        "comparable_with_haircut": False,
        "manual_review_required": False,
        "do_not_compare": False,
        "missing_price_data": False,
        "missing_liquidity_data": False,
        "stale_data": False,
        "low_quality_data": False,
        "high_integrity_risk": False,
        "wide_spread": False,
        "one_sided_or_empty_book": False,
        "input_hash": "input",
        "output_hash": "output",
    }
    data.update(updates)
    return CrossVenueDivergenceSnapshot.model_validate(data)
