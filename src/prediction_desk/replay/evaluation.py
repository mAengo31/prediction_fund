"""Replay evaluation summaries for admissibility decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.replay.models import ReplayRunSummary, ReplayStep

SCORE_FIELDS = (
    "price_integrity_score",
    "resolution_risk_score",
    "liquidity_risk_score",
    "cross_venue_consistency_score",
    "information_freshness_score",
    "manipulation_risk_score",
)


def summarize_replay_steps(run_id: str, steps: list[ReplayStep]) -> ReplayRunSummary:
    total_steps = len(steps)
    errored_steps = sum(1 for step in steps if step.error_code is not None)
    action_counts = _action_counts(steps)
    average_scores = _average_scores(steps)
    allowed_exposure_units = sum(
        (step.allowed_size_multiplier for step in steps),
        start=Decimal("0"),
    )
    blocked_exposure_units = Decimal(total_steps) - allowed_exposure_units
    markets_replayed = len({step.market_id for step in steps})

    return ReplayRunSummary(
        summary_id=_summary_id(run_id),
        run_id=run_id,
        created_at=datetime.now(tz=UTC),
        total_steps=total_steps,
        errored_steps=errored_steps,
        action_counts=action_counts,
        average_scores=average_scores,
        no_trade_rate=_rate(action_counts.get(VerdictAction.NO_TRADE.value, 0), total_steps),
        manual_review_rate=_rate(
            action_counts.get(VerdictAction.MANUAL_REVIEW.value, 0),
            total_steps,
        ),
        passive_only_rate=_rate(
            action_counts.get(VerdictAction.PASSIVE_ONLY.value, 0),
            total_steps,
        ),
        allow_rate=_rate(
            action_counts.get(VerdictAction.ALLOW.value, 0)
            + action_counts.get(VerdictAction.ALLOW_SMALLER_SIZE.value, 0),
            total_steps,
        ),
        allowed_exposure_units=allowed_exposure_units,
        blocked_exposure_units=blocked_exposure_units,
        markets_replayed=markets_replayed,
        metadata={"evaluator_version": "replay_evaluation_v1"},
    )


def _action_counts(steps: list[ReplayStep]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in steps:
        counts[step.action] = counts.get(step.action, 0) + 1
    return dict(sorted(counts.items()))


def _average_scores(steps: list[ReplayStep]) -> dict[str, Decimal]:
    averages: dict[str, Decimal] = {}
    for field_name in SCORE_FIELDS:
        values = [
            value
            for step in steps
            if (value := getattr(step, field_name)) is not None
        ]
        if values:
            averages[field_name] = Decimal(sum(values)) / Decimal(len(values))
        else:
            averages[field_name] = Decimal("0")
    return averages


def _rate(count: int, total_steps: int) -> Decimal:
    if total_steps == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total_steps)


def _summary_id(run_id: str) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {"run_id": run_id, "summary_version": "replay_summary_v1"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return f"replay_summary_{digest[:24]}"
