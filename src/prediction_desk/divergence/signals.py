"""Deterministic cross-venue divergence signal generation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.divergence.enums import (
    DivergenceActionHint,
    DivergenceSignalCategory,
    DivergenceSignalSeverity,
    DivergenceStatus,
)
from prediction_desk.divergence.models import (
    DIVERGENCE_SIGNAL_VERSION,
    CrossVenueDivergenceAssessment,
    CrossVenueDivergenceSignal,
    CrossVenueDivergenceSnapshot,
    compute_signal_input_hash,
    compute_signal_output_hash,
)


def generate_divergence_signals(
    snapshot: CrossVenueDivergenceSnapshot,
    *,
    previous_assessments: list[CrossVenueDivergenceAssessment] | None = None,
    config: dict[str, Any] | None = None,
) -> list[CrossVenueDivergenceSignal]:
    cfg = _Config(config or {})
    signals: list[CrossVenueDivergenceSignal] = []
    if snapshot.do_not_compare:
        signals.append(
            _signal(
                snapshot,
                "DO_NOT_COMPARE_CONTEXT",
                DivergenceSignalCategory.EQUIVALENCE_CONTEXT,
                DivergenceSignalSeverity.CRITICAL,
                100,
                DivergenceActionHint.DO_NOT_COMPARE,
                "DO_NOT_COMPARE_CONTEXT",
                "Comparison is disabled by contract-equivalence context.",
                {"comparison_permission": snapshot.comparison_permission},
            )
        )
        return signals

    if snapshot.manual_review_required:
        severity = (
            DivergenceSignalSeverity.ERROR
            if snapshot.missing_price_data or snapshot.high_integrity_risk
            else DivergenceSignalSeverity.WARNING
        )
        signals.append(
            _signal(
                snapshot,
                "MANUAL_REVIEW_EQUIVALENCE_CONTEXT",
                DivergenceSignalCategory.EQUIVALENCE_CONTEXT,
                severity,
                70 if severity == DivergenceSignalSeverity.ERROR else 50,
                DivergenceActionHint.MANUAL_REVIEW,
                "MANUAL_REVIEW_EQUIVALENCE_CONTEXT",
                "Contract-equivalence context requires review before comparing prices.",
                {
                    "comparison_permission": snapshot.comparison_permission,
                    "missing_price_data": snapshot.missing_price_data,
                    "high_integrity_risk": snapshot.high_integrity_risk,
                },
            )
        )

    gap = snapshot.absolute_mid_gap
    if (snapshot.comparable or snapshot.comparable_with_haircut) and _gte(gap, cfg.watch_gap):
        severity, score, hint = _price_gap_level(gap or Decimal("0"), cfg)
        signals.append(
            _signal(
                snapshot,
                "EQUIVALENT_PRICE_GAP",
                DivergenceSignalCategory.PRICE_DIVERGENCE,
                severity,
                score,
                hint,
                "EQUIVALENT_PRICE_GAP",
                "Cross-venue price divergence detected for comparable contracts.",
                {
                    "absolute_mid_gap": snapshot.absolute_mid_gap,
                    "watch_gap_threshold": cfg.watch_gap,
                    "material_gap_threshold": cfg.material_gap,
                    "critical_gap_threshold": cfg.critical_gap,
                },
            )
        )

    if _gte(snapshot.spread_adjusted_gap, cfg.spread_adjusted_gap):
        severity = (
            DivergenceSignalSeverity.ERROR
            if (snapshot.spread_adjusted_gap or Decimal("0")) >= cfg.spread_adjusted_gap * 2
            else DivergenceSignalSeverity.WARNING
        )
        signals.append(
            _signal(
                snapshot,
                "SPREAD_ADJUSTED_DIVERGENCE",
                DivergenceSignalCategory.SPREAD_ADJUSTED_DIVERGENCE,
                severity,
                80 if severity == DivergenceSignalSeverity.ERROR else 60,
                DivergenceActionHint.MANUAL_REVIEW
                if severity == DivergenceSignalSeverity.ERROR
                else DivergenceActionHint.RESEARCH,
                "SPREAD_ADJUSTED_DIVERGENCE",
                "Cross-venue divergence remains after spread context is applied.",
                {
                    "spread_adjusted_gap": snapshot.spread_adjusted_gap,
                    "combined_spread": snapshot.combined_spread,
                },
            )
        )

    if _gte(gap, cfg.watch_gap) and snapshot.stale_side is not None:
        signals.append(
            _signal(
                snapshot,
                "STALE_SIDE_DIVERGENCE",
                DivergenceSignalCategory.STALE_SIDE,
                DivergenceSignalSeverity.ERROR,
                75,
                DivergenceActionHint.MANUAL_REVIEW,
                "STALE_SIDE_DIVERGENCE",
                "Divergence appears with stale market-data context on at least one side.",
                {"stale_side": snapshot.stale_side},
            )
        )

    if _gte(gap, cfg.watch_gap) and (
        snapshot.wide_spread
        or snapshot.one_sided_or_empty_book
        or snapshot.missing_liquidity_data
        or (snapshot.min_total_depth is not None and snapshot.min_total_depth <= cfg.low_depth)
    ):
        severity = (
            DivergenceSignalSeverity.ERROR
            if snapshot.one_sided_or_empty_book or snapshot.missing_liquidity_data
            else DivergenceSignalSeverity.WARNING
        )
        signals.append(
            _signal(
                snapshot,
                "LOW_LIQUIDITY_DIVERGENCE",
                DivergenceSignalCategory.LOW_LIQUIDITY,
                severity,
                80 if severity == DivergenceSignalSeverity.ERROR else 60,
                DivergenceActionHint.MANUAL_REVIEW,
                "LOW_LIQUIDITY_DIVERGENCE",
                "Divergence appears with weak liquidity context on at least one side.",
                {
                    "wide_spread": snapshot.wide_spread,
                    "one_sided_or_empty_book": snapshot.one_sided_or_empty_book,
                    "missing_liquidity_data": snapshot.missing_liquidity_data,
                    "min_total_depth": snapshot.min_total_depth,
                },
            )
        )

    if _gte(gap, cfg.watch_gap) and (
        (snapshot.left_quality_score is not None and snapshot.left_quality_score < cfg.quality)
        or (snapshot.right_quality_score is not None and snapshot.right_quality_score < cfg.quality)
    ):
        severity = (
            DivergenceSignalSeverity.ERROR
            if min(
                score
                for score in (snapshot.left_quality_score, snapshot.right_quality_score)
                if score is not None
            )
            < 40
            else DivergenceSignalSeverity.WARNING
        )
        signals.append(
            _signal(
                snapshot,
                "LOW_DATA_QUALITY_DIVERGENCE",
                DivergenceSignalCategory.LOW_DATA_QUALITY,
                severity,
                80 if severity == DivergenceSignalSeverity.ERROR else 60,
                DivergenceActionHint.MANUAL_REVIEW,
                "LOW_DATA_QUALITY_DIVERGENCE",
                "Divergence appears with low market-data quality on at least one side.",
                {
                    "left_quality_score": snapshot.left_quality_score,
                    "right_quality_score": snapshot.right_quality_score,
                },
            )
        )

    left_high_integrity = (
        snapshot.left_integrity_risk_score is not None
        and snapshot.left_integrity_risk_score >= cfg.integrity
    )
    right_high_integrity = (
        snapshot.right_integrity_risk_score is not None
        and snapshot.right_integrity_risk_score >= cfg.integrity
    )
    if _gte(gap, cfg.watch_gap) and (left_high_integrity or right_high_integrity):
        signals.append(
            _signal(
                snapshot,
                "HIGH_INTEGRITY_RISK_DIVERGENCE",
                DivergenceSignalCategory.INTEGRITY_CONTEXT,
                DivergenceSignalSeverity.ERROR,
                80,
                DivergenceActionHint.MANUAL_REVIEW,
                "HIGH_INTEGRITY_RISK_DIVERGENCE",
                "Divergence appears with high integrity-risk context on at least one side.",
                {
                    "left_integrity_risk_score": snapshot.left_integrity_risk_score,
                    "right_integrity_risk_score": snapshot.right_integrity_risk_score,
                },
            )
        )

    if snapshot.comparable_with_haircut and _gte(gap, cfg.watch_gap):
        signals.append(
            _signal(
                snapshot,
                "COMPARABLE_WITH_HAIRCUT_DIVERGENCE",
                DivergenceSignalCategory.EQUIVALENCE_CONTEXT,
                DivergenceSignalSeverity.WARNING,
                55,
                DivergenceActionHint.RESEARCH,
                "COMPARABLE_WITH_HAIRCUT_DIVERGENCE",
                "Divergence appears where equivalence allows comparison only with haircut.",
                {"comparison_permission": snapshot.comparison_permission},
            )
        )

    previous = previous_assessments or []
    persistent_count = _persistent_count(
        snapshot,
        previous,
        lookback_seconds=cfg.persistence_lookback_seconds,
    )
    if persistent_count >= cfg.persistence_min_count:
        signals.append(
            _signal(
                snapshot,
                "PERSISTENT_DIVERGENCE",
                DivergenceSignalCategory.PERSISTENCE,
                DivergenceSignalSeverity.ERROR
                if persistent_count >= cfg.persistence_min_count * 2
                else DivergenceSignalSeverity.WARNING,
                80 if persistent_count >= cfg.persistence_min_count * 2 else 60,
                DivergenceActionHint.RESEARCH,
                "PERSISTENT_DIVERGENCE",
                "Similar divergence context has persisted across prior assessments.",
                {
                    "persistent_count": persistent_count,
                    "lookback_seconds": cfg.persistence_lookback_seconds,
                },
            )
        )

    return signals


class _Config:
    def __init__(self, values: dict[str, Any]) -> None:
        self.watch_gap = Decimal(str(values.get("watch_gap_threshold", "0.03")))
        self.material_gap = Decimal(str(values.get("material_gap_threshold", "0.05")))
        self.critical_gap = Decimal(str(values.get("critical_gap_threshold", "0.10")))
        self.spread_adjusted_gap = Decimal(
            str(values.get("spread_adjusted_gap_threshold", "0.02"))
        )
        self.quality = int(values.get("quality_score_threshold", 70))
        self.integrity = int(values.get("integrity_risk_threshold", 70))
        self.low_depth = Decimal(str(values.get("low_depth_threshold", "1")))
        self.persistence_lookback_seconds = int(
            values.get("persistence_lookback_seconds", 86400)
        )
        self.persistence_min_count = int(values.get("persistence_min_count", 3))


def _price_gap_level(
    gap: Decimal,
    config: _Config,
) -> tuple[DivergenceSignalSeverity, int, DivergenceActionHint]:
    if gap >= config.critical_gap:
        return DivergenceSignalSeverity.CRITICAL, 95, DivergenceActionHint.MANUAL_REVIEW
    if gap >= config.material_gap:
        return DivergenceSignalSeverity.ERROR, 80, DivergenceActionHint.RESEARCH
    return DivergenceSignalSeverity.WARNING, 55, DivergenceActionHint.WATCH


def _gte(value: Decimal | None, threshold: Decimal) -> bool:
    return value is not None and value >= threshold


def _persistent_count(
    snapshot: CrossVenueDivergenceSnapshot,
    previous: list[CrossVenueDivergenceAssessment],
    *,
    lookback_seconds: int,
) -> int:
    cutoff = snapshot.asof_timestamp - timedelta(seconds=lookback_seconds)
    statuses = {DivergenceStatus.WATCH, DivergenceStatus.MATERIAL_DIVERGENCE}
    return sum(
        1
        for assessment in previous
        if assessment.status in statuses
        and assessment.asof_timestamp < snapshot.asof_timestamp
        and assessment.asof_timestamp >= cutoff
        and {
            assessment.left_market_id,
            assessment.right_market_id,
        }
        == {snapshot.left_market_id, snapshot.right_market_id}
    )


def _signal(
    snapshot: CrossVenueDivergenceSnapshot,
    signal_name: str,
    category: DivergenceSignalCategory,
    severity: DivergenceSignalSeverity,
    score: int,
    action_hint: DivergenceActionHint,
    reason_code: str,
    message: str,
    evidence: dict[str, Any],
) -> CrossVenueDivergenceSignal:
    generated_at = datetime.now(tz=UTC)
    signal = CrossVenueDivergenceSignal(
        divergence_signal_id=f"divergence_signal_{uuid4().hex[:24]}",
        divergence_snapshot_id=snapshot.divergence_snapshot_id,
        equivalence_assessment_id=snapshot.equivalence_assessment_id,
        left_market_id=snapshot.left_market_id,
        right_market_id=snapshot.right_market_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=generated_at,
        available_at=snapshot.available_at,
        signal_name=signal_name,
        signal_version=DIVERGENCE_SIGNAL_VERSION,
        category=category,
        severity=severity,
        score=max(0, min(100, score)),
        action_hint=action_hint,
        reason_code=reason_code,
        message=message,
        evidence=evidence,
        input_hash="pending",
        output_hash="pending",
        metadata={"signal_generator": "divergence_signals_v1"},
    )
    input_hash = compute_signal_input_hash(snapshot, signal_name)
    output_hash = compute_signal_output_hash(signal.model_copy(update={"input_hash": input_hash}))
    return signal.model_copy(
        update={
            "divergence_signal_id": f"divergence_signal_{output_hash[:24]}",
            "input_hash": input_hash,
            "output_hash": output_hash,
        }
    )
