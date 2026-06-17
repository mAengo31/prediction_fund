from __future__ import annotations

from decimal import Decimal

from prediction_desk.divergence.pricing import (
    align_right_bid_ask_for_outcome_relation,
    align_right_price_for_outcome_relation,
    compute_gap_bps,
    compute_spread_adjusted_gap,
)


def test_same_outcome_price_alignment_returns_right_price() -> None:
    assert align_right_price_for_outcome_relation(Decimal("0.42"), "SAME") == Decimal("0.42")


def test_inverse_outcome_price_alignment_returns_complement() -> None:
    assert align_right_price_for_outcome_relation(Decimal("0.42"), "INVERSE") == Decimal("0.58")


def test_inverse_bid_ask_alignment_maps_conservatively() -> None:
    bid, ask = align_right_bid_ask_for_outcome_relation(
        Decimal("0.30"),
        Decimal("0.35"),
        "INVERSE",
    )
    assert bid == Decimal("0.65")
    assert ask == Decimal("0.70")


def test_inverse_bid_ask_alignment_handles_missing_sides() -> None:
    bid, ask = align_right_bid_ask_for_outcome_relation(None, Decimal("0.35"), "INVERSE")
    assert bid == Decimal("0.65")
    assert ask is None


def test_gap_bps_and_spread_adjusted_gap_are_deterministic() -> None:
    assert compute_gap_bps(Decimal("0.05"), Decimal("0.50")) == Decimal("1000.00")
    assert compute_spread_adjusted_gap(
        Decimal("0.10"),
        Decimal("0.02"),
        Decimal("0.04"),
    ) == Decimal("0.07")

