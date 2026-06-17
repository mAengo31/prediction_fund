"""Aggregate point-in-time integrity signals into an assessment."""

from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.integrity.enums import (
    IntegrityActionHint,
    SignalCategory,
    SignalSeverity,
)
from prediction_desk.integrity.models import (
    IntegrityAssessment,
    IntegritySignal,
    MarketFeatureSnapshot,
    compute_assessment_input_hash,
    compute_assessment_output_hash,
)

_SEVERITY_RANK: dict[SignalSeverity, int] = {
    SignalSeverity.INFO: 0,
    SignalSeverity.WARNING: 1,
    SignalSeverity.ERROR: 2,
    SignalSeverity.CRITICAL: 3,
}

_ACTION_RANK: dict[IntegrityActionHint, int] = {
    IntegrityActionHint.NONE: 0,
    IntegrityActionHint.ALLOW: 0,
    IntegrityActionHint.ALLOW_SMALLER_SIZE: 1,
    IntegrityActionHint.PASSIVE_ONLY: 2,
    IntegrityActionHint.MANUAL_REVIEW: 3,
    IntegrityActionHint.NO_TRADE: 4,
}


def aggregate_integrity_signals(
    feature_snapshot: MarketFeatureSnapshot,
    signals: list[IntegritySignal],
) -> IntegrityAssessment:
    """Combines triggered signals with transparent max-risk aggregation."""

    category_scores = _category_scores(signals)
    severity = max(
        (signal.severity for signal in signals),
        key=lambda item: _SEVERITY_RANK[item],
        default=SignalSeverity.INFO,
    )
    action_hint = max(
        (signal.action_hint for signal in signals),
        key=lambda item: _ACTION_RANK[item],
        default=IntegrityActionHint.NONE,
    )
    reason_codes = sorted({signal.reason_code for signal in signals})
    overall_risk_score = max(category_scores.values(), default=0)
    input_hash = compute_assessment_input_hash(feature_snapshot, signals)
    assessment = IntegrityAssessment(
        integrity_assessment_id="pending",
        market_id=feature_snapshot.market_id,
        asof_timestamp=feature_snapshot.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=feature_snapshot.available_at,
        feature_snapshot_id=feature_snapshot.feature_snapshot_id,
        signal_ids=sorted(signal.integrity_signal_id for signal in signals),
        overall_risk_score=overall_risk_score,
        price_anomaly_score=category_scores[SignalCategory.PRICE_ANOMALY],
        liquidity_anomaly_score=category_scores[SignalCategory.LIQUIDITY_ANOMALY],
        freshness_risk_score=category_scores[SignalCategory.DATA_FRESHNESS],
        orderbook_structure_score=category_scores[SignalCategory.ORDERBOOK_STRUCTURE],
        rule_change_risk_score=category_scores[SignalCategory.RULE_CHANGE],
        rule_price_coupling_score=category_scores[SignalCategory.RULE_PRICE_COUPLING],
        data_quality_risk_score=category_scores[SignalCategory.DATA_QUALITY],
        manipulation_proxy_score=category_scores[SignalCategory.MANIPULATION_PROXY],
        severity=severity,
        action_hint=action_hint,
        reason_codes=reason_codes,
        input_hash=input_hash,
        output_hash="pending",
        metadata={
            "aggregation": "max_category_score",
            "action_hint_rule": "most_restrictive",
            "severity_rule": "max_severity",
        },
    )
    output_hash = compute_assessment_output_hash(assessment)
    return assessment.model_copy(
        update={
            "integrity_assessment_id": f"integrity_assessment_{output_hash[:24]}",
            "output_hash": output_hash,
        }
    )


def _category_scores(signals: list[IntegritySignal]) -> dict[SignalCategory, int]:
    scores = {
        SignalCategory.PRICE_ANOMALY: 0,
        SignalCategory.LIQUIDITY_ANOMALY: 0,
        SignalCategory.DATA_FRESHNESS: 0,
        SignalCategory.ORDERBOOK_STRUCTURE: 0,
        SignalCategory.RULE_CHANGE: 0,
        SignalCategory.RULE_PRICE_COUPLING: 0,
        SignalCategory.DATA_QUALITY: 0,
        SignalCategory.MANIPULATION_PROXY: 0,
        SignalCategory.UNKNOWN: 0,
    }
    for signal in signals:
        scores[signal.category] = max(scores.get(signal.category, 0), signal.score)
    return scores
