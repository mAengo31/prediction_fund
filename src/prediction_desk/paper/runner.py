"""Run-once paper simulation runner."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.paper.enums import PaperOrderStatus, PaperSimulationRunStatus
from prediction_desk.paper.models import (
    PAPER_RUNNER_VERSION,
    PaperExecutionPolicy,
    PaperOrder,
    PaperPortfolioSnapshot,
    PaperSimulateIntentRequest,
    PaperSimulationRun,
    PaperSimulationRunConfig,
    PaperSimulationRunResult,
    PaperSimulationRunSummary,
    compute_trade_intent_from_request,
)
from prediction_desk.paper.policies import build_default_paper_execution_policy
from prediction_desk.paper.service import PaperExecutionService, PaperServiceError
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import TradeSide
from prediction_desk.pretrade.models import TradeIntent


class PaperRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_paper_simulation(
    config: PaperSimulationRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> PaperSimulationRunResult:
    if repo is not None:
        return _run_paper_simulation(config, repo)
    with session_scope(database_url) as session:
        return _run_paper_simulation(config, PredictionMarketRepository(session))


def generate_paper_timestamps(
    start_time: datetime,
    end_time: datetime,
    interval_seconds: int,
) -> list[datetime]:
    timestamps: list[datetime] = []
    current = start_time
    interval = timedelta(seconds=interval_seconds)
    while current <= end_time:
        timestamps.append(current)
        current += interval
    return timestamps


def summarize_paper_run(
    simulation_run_id: str,
    orders: list[PaperOrder],
    fills_count: int,
    final_portfolio: PaperPortfolioSnapshot | None,
) -> PaperSimulationRunSummary:
    total = len(orders)
    status_counts = Counter(order.status.value for order in orders)
    filled_orders = status_counts[PaperOrderStatus.FILLED.value]
    partial_orders = status_counts[PaperOrderStatus.PARTIALLY_FILLED.value]
    rejected_orders = status_counts[PaperOrderStatus.REJECTED.value]
    return PaperSimulationRunSummary(
        summary_id=f"paper_summary_{uuid4().hex[:24]}",
        simulation_run_id=simulation_run_id,
        created_at=datetime.now(tz=UTC),
        total_orders=total,
        filled_orders=filled_orders,
        partially_filled_orders=partial_orders,
        rejected_orders=rejected_orders,
        total_fills=fills_count,
        total_fees_simulated=(
            final_portfolio.total_fees_simulated if final_portfolio else Decimal("0")
        ),
        final_cash_simulated=(
            final_portfolio.cash_balance_simulated if final_portfolio else Decimal("0")
        ),
        final_gross_exposure_simulated=(
            final_portfolio.gross_exposure_simulated if final_portfolio else Decimal("0")
        ),
        final_net_exposure_simulated=(
            final_portfolio.net_exposure_simulated if final_portfolio else Decimal("0")
        ),
        final_realized_pnl_simulated=(
            final_portfolio.realized_pnl_simulated if final_portfolio else Decimal("0")
        ),
        final_unrealized_pnl_simulated=(
            final_portfolio.unrealized_pnl_simulated if final_portfolio else Decimal("0")
        ),
        final_total_equity_simulated=(
            final_portfolio.total_equity_simulated if final_portfolio else Decimal("0")
        ),
        fill_rate=_rate(filled_orders + partial_orders, total),
        rejection_rate=_rate(rejected_orders, total),
        metadata={"runner_version": PAPER_RUNNER_VERSION},
    )


def _run_paper_simulation(
    config: PaperSimulationRunConfig,
    repo: PredictionMarketRepository,
) -> PaperSimulationRunResult:
    if config.start_time >= config.end_time:
        raise PaperRunError("invalid_paper_time_range")
    policy = _policy(repo, config.paper_policy_id)
    intents = _planned_intents(config, repo)
    if len(intents) > config.max_orders:
        raise PaperRunError("too_many_paper_orders")
    now = datetime.now(tz=UTC)
    run = PaperSimulationRun(
        simulation_run_id=f"paper_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=PaperSimulationRunStatus.RUNNING,
        paper_policy_id=policy.paper_policy_id,
        start_time=config.start_time,
        end_time=config.end_time,
        interval_seconds=config.interval_seconds,
        market_ids=sorted({intent.market_id for intent in intents}),
        max_orders=config.max_orders,
        initial_cash_simulated=config.initial_cash_simulated,
        config={
            **config.model_dump(mode="json"),
            "runner_version": PAPER_RUNNER_VERSION,
            "timestamp_window": "inclusive_start_inclusive_end",
        },
        metadata=dict(config.metadata),
    )
    repo.save_paper_simulation_run(run)
    service = PaperExecutionService(repo)
    orders: list[PaperOrder] = []
    fills_count = 0
    errors: list[dict[str, Any]] = []
    final_portfolio = None
    try:
        for intent in intents:
            try:
                result = service.simulate_trade_intent(
                    intent,
                    paper_policy_id=policy.paper_policy_id,
                    simulation_run_id=run.simulation_run_id,
                    initial_cash_simulated=config.initial_cash_simulated,
                )
                orders.append(result.order)
                fills_count += len(result.fills)
                final_portfolio = result.portfolio_snapshot or final_portfolio
            except PaperServiceError as exc:
                errors.append(
                    {
                        "market_id": intent.market_id,
                        "asof_timestamp": intent.asof_timestamp.isoformat(),
                        "error_code": exc.code,
                        "error_message": exc.message,
                    }
                )
        summary = summarize_paper_run(
            run.simulation_run_id,
            orders,
            fills_count,
            final_portfolio,
        )
        repo.save_paper_simulation_run_summary(summary)
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": PaperSimulationRunStatus.COMPLETED
                if not errors
                else PaperSimulationRunStatus.PARTIAL,
                "orders_created": len(orders),
                "fills_created": fills_count,
                "rejected_orders": sum(
                    1 for order in orders if order.status == PaperOrderStatus.REJECTED
                ),
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_paper_simulation_run(completed)
        fills = repo.list_paper_fills(simulation_run_id=run.simulation_run_id, limit=10000)
        return PaperSimulationRunResult(
            run=completed,
            orders=orders,
            fills=fills,
            summary=summary,
        )
    except Exception:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": PaperSimulationRunStatus.FAILED,
                "errors_count": max(1, len(errors)),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_paper_simulation_run(failed)
        raise


def _policy(
    repo: PredictionMarketRepository,
    paper_policy_id: str | None,
) -> PaperExecutionPolicy:
    if paper_policy_id is not None:
        policy = repo.get_paper_execution_policy(paper_policy_id)
        if policy is None:
            raise PaperRunError("paper_policy_not_found")
        return policy
    existing = repo.get_active_paper_execution_policy()
    if existing is not None:
        return existing
    return repo.save_paper_execution_policy(build_default_paper_execution_policy())


def _planned_intents(
    config: PaperSimulationRunConfig,
    repo: PredictionMarketRepository,
) -> list[TradeIntent]:
    if config.trade_plan:
        return [
            compute_trade_intent_from_request(
                PaperSimulateIntentRequest(**item),
                PaperSimulateIntentRequest(**item).asof_timestamp or config.start_time,
            )
            for item in config.trade_plan
        ]
    timestamps = generate_paper_timestamps(
        config.start_time,
        config.end_time,
        config.interval_seconds,
    )
    markets = repo.list_markets_for_replay(
        market_ids=config.market_ids,
        start_time=config.start_time,
        end_time=config.end_time,
    )
    intents = []
    for asof_timestamp in timestamps:
        for market in markets:
            request = PaperSimulateIntentRequest(
                market_id=market.market_id,
                venue_id=market.venue_id,
                strategy_context=config.default_strategy_context,
                side=TradeSide.BUY,
                intent_type=config.default_intent_type,
                requested_size_units=config.default_order_size_units,
                asof_timestamp=asof_timestamp,
                metadata={"source": "paper_runner_default_plan_v1"},
            )
            intents.append(compute_trade_intent_from_request(request, asof_timestamp))
    return intents


def _rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)
