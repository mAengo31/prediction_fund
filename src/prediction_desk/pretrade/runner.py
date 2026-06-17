"""Run-once pre-trade gate checks."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction, PreTradeRunStatus
from prediction_desk.pretrade.models import (
    PRETRADE_RUNNER_VERSION,
    PreTradeDecision,
    PreTradeRun,
    PreTradeRunConfig,
    PreTradeRunResult,
    PreTradeRunSummary,
)
from prediction_desk.pretrade.service import PreTradeService, PreTradeServiceError


class PreTradeRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_pretrade_checks(
    config: PreTradeRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> PreTradeRunResult:
    if repo is not None:
        return _run_pretrade_checks(config, repo)
    with session_scope(database_url) as session:
        return _run_pretrade_checks(config, PredictionMarketRepository(session))


def summarize_pretrade_run(
    pretrade_run_id: str,
    decisions: list[PreTradeDecision],
) -> PreTradeRunSummary:
    total = len(decisions)
    action_counts = Counter(decision.action.value for decision in decisions)
    total_requested = sum(
        (decision.requested_size_units for decision in decisions),
        Decimal("0"),
    )
    total_allowed = sum(
        (decision.final_allowed_size_units for decision in decisions),
        Decimal("0"),
    )
    average_scores = {
        "composite_risk_score": (
            sum(Decimal(decision.composite_risk_score) for decision in decisions)
            / Decimal(total)
            if total
            else Decimal("0")
        )
    }
    return PreTradeRunSummary(
        summary_id=f"pretrade_summary_{uuid4().hex[:24]}",
        pretrade_run_id=pretrade_run_id,
        created_at=datetime.now(tz=UTC),
        total_decisions=total,
        action_counts=dict(sorted(action_counts.items())),
        average_scores=average_scores,
        no_trade_rate=_rate(action_counts[PreTradeAction.NO_TRADE.value], total),
        manual_review_rate=_rate(action_counts[PreTradeAction.MANUAL_REVIEW.value], total),
        passive_only_rate=_rate(action_counts[PreTradeAction.PASSIVE_ONLY.value], total),
        allow_smaller_size_rate=_rate(
            action_counts[PreTradeAction.ALLOW_SMALLER_SIZE.value],
            total,
        ),
        allow_rate=_rate(action_counts[PreTradeAction.ALLOW.value], total),
        hard_block_rate=_rate(
            sum(1 for decision in decisions if decision.hard_blocked),
            total,
        ),
        total_requested_size_units=total_requested,
        total_final_allowed_size_units=total_allowed,
        metadata={"runner_version": PRETRADE_RUNNER_VERSION},
    )


def _run_pretrade_checks(
    config: PreTradeRunConfig,
    repo: PredictionMarketRepository,
) -> PreTradeRunResult:
    markets = repo.list_markets(limit=10000)
    if config.market_ids:
        requested = set(config.market_ids)
        markets = [market for market in markets if market.market_id in requested]
    if len(markets) > config.max_checks:
        raise PreTradeRunError("too_many_pretrade_checks")
    now = datetime.now(tz=UTC)
    run = PreTradeRun(
        pretrade_run_id=f"pretrade_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=PreTradeRunStatus.RUNNING,
        asof_timestamp=config.asof_timestamp,
        policy_id=config.policy_id,
        market_ids=[market.market_id for market in markets],
        max_checks=config.max_checks,
        config={
            **config.model_dump(mode="json"),
            "runner_version": PRETRADE_RUNNER_VERSION,
        },
        metadata=dict(config.metadata),
    )
    repo.save_pretrade_run(run)
    service = PreTradeService(repo)
    decisions: list[PreTradeDecision] = []
    errors: list[dict[str, Any]] = []
    try:
        for market in markets:
            try:
                result = service.check_market_default_intent(
                    market.market_id,
                    config.asof_timestamp,
                    policy_id=config.policy_id,
                    strategy_context=config.strategy_context,
                    intent_type=config.intent_type,
                    requested_size_units=config.default_requested_size_units,
                )
                decisions.append(result.decision)
            except PreTradeServiceError as exc:
                errors.append(
                    {
                        "market_id": market.market_id,
                        "error_code": exc.code,
                        "error_message": exc.message,
                    }
                )
        summary = summarize_pretrade_run(run.pretrade_run_id, decisions)
        repo.save_pretrade_run_summary(summary)
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": PreTradeRunStatus.COMPLETED
                if not errors
                else PreTradeRunStatus.PARTIAL,
                "decisions_created": len(decisions),
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_pretrade_run(completed)
        return PreTradeRunResult(run=completed, decisions=decisions, summary=summary)
    except Exception:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": PreTradeRunStatus.FAILED,
                "errors_count": max(1, len(errors)),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_pretrade_run(failed)
        raise


def _rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)
