"""Deterministic fast-lane integrity signal heuristics."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.integrity.enums import (
    IntegrityActionHint,
    SignalCategory,
    SignalSeverity,
)
from prediction_desk.integrity.models import (
    SIGNAL_VERSION,
    IntegritySignal,
    MarketFeatureSnapshot,
    compute_signal_input_hash,
    compute_signal_output_hash,
)

DEFAULT_THRESHOLDS: dict[str, Decimal | int] = {
    "depth_collapse_threshold": Decimal("-0.50"),
    "extreme_imbalance_threshold": Decimal("0.80"),
    "freshness_threshold_seconds": 3600,
    "price_jump_error_threshold": Decimal("0.10"),
    "price_jump_warning_threshold": Decimal("0.05"),
    "rule_price_coupling_threshold": Decimal("0.05"),
    "spread_widening_threshold": Decimal("0.05"),
    "wide_spread_threshold": Decimal("0.10"),
}


def generate_integrity_signals(
    feature: MarketFeatureSnapshot,
    thresholds: dict[str, Any] | None = None,
) -> list[IntegritySignal]:
    """Returns all deterministic integrity signals triggered by a feature snapshot."""

    config = _thresholds(thresholds)
    signals: list[IntegritySignal] = []
    if feature.is_empty_book:
        signals.append(
            _signal(
                feature,
                signal_name="EMPTY_BOOK",
                category=SignalCategory.ORDERBOOK_STRUCTURE,
                severity=SignalSeverity.CRITICAL,
                score=100,
                action_hint=IntegrityActionHint.NO_TRADE,
                reason_code="EMPTY_BOOK",
                message="Order book has no visible bid or ask liquidity.",
                evidence={
                    "latest_liquidity_snapshot_id": feature.latest_liquidity_snapshot_id,
                    "is_empty_book": feature.is_empty_book,
                },
            )
        )
    if feature.is_crossed_book:
        signals.append(
            _signal(
                feature,
                signal_name="CROSSED_BOOK",
                category=SignalCategory.ORDERBOOK_STRUCTURE,
                severity=SignalSeverity.CRITICAL,
                score=100,
                action_hint=IntegrityActionHint.NO_TRADE,
                reason_code="CROSSED_BOOK",
                message="Order book is crossed because best bid exceeds best ask.",
                evidence={
                    "bid": feature.bid,
                    "ask": feature.ask,
                    "spread": feature.spread,
                },
            )
        )
    if feature.has_missing_bid_or_ask and not feature.is_empty_book:
        signals.append(
            _signal(
                feature,
                signal_name="ONE_SIDED_BOOK",
                category=SignalCategory.LIQUIDITY_ANOMALY,
                severity=SignalSeverity.ERROR,
                score=75,
                action_hint=IntegrityActionHint.PASSIVE_ONLY,
                reason_code="ONE_SIDED_BOOK",
                message="Order book is one-sided; bid or ask liquidity is missing.",
                evidence={"bid": feature.bid, "ask": feature.ask},
            )
        )
    if feature.spread is not None:
        wide_threshold = _decimal(config["wide_spread_threshold"])
        if feature.spread >= wide_threshold:
            is_error = feature.spread >= wide_threshold * Decimal("2")
            signals.append(
                _signal(
                    feature,
                    signal_name="WIDE_SPREAD",
                    category=SignalCategory.LIQUIDITY_ANOMALY,
                    severity=SignalSeverity.ERROR if is_error else SignalSeverity.WARNING,
                    score=75 if is_error else 55,
                    action_hint=IntegrityActionHint.PASSIVE_ONLY,
                    reason_code="WIDE_SPREAD",
                    message="Bid/ask spread is wide for a probability-style market.",
                    evidence={"spread": feature.spread, "threshold": wide_threshold},
                )
            )
    if feature.spread_change_abs is not None:
        widening_threshold = _decimal(config["spread_widening_threshold"])
        if feature.spread_change_abs >= widening_threshold:
            severe = feature.spread_change_abs >= widening_threshold * Decimal("2")
            signals.append(
                _signal(
                    feature,
                    signal_name="SPREAD_WIDENING",
                    category=SignalCategory.LIQUIDITY_ANOMALY,
                    severity=SignalSeverity.WARNING,
                    score=65 if severe else 50,
                    action_hint=(
                        IntegrityActionHint.PASSIVE_ONLY
                        if severe
                        else IntegrityActionHint.ALLOW_SMALLER_SIZE
                    ),
                    reason_code="SPREAD_WIDENING",
                    message="Spread widened materially versus the prior as-of feature.",
                    evidence={
                        "spread": feature.spread,
                        "spread_change_abs": feature.spread_change_abs,
                        "threshold": widening_threshold,
                    },
                )
            )
    if feature.depth_change_pct is not None:
        collapse_threshold = _decimal(config["depth_collapse_threshold"])
        if feature.depth_change_pct <= collapse_threshold:
            severe = feature.depth_change_pct <= Decimal("-0.75")
            signals.append(
                _signal(
                    feature,
                    signal_name="DEPTH_COLLAPSE",
                    category=SignalCategory.LIQUIDITY_ANOMALY,
                    severity=SignalSeverity.ERROR,
                    score=85 if severe else 70,
                    action_hint=IntegrityActionHint.PASSIVE_ONLY,
                    reason_code="DEPTH_COLLAPSE",
                    message="Visible book depth collapsed versus the prior as-of feature.",
                    evidence={
                        "total_depth": feature.total_depth,
                        "depth_change_pct": feature.depth_change_pct,
                        "threshold": collapse_threshold,
                    },
                )
            )
    price_move = _abs_first(feature.price_change_abs, feature.mid_change_abs)
    if price_move is not None:
        warning_threshold = _decimal(config["price_jump_warning_threshold"])
        error_threshold = _decimal(config["price_jump_error_threshold"])
        if price_move >= warning_threshold:
            is_error = price_move >= error_threshold
            signals.append(
                _signal(
                    feature,
                    signal_name="PRICE_JUMP",
                    category=SignalCategory.PRICE_ANOMALY,
                    severity=SignalSeverity.ERROR if is_error else SignalSeverity.WARNING,
                    score=75 if is_error else 55,
                    action_hint=(
                        IntegrityActionHint.MANUAL_REVIEW
                        if is_error
                        else IntegrityActionHint.ALLOW_SMALLER_SIZE
                    ),
                    reason_code="PRICE_JUMP",
                    message="Market price moved sharply versus the prior as-of feature.",
                    evidence={
                        "price_change_abs": feature.price_change_abs,
                        "mid_change_abs": feature.mid_change_abs,
                        "warning_threshold": warning_threshold,
                        "error_threshold": error_threshold,
                    },
                )
            )
    if feature.freshness_seconds is not None:
        freshness_threshold = int(config["freshness_threshold_seconds"])
        if feature.freshness_seconds > freshness_threshold:
            severe = feature.freshness_seconds >= freshness_threshold * 2
            signals.append(
                _signal(
                    feature,
                    signal_name="STALE_MARKET_DATA",
                    category=SignalCategory.DATA_FRESHNESS,
                    severity=SignalSeverity.ERROR if severe else SignalSeverity.WARNING,
                    score=80 if severe else 55,
                    action_hint=(
                        IntegrityActionHint.MANUAL_REVIEW
                        if severe
                        else IntegrityActionHint.ALLOW_SMALLER_SIZE
                    ),
                    reason_code="STALE_MARKET_DATA",
                    message="Latest market data is stale for the configured threshold.",
                    evidence={
                        "freshness_seconds": feature.freshness_seconds,
                        "threshold_seconds": freshness_threshold,
                    },
                )
            )
    if feature.book_imbalance is not None:
        imbalance_threshold = _decimal(config["extreme_imbalance_threshold"])
        if abs(feature.book_imbalance) >= imbalance_threshold:
            signals.append(
                _signal(
                    feature,
                    signal_name="EXTREME_BOOK_IMBALANCE",
                    category=SignalCategory.MANIPULATION_PROXY,
                    severity=SignalSeverity.WARNING,
                    score=55,
                    action_hint=IntegrityActionHint.ALLOW_SMALLER_SIZE,
                    reason_code="EXTREME_BOOK_IMBALANCE",
                    message=(
                        "Extreme book imbalance is a heuristic manipulation-risk proxy "
                        "only, not proof of manipulation."
                    ),
                    evidence={
                        "book_imbalance": feature.book_imbalance,
                        "threshold": imbalance_threshold,
                    },
                )
            )
    if feature.market_data_quality_score is not None and feature.market_data_quality_score < 70:
        quality_score = feature.market_data_quality_score
        if quality_score < 20:
            severity = SignalSeverity.CRITICAL
            score = 95
            action_hint = IntegrityActionHint.NO_TRADE
        elif quality_score < 40:
            severity = SignalSeverity.ERROR
            score = 75
            action_hint = IntegrityActionHint.MANUAL_REVIEW
        else:
            severity = SignalSeverity.WARNING
            score = 50
            action_hint = IntegrityActionHint.ALLOW_SMALLER_SIZE
        signals.append(
            _signal(
                feature,
                signal_name="LOW_DATA_QUALITY",
                category=SignalCategory.DATA_QUALITY,
                severity=severity,
                score=score,
                action_hint=action_hint,
                reason_code="LOW_DATA_QUALITY",
                message="Market-data quality score is below the configured usable range.",
                evidence={
                    "market_data_quality_score": quality_score,
                    "market_data_quality_reason_codes": sorted(
                        feature.market_data_quality_reason_codes
                    ),
                },
            )
        )
    if feature.rule_changed_recently:
        signals.append(
            _signal(
                feature,
                signal_name="RULE_CHANGED_RECENTLY",
                category=SignalCategory.RULE_CHANGE,
                severity=SignalSeverity.WARNING,
                score=55,
                action_hint=IntegrityActionHint.MANUAL_REVIEW,
                reason_code="RULE_CHANGED_RECENTLY",
                message="Market rule text changed within the feature lookback window.",
                evidence={
                    "latest_rule_diff_id": feature.latest_rule_diff_id,
                    "rule_change_age_seconds": feature.rule_change_age_seconds,
                },
            )
    )
    coupling_threshold = _decimal(config["rule_price_coupling_threshold"])
    if (
        feature.rule_changed_recently
        and price_move is not None
        and price_move >= coupling_threshold
    ):
        severe = price_move >= Decimal("0.10")
        signals.append(
            _signal(
                feature,
                signal_name="RULE_CHANGE_PRICE_COUPLING",
                category=SignalCategory.RULE_PRICE_COUPLING,
                severity=SignalSeverity.ERROR,
                score=85 if severe else 70,
                action_hint=(
                    IntegrityActionHint.NO_TRADE
                    if severe
                    else IntegrityActionHint.MANUAL_REVIEW
                ),
                reason_code="RULE_CHANGE_PRICE_COUPLING",
                message="Recent rule change coincides with a sharp price move.",
                evidence={
                    "latest_rule_diff_id": feature.latest_rule_diff_id,
                    "price_change_abs": feature.price_change_abs,
                    "mid_change_abs": feature.mid_change_abs,
                    "threshold": coupling_threshold,
                },
            )
        )
    return sorted(signals, key=lambda signal: signal.signal_name)


def _signal(
    feature: MarketFeatureSnapshot,
    *,
    signal_name: str,
    category: SignalCategory,
    severity: SignalSeverity,
    score: int,
    action_hint: IntegrityActionHint,
    reason_code: str,
    message: str,
    evidence: dict[str, Any],
) -> IntegritySignal:
    input_hash = compute_signal_input_hash(feature, signal_name)
    signal = IntegritySignal(
        integrity_signal_id="pending",
        market_id=feature.market_id,
        asof_timestamp=feature.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=feature.available_at,
        feature_snapshot_id=feature.feature_snapshot_id,
        signal_name=signal_name,
        signal_version=SIGNAL_VERSION,
        category=category,
        severity=severity,
        score=max(0, min(100, score)),
        action_hint=action_hint,
        reason_code=reason_code,
        message=message,
        evidence=evidence,
        input_hash=input_hash,
        output_hash="pending",
    )
    output_hash = compute_signal_output_hash(signal)
    return signal.model_copy(
        update={
            "integrity_signal_id": f"integrity_signal_{output_hash[:24]}",
            "output_hash": output_hash,
        }
    )


def _thresholds(values: dict[str, Any] | None) -> dict[str, Decimal | int]:
    config = dict(DEFAULT_THRESHOLDS)
    for key, value in (values or {}).items():
        if key not in config:
            continue
        if isinstance(config[key], Decimal):
            config[key] = _decimal(value)
        else:
            config[key] = int(value)
    return config


def _decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _abs_first(first: Decimal | None, second: Decimal | None) -> Decimal | None:
    value = first if first is not None else second
    return abs(value) if value is not None else None
