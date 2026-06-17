from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.domain.models import OrderBookSnapshot, PriceLevel
from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.scoring.trust_verdict import build_trust_verdict


def test_high_resolution_risk_forces_no_trade() -> None:
    _, ambiguous, *_ = sample_markets()

    verdict = build_trust_verdict(
        market=ambiguous.market,
        rule_snapshot=ambiguous.rule_snapshot,
        orderbook_snapshot=ambiguous.orderbook_snapshot,
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
    )

    assert verdict.resolution_risk_score == 100
    assert verdict.action is VerdictAction.NO_TRADE


def test_missing_orderbook_requires_manual_review_when_rules_are_clean() -> None:
    clean, *_ = sample_markets()

    verdict = build_trust_verdict(
        market=clean.market,
        rule_snapshot=clean.rule_snapshot,
        orderbook_snapshot=None,
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
    )

    assert verdict.liquidity_risk_score == 90
    assert verdict.action is VerdictAction.MANUAL_REVIEW
    assert "missing_orderbook_snapshot" in verdict.reason_codes


def test_wide_binary_spread_selects_passive_only_for_clean_market() -> None:
    clean, *_ = sample_markets()
    wide_book = OrderBookSnapshot(
        snapshot_id="wide_book",
        market_id=clean.market.market_id,
        captured_at=datetime(2026, 6, 16, tzinfo=UTC),
        bids=[PriceLevel(price=Decimal("0.40"), quantity=Decimal("10"))],
        asks=[PriceLevel(price=Decimal("0.60"), quantity=Decimal("10"))],
    )

    verdict = build_trust_verdict(
        market=clean.market,
        rule_snapshot=clean.rule_snapshot,
        orderbook_snapshot=wide_book,
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
    )

    assert verdict.resolution_risk_score == 0
    assert verdict.liquidity_risk_score == 70
    assert verdict.action is VerdictAction.PASSIVE_ONLY
    assert "wide_binary_spread" in verdict.reason_codes
