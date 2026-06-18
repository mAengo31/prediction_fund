"""Deterministic review-priority scoring for the desk workbench."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from prediction_desk.workbench.enums import (
    RecommendedReviewAction,
    ReviewPriorityBucket,
)

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
_DATA_QUALITY_ONLY_REASONS = {
    "LOW_DATA_QUALITY",
    "MISSING_QUALITY_REPORT",
    "STALE_MARKET_DATA",
    "MISSING_RULE_SNAPSHOT",
    "MISSING_ORDERBOOK",
    "MISSING_PRICE_SNAPSHOT",
    "MISSING_LIQUIDITY_SNAPSHOT",
    "MISSING_MARKET_DATA_QUALITY",
    "LOW_MARKET_DATA_QUALITY",
}
_HARD_PRETRADE_REASONS = {
    "MARKET_NOT_ACTIVE",
    "RESOLUTION_RISK_ABOVE_POLICY_LIMIT",
    "DIVERGENCE_DO_NOT_COMPARE_CONTEXT",
    "EXPOSURE_LIMIT_BREACH",
}


@dataclass(frozen=True)
class ReviewScoreDetails:
    priority_score: int
    reason_codes: list[str]
    score_components: dict[str, int]
    score_explanation: list[str]
    hard_escalators: list[str]
    soft_escalators: list[str]
    dampeners: list[str]


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
    if reasons & {
        "DIVERGENCE_REVIEW",
        "DIVERGENCE_MATERIAL",
        "DIVERGENCE_NEEDS_REVIEW",
        "DIVERGENCE_DO_NOT_COMPARE",
    }:
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
    details = score_review_context_details(
        quality_report=quality_report,
        integrity_assessment=integrity_assessment,
        divergence_assessments=divergence_assessments,
        pretrade_decision=pretrade_decision,
        research_signals=research_signals,
        data_gaps=data_gaps,
        scenario_feature=scenario_feature,
    )
    return details.priority_score, details.reason_codes


def score_review_context_details(
    *,
    quality_report: Any | None,
    integrity_assessment: Any | None,
    divergence_assessments: list[Any],
    pretrade_decision: Any | None,
    research_signals: list[Any],
    data_gaps: list[Any],
    scenario_feature: Any | None,
) -> ReviewScoreDetails:
    components: dict[str, int] = {}
    explanations: list[str] = []
    hard_escalators: list[str] = []
    soft_escalators: list[str] = []
    dampeners: list[str] = []
    reasons: list[str] = []

    data_gap_points = 0
    for gap in data_gaps:
        gap_type = _value(getattr(gap, "gap_type", "UNKNOWN"))
        severity = _value(getattr(gap, "severity", "INFO"))
        reasons.append(gap_type)
        data_gap_points += _gap_points(gap_type, severity)
        if severity in {"CRITICAL", "ERROR"}:
            soft_escalators.append(f"{gap_type}_{severity}")
        if _public_empty_rule_marker(gap):
            dampeners.append("PUBLIC_DETAIL_RULE_TEXT_EMPTY")
    if data_gap_points:
        _component(
            components,
            explanations,
            "data_gaps",
            min(data_gap_points, 35),
            "latest data gap batch requires desk review",
        )

    quality_only_context = False
    active_review_context = bool(pretrade_decision or research_signals or divergence_assessments)
    if quality_report is None:
        reasons.append("MISSING_QUALITY_REPORT")
        _component(
            components,
            explanations,
            "data_quality",
            20,
            "market has no as-of quality report",
        )
        quality_only_context = True
    else:
        quality_score = int(getattr(quality_report, "quality_score", 0))
        if quality_score < 50:
            reasons.append("LOW_DATA_QUALITY")
            _component(
                components,
                explanations,
                "data_quality",
                30,
                "market-data quality is low",
            )
            quality_only_context = True
        elif quality_score < 70:
            reasons.append("MEDIUM_DATA_QUALITY")
            _component(
                components,
                explanations,
                "data_quality",
                12,
                "market-data quality is moderate",
            )

    integrity_data_quality_only = False
    if integrity_assessment is not None:
        action_hint = _value(getattr(integrity_assessment, "action_hint", ""))
        risk_score = int(getattr(integrity_assessment, "overall_risk_score", 0))
        severity = _value(getattr(integrity_assessment, "severity", ""))
        integrity_reasons = [
            _value(reason) for reason in getattr(integrity_assessment, "reason_codes", [])
        ]
        integrity_data_quality_only = _only_data_quality_reasons(integrity_reasons)
        integrity_hard = (
            (action_hint == "NO_TRADE" or severity == "CRITICAL" or risk_score >= 90)
            and not integrity_data_quality_only
        )
        if integrity_hard:
            reasons.append("INTEGRITY_HIGH_RISK")
            hard_escalators.append("INTEGRITY_HIGH_RISK")
            _component(
                components,
                explanations,
                "integrity",
                85,
                "integrity context has a hard review escalator",
            )
        elif action_hint in _INTEGRITY_REVIEW_HINTS or risk_score >= 70 or severity == "ERROR":
            reasons.append("INTEGRITY_HIGH_RISK")
            soft_escalators.append("INTEGRITY_HIGH_RISK")
            _component(
                components,
                explanations,
                "integrity",
                65 if integrity_data_quality_only else 70,
                "integrity context requires review",
            )
            if integrity_data_quality_only:
                dampeners.append("INTEGRITY_FROM_DATA_QUALITY_ONLY")
        elif risk_score >= 50:
            reasons.append("INTEGRITY_REVIEW")
            soft_escalators.append("INTEGRITY_REVIEW")
            _component(
                components,
                explanations,
                "integrity",
                30,
                "integrity context has a moderate warning",
            )

    for divergence in divergence_assessments:
        status = _value(getattr(divergence, "status", ""))
        score_value = int(getattr(divergence, "overall_divergence_score", 0))
        action_hint = _value(getattr(divergence, "action_hint", ""))
        if status in _DIVERGENCE_BLOCK_CONTEXT or action_hint == "DO_NOT_COMPARE":
            reasons.append("DIVERGENCE_DO_NOT_COMPARE")
            hard_escalators.append("DIVERGENCE_DO_NOT_COMPARE")
            _component(
                components,
                explanations,
                "divergence",
                85,
                "cross-venue context says the pair should not be compared",
            )
        elif status == "NEEDS_REVIEW" or action_hint == "MANUAL_REVIEW":
            reasons.append("DIVERGENCE_NEEDS_REVIEW")
            soft_escalators.append("DIVERGENCE_NEEDS_REVIEW")
            _component(
                components,
                explanations,
                "divergence",
                70,
                "cross-venue divergence needs desk review",
            )
        elif status == "MATERIAL_DIVERGENCE" or score_value >= 70:
            reasons.append("DIVERGENCE_MATERIAL")
            soft_escalators.append("DIVERGENCE_MATERIAL")
            _component(
                components,
                explanations,
                "divergence",
                70,
                "material cross-venue divergence needs review",
            )
        elif status in _DIVERGENCE_REVIEW_STATUSES:
            reasons.append("DIVERGENCE_REVIEW")
            soft_escalators.append("DIVERGENCE_REVIEW")
            _component(
                components,
                explanations,
                "divergence",
                35,
                "cross-venue divergence is watchlisted",
            )

    if pretrade_decision is not None:
        action = _value(getattr(pretrade_decision, "action", ""))
        hard_blockers = [_value(item) for item in getattr(pretrade_decision, "hard_blockers", [])]
        pretrade_reasons = [
            _value(item) for item in getattr(pretrade_decision, "reason_codes", [])
        ]
        pretrade_hard = _pretrade_has_hard_blocker(
            hard_blockers,
            pretrade_reasons,
            integrity_data_quality_only=integrity_data_quality_only,
        )
        if action == "NO_TRADE":
            reasons.append("PRETRADE_BLOCKED")
            if pretrade_hard:
                hard_escalators.append("PRETRADE_HARD_BLOCK")
                _component(
                    components,
                    explanations,
                    "pretrade",
                    90,
                    "pre-trade gate produced a hard no-trade blocker",
                )
            else:
                soft_escalators.append("PRETRADE_BLOCKED")
                _component(
                    components,
                    explanations,
                    "pretrade",
                    75,
                    "pre-trade gate blocked the hypothetical intent without a hard blocker",
                )
        elif action == "MANUAL_REVIEW":
            reasons.append("PRETRADE_MANUAL_REVIEW")
            soft_escalators.append("PRETRADE_MANUAL_REVIEW")
            _component(
                components,
                explanations,
                "pretrade",
                70,
                "pre-trade gate requires manual review",
            )
        elif action in _PRETRADE_REVIEW_ACTIONS:
            reasons.append("PRETRADE_CONSTRAINED")
            soft_escalators.append("PRETRADE_CONSTRAINED")
            _component(
                components,
                explanations,
                "pretrade",
                35,
                "pre-trade gate constrained the hypothetical intent",
            )

    research_points = 0
    for signal in research_signals:
        signal_type = _value(getattr(signal, "signal_type", ""))
        action_bias = _value(getattr(signal, "action_bias", ""))
        if signal_type in _RESEARCH_REVIEW_TYPES or action_bias in {"BLOCK", "REVIEW_ONLY"}:
            reasons.append("RESEARCH_SIGNAL_REVIEW")
            soft_escalators.append("RESEARCH_SIGNAL_REVIEW")
            research_points += 18
    if research_points:
        _component(
            components,
            explanations,
            "research",
            min(research_points, 35),
            "research signal context needs desk review",
        )

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
            soft_escalators.append("SCENARIO_CONTEXT_REVIEW")
            _component(
                components,
                explanations,
                "scenario",
                15,
                "slow-lane scenario context needs review",
            )

    if quality_only_context and not active_review_context:
        dampeners.append("NO_ACTIVE_REVIEW_CONTEXT")
    if _only_low_priority_reasons(reasons):
        dampeners.append("DATA_GAP_ONLY_CONTEXT")
    if "STALE_MARKET_DATA" in reasons and len(set(reasons)) == 1:
        dampeners.append("STALE_ONLY_CONTEXT")

    score = min(sum(components.values()), 100)
    if dampeners:
        score = max(0, score - min(20, 5 * len(_dedupe(dampeners))))

    if hard_escalators:
        score = max(score, 85)
    elif score >= 85:
        score = 84

    if not reasons:
        reasons.append("NO_REVIEW_SIGNAL")
    elif score < 20:
        reasons.append("WATCH_MARKET")

    ordered_reasons = _order_reasons(
        _dedupe(reasons),
        hard_escalators=hard_escalators,
        soft_escalators=soft_escalators,
    )
    return ReviewScoreDetails(
        priority_score=min(score, 100),
        reason_codes=ordered_reasons,
        score_components=dict(sorted(components.items())),
        score_explanation=explanations,
        hard_escalators=_dedupe(hard_escalators),
        soft_escalators=_dedupe(soft_escalators),
        dampeners=_dedupe(dampeners),
    )


def _gap_points(gap_type: str, severity: str) -> int:
    base = {
        "MISSING_RULE_SNAPSHOT": 12,
        "MISSING_ORDERBOOK": 15,
        "MISSING_PRICE_SNAPSHOT": 15,
        "MISSING_LIQUIDITY_SNAPSHOT": 15,
        "STALE_MARKET_DATA": 8,
        "MISSING_QUALITY_REPORT": 18,
        "NORMALIZATION_ERROR": 20,
        "UNSUPPORTED_HISTORICAL_ENDPOINT": 8,
    }.get(gap_type, 8)
    if severity == "CRITICAL":
        return max(base, 35)
    if severity == "ERROR":
        return max(base, 25)
    if severity == "WARNING":
        return max(base, 15)
    return base


def _component(
    components: dict[str, int],
    explanations: list[str],
    key: str,
    points: int,
    explanation: str,
) -> None:
    if points > components.get(key, 0):
        components[key] = points
    if explanation not in explanations:
        explanations.append(explanation)


def _only_data_quality_reasons(reasons: list[str]) -> bool:
    return bool(reasons) and set(reasons).issubset(_DATA_QUALITY_ONLY_REASONS)


def _only_low_priority_reasons(reasons: list[str]) -> bool:
    if not reasons:
        return False
    low_priority = _DATA_QUALITY_ONLY_REASONS | {"WATCH_MARKET", "NO_REVIEW_SIGNAL"}
    return set(reasons).issubset(low_priority)


def _pretrade_has_hard_blocker(
    hard_blockers: list[str],
    reason_codes: list[str],
    *,
    integrity_data_quality_only: bool,
) -> bool:
    if not hard_blockers:
        return False
    if set(hard_blockers).issubset({"INTEGRITY_ACTION_HINT_NO_TRADE"}):
        return not integrity_data_quality_only
    if set(hard_blockers) & _HARD_PRETRADE_REASONS:
        return True
    explicit_restriction_blockers = [
        blocker
        for blocker in hard_blockers
        if blocker not in {"INTEGRITY_ACTION_HINT_NO_TRADE"}
    ]
    return bool(explicit_restriction_blockers or set(reason_codes) & _HARD_PRETRADE_REASONS)


def _public_empty_rule_marker(gap: Any) -> bool:
    values = [
        getattr(gap, "reason_code", ""),
        getattr(gap, "description", ""),
        *[
            str(value)
            for value in getattr(gap, "metadata", {}).values()
            if value is not None
        ],
    ]
    joined = " ".join(str(value).upper() for value in values)
    return (
        "NO_RULE_TEXT_IN_PUBLIC_DETAIL_PAYLOAD" in joined
        or "PUBLIC_DETAIL_RULE_TEXT_EMPTY" in joined
        or "EMPTY_RULE_TEXT" in joined
    )


def _order_reasons(
    reasons: list[str],
    *,
    hard_escalators: list[str],
    soft_escalators: list[str],
) -> list[str]:
    ordered: list[str] = []
    for reason in hard_escalators:
        if reason in reasons and reason not in ordered:
            ordered.append(reason)
    for reason in soft_escalators:
        if reason in reasons and reason not in ordered:
            ordered.append(reason)
    for reason in reasons:
        if reason not in ordered:
            ordered.append(reason)
    return ordered


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
