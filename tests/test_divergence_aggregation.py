from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.divergence.aggregation import aggregate_divergence_signals
from prediction_desk.divergence.enums import DivergenceActionHint, DivergenceStatus
from prediction_desk.divergence.signals import generate_divergence_signals
from tests.test_divergence_signals import _snapshot


def test_aggregation_picks_most_restrictive_action_and_deduplicates_reasons() -> None:
    snapshot = _snapshot(
        absolute_mid_gap=Decimal("0.06"),
        stale_side="left",
        stale_data=True,
        low_quality_data=True,
        left_quality_score=50,
    )
    signals = generate_divergence_signals(snapshot)
    duplicated = signals + [signals[0].model_copy(update={"divergence_signal_id": "copy"})]

    assessment = aggregate_divergence_signals(snapshot, duplicated)

    assert assessment.status == DivergenceStatus.NEEDS_REVIEW
    assert assessment.action_hint == DivergenceActionHint.MANUAL_REVIEW
    assert assessment.reason_codes == sorted(set(assessment.reason_codes))


def test_aggregation_marks_do_not_compare() -> None:
    snapshot = _snapshot(do_not_compare=True, comparison_permission="DO_NOT_COMPARE")
    assessment = aggregate_divergence_signals(snapshot, generate_divergence_signals(snapshot))

    assert assessment.status == DivergenceStatus.DO_NOT_COMPARE
    assert assessment.overall_divergence_score == 100


def test_persistent_divergence_signal_fires_after_prior_assessments() -> None:
    snapshot = _snapshot(absolute_mid_gap=Decimal("0.04"))
    previous = [
        aggregate_divergence_signals(
            _snapshot(
                divergence_snapshot_id=f"snapshot_{index}",
                asof_timestamp=datetime(2026, 6, 16, 10 + index, tzinfo=UTC),
            ),
            [],
        ).model_copy(update={"status": DivergenceStatus.WATCH})
        for index in range(3)
    ]

    signals = generate_divergence_signals(snapshot, previous_assessments=previous)

    assert any(signal.signal_name == "PERSISTENT_DIVERGENCE" for signal in signals)

