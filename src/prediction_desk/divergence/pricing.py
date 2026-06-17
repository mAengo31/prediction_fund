"""Deterministic price-alignment utilities for equivalent market comparisons."""

from __future__ import annotations

from decimal import Decimal

from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.marketdata.models import (
    MarketDataQualityReport,
    MarketLiquiditySnapshot,
)


def align_right_price_for_outcome_relation(
    right_price: Decimal | None,
    relation: str | None,
) -> Decimal | None:
    if right_price is None:
        return None
    if relation == "SAME":
        return right_price
    if relation == "INVERSE":
        return Decimal("1") - right_price
    return None


def align_right_bid_ask_for_outcome_relation(
    right_bid: Decimal | None,
    right_ask: Decimal | None,
    relation: str | None,
) -> tuple[Decimal | None, Decimal | None]:
    if relation == "SAME":
        return right_bid, right_ask
    if relation != "INVERSE":
        return None, None
    aligned_bid = Decimal("1") - right_ask if right_ask is not None else None
    aligned_ask = Decimal("1") - right_bid if right_bid is not None else None
    return aligned_bid, aligned_ask


def compute_gap_bps(
    gap: Decimal | None,
    reference_price: Decimal | None,
) -> Decimal | None:
    if gap is None or reference_price is None or reference_price <= Decimal("0"):
        return None
    return (gap / reference_price) * Decimal("10000")


def compute_spread_adjusted_gap(
    absolute_mid_gap: Decimal | None,
    left_spread: Decimal | None,
    right_spread: Decimal | None,
) -> Decimal | None:
    if absolute_mid_gap is None or left_spread is None or right_spread is None:
        return None
    combined = left_spread + right_spread
    return max(Decimal("0"), absolute_mid_gap - (combined / Decimal("2")))


def determine_weaker_side(
    *,
    left_quality_score: int | None,
    right_quality_score: int | None,
    left_integrity_risk_score: int | None,
    right_integrity_risk_score: int | None,
    left_liquidity: MarketLiquiditySnapshot | None,
    right_liquidity: MarketLiquiditySnapshot | None,
) -> str | None:
    left_score = _side_weakness_score(
        quality_score=left_quality_score,
        integrity_risk_score=left_integrity_risk_score,
        liquidity=left_liquidity,
    )
    right_score = _side_weakness_score(
        quality_score=right_quality_score,
        integrity_risk_score=right_integrity_risk_score,
        liquidity=right_liquidity,
    )
    if left_score == 0 and right_score == 0:
        return None
    if left_score == right_score:
        return "both"
    return "left" if left_score > right_score else "right"


def determine_stale_side(
    left_quality: MarketDataQualityReport | None,
    right_quality: MarketDataQualityReport | None,
) -> str | None:
    left_stale = _stale(left_quality)
    right_stale = _stale(right_quality)
    if left_stale and right_stale:
        return "both"
    if left_stale:
        return "left"
    if right_stale:
        return "right"
    return None


def quality_score(report: MarketDataQualityReport | None) -> int | None:
    return report.quality_score if report is not None else None


def integrity_risk_score(assessment: IntegrityAssessment | None) -> int | None:
    return assessment.overall_risk_score if assessment is not None else None


def total_depth(liquidity: MarketLiquiditySnapshot | None) -> Decimal | None:
    if liquidity is None:
        return None
    return liquidity.total_bid_depth + liquidity.total_ask_depth


def _stale(report: MarketDataQualityReport | None) -> bool:
    return report is not None and (
        report.stale_market_data or "STALE_MARKET_DATA" in report.reason_codes
    )


def _side_weakness_score(
    *,
    quality_score: int | None,
    integrity_risk_score: int | None,
    liquidity: MarketLiquiditySnapshot | None,
) -> int:
    score = 0
    if quality_score is None:
        score += 20
    elif quality_score < 40:
        score += 40
    elif quality_score < 70:
        score += 20
    if integrity_risk_score is not None and integrity_risk_score >= 70:
        score += 30
    if liquidity is None:
        score += 20
    elif liquidity.is_empty_book:
        score += 35
    elif liquidity.best_bid is None or liquidity.best_ask is None:
        score += 25
    elif liquidity.spread is not None and liquidity.spread >= Decimal("0.10"):
        score += 15
    if liquidity is not None and total_depth(liquidity) == Decimal("0"):
        score += 10
    return score
