from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.replay.evaluation import summarize_replay_steps
from prediction_desk.replay.models import ReplayStep


def test_summary_metrics_are_correct() -> None:
    steps = [
        _step("1", VerdictAction.ALLOW.value, Decimal("1.0"), 10, 20),
        _step("2", VerdictAction.PASSIVE_ONLY.value, Decimal("0.25"), 30, 80),
        _step("3", VerdictAction.NO_TRADE.value, Decimal("0.0"), None, None, error=True),
        _step("4", VerdictAction.MANUAL_REVIEW.value, Decimal("0.0"), 50, 70),
    ]

    summary = summarize_replay_steps("run", steps)

    assert summary.total_steps == 4
    assert summary.errored_steps == 1
    assert summary.action_counts[VerdictAction.ALLOW.value] == 1
    assert summary.no_trade_rate == Decimal("0.25")
    assert summary.manual_review_rate == Decimal("0.25")
    assert summary.passive_only_rate == Decimal("0.25")
    assert summary.allow_rate == Decimal("0.25")
    assert summary.allowed_exposure_units == Decimal("1.25")
    assert summary.blocked_exposure_units == Decimal("2.75")
    assert summary.average_scores["resolution_risk_score"] == Decimal("30")
    assert summary.markets_replayed == 1


def _step(
    step_id: str,
    action: str,
    multiplier: Decimal,
    resolution_risk_score: int | None,
    liquidity_risk_score: int | None,
    *,
    error: bool = False,
) -> ReplayStep:
    return ReplayStep(
        step_id=step_id,
        run_id="run",
        market_id="mkt",
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
        action=action,
        allowed_size_multiplier=multiplier,
        resolution_risk_score=resolution_risk_score,
        liquidity_risk_score=liquidity_risk_score,
        reason_codes=[],
        input_hash=f"in-{step_id}",
        output_hash=f"out-{step_id}",
        error_code="error" if error else None,
    )
