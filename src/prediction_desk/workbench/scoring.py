"""Deterministic review-priority scoring for the desk workbench."""

from __future__ import annotations

from typing import Any

from prediction_desk.workbench.enums import (
    RecommendedReviewAction,
    ReviewPriorityBucket,
)

_PRETRADE_BLOCK_ACTIONS = {"NO_TRADE", "MANUAL_REVIEW"}
_PRETRADE_REVIEW_ACTIONS = {"PASSIVE_ONLY", "ALLOW_SMALLER_SIZE"}
_DIVERGENCE_REVIEW_STATUSES = {"WATCH", "MATERIAL_DIVERGENCE", "NEEDS_REVIEW"}
_DIVERGENCE_BLOCK_CONTEXT = {"DO_NOT_COMPARE"}
_INTEGRITY_REVIEW_HINTS = {"NO_TRADE", "MANUAL_REVIEW"}
_RESEARCH_REVIEW_TYPES = {
    "HYPOTHETICAL_INTENT",
    "FILTER_BLOCK",
    "REVIEW_ONLY",
    "WATCH",
}


def priority_bucket(score: int) -> ReviewPriorityBucket:
    if score >= 85:
        return ReviewPriorityBucket.CRITICAL
    if score >= 70:
        return ReviewPriorityBucket.HIGH
    if score >= 45:
        return ReviewPriorityBucket.MEDIUM
    if score >= 20:
        return ReviewPriorityBucket.LOW
    return ReviewPriorityBucket.INFO


def recommended_action(reason_codes: list[str]) -> RecommendedReviewAction:
    reasons = set(reason_codes)
    if reasons & {"PRETRADE_BLOCKED", "PRETRADE_MANUAL_REVIEW"}:
        return RecommendedReviewAction.REVIEW_PRETRADE_BLOCK
    if reasons & {"DIVERGENCE_REVIEW", "DIVERGENCE_MATERIAL", "DIVERGENCE_NEEDS_REVIEW"}:
        return RecommendedReviewAction.REVIEW_DIVERGENCE
    if reasons & {"INTEGRITY_REVIEW", "INTEGRITY_HIGH_RISK"}:
        return RecommendedReviewAction.REVIEW_INTEGRITY
    if reasons & {
        "MISSING_RULE_SNAPSHOT",
        "MISSING_ORDERBOOK",
        "MISSING_PRICE_SNAPSHOT",
        "MISSING_LIQUIDITY_SNAPSHOT",
        "STALE_MARKET_DATA",
        "LOW_DATA_QUALITY",
    }:
        return RecommendedReviewAction.REVIEW_DATA_GAP
    if reasons & {"RESEARCH_SIGNAL_REVIEW", "RESEARCH_PRETRADE_BLOCKED"}:
        return RecommendedReviewAction.REVIEW_RESEARCH_SIGNAL
    if reasons & {"NO_RULE_SNAPSHOT"}:
        return RecommendedReviewAction.REVIEW_CONTRACT
    if reasons & {"WATCH_MARKET"}:
        return RecommendedReviewAction.WATCH_ONLY
    return RecommendedReviewAction.NO_ACTION


def score_review_context(
    *,
    quality_report: Any | None,
    integrity_assessment: Any | None,
    divergence_assessments: list[Any],
    pretrade_decision: Any | None,
    research_signals: list[Any],
    data_gaps: list[Any],
    scenario_feature: Any | None,
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    for gap in data_gaps:
        gap_type = _value(getattr(gap, "gap_type", "UNKNOWN"))
        severity = _value(getattr(gap, "severity", "INFO"))
        reasons.append(gap_type)
        if severity == "CRITICAL":
            score += 45
        elif severity == "ERROR":
            score += 35
        elif severity == "WARNING":
            score += 20
        else:
            score += 8

    if quality_report is None:
        reasons.append("MISSING_QUALITY_REPORT")
        score += 15
    else:
        quality_score = int(getattr(quality_report, "quality_score", 0))
        if quality_score < 50:
            reasons.append("LOW_DATA_QUALITY")
            score += 25
        elif quality_score < 70:
            reasons.append("MEDIUM_DATA_QUALITY")
            score += 10

    if integrity_assessment is not None:
        action_hint = _value(getattr(integrity_assessment, "action_hint", ""))
        risk_score = int(getattr(integrity_assessment, "overall_risk_score", 0))
        if action_hint in _INTEGRITY_REVIEW_HINTS or risk_score >= 70:
            reasons.append("INTEGRITY_HIGH_RISK")
            score += 35
        elif risk_score >= 50:
            reasons.append("INTEGRITY_REVIEW")
            score += 20

    for divergence in divergence_assessments:
        status = _value(getattr(divergence, "status", ""))
        score_value = int(getattr(divergence, "overall_divergence_score", 0))
        if status in _DIVERGENCE_BLOCK_CONTEXT:
            reasons.append("DIVERGENCE_NEEDS_REVIEW")
            score += 25
        elif status in _DIVERGENCE_REVIEW_STATUSES:
            reasons.append(
                "DIVERGENCE_MATERIAL" if score_value >= 70 else "DIVERGENCE_REVIEW"
            )
            score += 30 if score_value >= 70 else 20

    if pretrade_decision is not None:
        action = _value(getattr(pretrade_decision, "action", ""))
        if action in _PRETRADE_BLOCK_ACTIONS:
            reasons.append(
                "PRETRADE_BLOCKED" if action == "NO_TRADE" else "PRETRADE_MANUAL_REVIEW"
            )
            score += 40
        elif action in _PRETRADE_REVIEW_ACTIONS:
            reasons.append("PRETRADE_CONSTRAINED")
            score += 15

    for signal in research_signals:
        signal_type = _value(getattr(signal, "signal_type", ""))
        action_bias = _value(getattr(signal, "action_bias", ""))
        if signal_type in _RESEARCH_REVIEW_TYPES or action_bias in {"BLOCK", "REVIEW_ONLY"}:
            reasons.append("RESEARCH_SIGNAL_REVIEW")
            score += 15

    if scenario_feature is not None:
        uncertainty = getattr(scenario_feature, "scenario_uncertainty_score", None)
        narrative_risk = getattr(scenario_feature, "narrative_risk_score", None)
        shock_risk = getattr(scenario_feature, "shock_risk_score", None)
        if (
            _score_at_least(uncertainty, 70)
            or _score_at_least(narrative_risk, 70)
            or _score_at_least(shock_risk, 70)
        ):
            reasons.append("SCENARIO_CONTEXT_REVIEW")
            score += 10

    if not reasons:
        reasons.append("NO_REVIEW_SIGNAL")
    elif score < 20:
        reasons.append("WATCH_MARKET")

    return min(score, 100), _dedupe(reasons)


def _score_at_least(value: Any, threshold: int) -> bool:
    return value is not None and int(value) >= threshold


def _value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
