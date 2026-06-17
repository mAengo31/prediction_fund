"""Aggregate divergence signals into a pair/outcome assessment."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.divergence.enums import (
    DivergenceActionHint,
    DivergenceSignalCategory,
    DivergenceSignalSeverity,
    DivergenceStatus,
)
from prediction_desk.divergence.models import (
    CrossVenueDivergenceAssessment,
    CrossVenueDivergenceSignal,
    CrossVenueDivergenceSnapshot,
    compute_assessment_input_hash,
    compute_assessment_output_hash,
)

_SEVERITY_ORDER = {
    DivergenceSignalSeverity.INFO: 0,
    DivergenceSignalSeverity.WARNING: 1,
    DivergenceSignalSeverity.ERROR: 2,
    DivergenceSignalSeverity.CRITICAL: 3,
}
_ACTION_ORDER = {
    DivergenceActionHint.NONE: 0,
    DivergenceActionHint.WATCH: 1,
    DivergenceActionHint.RESEARCH: 2,
    DivergenceActionHint.MANUAL_REVIEW: 3,
    DivergenceActionHint.DO_NOT_COMPARE: 4,
}


def aggregate_divergence_signals(
    snapshot: CrossVenueDivergenceSnapshot,
    signals: list[CrossVenueDivergenceSignal],
) -> CrossVenueDivergenceAssessment:
    category_scores = _category_scores(signals)
    severity = _max_severity(signals)
    action_hint = _max_action_hint(signals)
    overall_score = max(category_scores.values(), default=0)
    reason_codes = sorted({signal.reason_code for signal in signals})
    status = _status(snapshot, category_scores, signals)
    if status == DivergenceStatus.DO_NOT_COMPARE:
        action_hint = DivergenceActionHint.DO_NOT_COMPARE
        severity = DivergenceSignalSeverity.CRITICAL
        overall_score = max(overall_score, 100)
    elif status == DivergenceStatus.NEEDS_REVIEW:
        action_hint = max(
            action_hint,
            DivergenceActionHint.MANUAL_REVIEW,
            key=lambda item: _ACTION_ORDER[item],
        )
        severity = max(
            severity,
            DivergenceSignalSeverity.ERROR,
            key=lambda item: _SEVERITY_ORDER[item],
        )

    assessment = CrossVenueDivergenceAssessment(
        divergence_assessment_id="pending",
        divergence_snapshot_id=snapshot.divergence_snapshot_id,
        equivalence_assessment_id=snapshot.equivalence_assessment_id,
        outcome_mapping_id=snapshot.outcome_mapping_id,
        left_market_id=snapshot.left_market_id,
        right_market_id=snapshot.right_market_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=snapshot.available_at,
        signal_ids=sorted(signal.divergence_signal_id for signal in signals),
        overall_divergence_score=overall_score,
        price_divergence_score=category_scores[
            DivergenceSignalCategory.PRICE_DIVERGENCE.value
        ],
        spread_adjusted_score=category_scores[
            DivergenceSignalCategory.SPREAD_ADJUSTED_DIVERGENCE.value
        ],
        persistence_score=category_scores[DivergenceSignalCategory.PERSISTENCE.value],
        stale_side_score=category_scores[DivergenceSignalCategory.STALE_SIDE.value],
        low_liquidity_score=category_scores[DivergenceSignalCategory.LOW_LIQUIDITY.value],
        low_data_quality_score=category_scores[
            DivergenceSignalCategory.LOW_DATA_QUALITY.value
        ],
        integrity_context_score=category_scores[
            DivergenceSignalCategory.INTEGRITY_CONTEXT.value
        ],
        equivalence_context_score=category_scores[
            DivergenceSignalCategory.EQUIVALENCE_CONTEXT.value
        ],
        status=status,
        severity=severity,
        action_hint=action_hint,
        reason_codes=reason_codes,
        absolute_mid_gap=snapshot.absolute_mid_gap,
        spread_adjusted_gap=snapshot.spread_adjusted_gap,
        gap_bps=snapshot.gap_bps,
        comparison_permission=snapshot.comparison_permission,
        equivalence_score=snapshot.equivalence_score,
        equivalence_confidence_score=snapshot.equivalence_confidence_score,
        input_hash="pending",
        output_hash="pending",
        metadata={
            "aggregation": "max_category_score_most_restrictive_action_v1",
            "score_convention": "higher_is_more_divergence_or_context_risk",
        },
    )
    input_hash = compute_assessment_input_hash(snapshot, signals)
    output_hash = compute_assessment_output_hash(
        assessment.model_copy(update={"input_hash": input_hash})
    )
    return assessment.model_copy(
        update={
            "divergence_assessment_id": f"divergence_assessment_{output_hash[:24]}",
            "input_hash": input_hash,
            "output_hash": output_hash,
        }
    )


def _category_scores(signals: list[CrossVenueDivergenceSignal]) -> dict[str, int]:
    scores = {category.value: 0 for category in DivergenceSignalCategory}
    for signal in signals:
        scores[signal.category.value] = max(scores[signal.category.value], signal.score)
    return scores


def _max_severity(signals: list[CrossVenueDivergenceSignal]) -> DivergenceSignalSeverity:
    if not signals:
        return DivergenceSignalSeverity.INFO
    return max(signals, key=lambda signal: _SEVERITY_ORDER[signal.severity]).severity


def _max_action_hint(signals: list[CrossVenueDivergenceSignal]) -> DivergenceActionHint:
    if not signals:
        return DivergenceActionHint.NONE
    return max(signals, key=lambda signal: _ACTION_ORDER[signal.action_hint]).action_hint


def _status(
    snapshot: CrossVenueDivergenceSnapshot,
    category_scores: dict[str, int],
    signals: list[CrossVenueDivergenceSignal],
) -> DivergenceStatus:
    if snapshot.do_not_compare or any(
        signal.action_hint == DivergenceActionHint.DO_NOT_COMPARE for signal in signals
    ):
        return DivergenceStatus.DO_NOT_COMPARE
    if (
        snapshot.manual_review_required
        or snapshot.stale_data
        or snapshot.low_quality_data
        or snapshot.high_integrity_risk
    ):
        return DivergenceStatus.NEEDS_REVIEW
    if (
        category_scores[DivergenceSignalCategory.PRICE_DIVERGENCE.value] >= 75
        or category_scores[DivergenceSignalCategory.SPREAD_ADJUSTED_DIVERGENCE.value] >= 75
    ) and (snapshot.comparable or snapshot.comparable_with_haircut):
        return DivergenceStatus.MATERIAL_DIVERGENCE
    if signals and (snapshot.comparable or snapshot.comparable_with_haircut):
        return DivergenceStatus.WATCH
    return DivergenceStatus.NO_DIVERGENCE


def rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)

