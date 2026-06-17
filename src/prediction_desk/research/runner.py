"""Run-once strategy research simulation runner."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.research.attribution import (
    build_research_attribution_report,
    build_research_run_summary,
)
from prediction_desk.research.models import (
    RESEARCH_RUNNER_VERSION,
    ResearchDecisionTrace,
    ResearchIntentProposal,
    ResearchRun,
    ResearchRunConfig,
    ResearchRunResult,
    ResearchRunStatus,
    ResearchSignal,
)
from prediction_desk.research.service import ResearchService, ResearchServiceError


class ResearchRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_research_simulation(
    config: ResearchRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> ResearchRunResult:
    if repo is not None:
        return _run_research_simulation(config, repo)
    with session_scope(database_url) as session:
        return _run_research_simulation(config, PredictionMarketRepository(session))


def generate_research_timestamps(
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


def _run_research_simulation(
    config: ResearchRunConfig,
    repo: PredictionMarketRepository,
) -> ResearchRunResult:
    service = ResearchService(repo)
    definitions = _resolve_definitions(service, config.strategy_ids)
    timestamps = generate_research_timestamps(
        config.start_time,
        config.end_time,
        config.interval_seconds,
    )
    markets = repo.list_markets_for_replay(
        market_ids=config.market_ids,
        start_time=config.start_time,
        end_time=config.end_time,
    )
    total_steps = len(timestamps) * len(markets) * len(definitions)
    if total_steps > config.max_steps:
        raise ResearchRunError(
            "too_many_research_steps",
            f"Research run would create {total_steps} steps; max_steps={config.max_steps}.",
        )
    now = datetime.now(tz=UTC)
    run = ResearchRun(
        research_run_id=f"research_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=ResearchRunStatus.RUNNING,
        start_time=config.start_time,
        end_time=config.end_time,
        interval_seconds=config.interval_seconds,
        strategy_ids=[definition.strategy_id for definition in definitions],
        market_ids=[market.market_id for market in markets],
        max_steps=config.max_steps,
        max_proposals=config.max_proposals,
        enable_paper_simulation=config.enable_paper_simulation,
        paper_policy_id=config.paper_policy_id,
        initial_cash_simulated=config.initial_cash_simulated,
        config={
            **config.model_dump(mode="json"),
            "runner_version": RESEARCH_RUNNER_VERSION,
            "timestamp_window": "inclusive_start_inclusive_end",
        },
        metadata=dict(config.metadata),
    )
    repo.save_research_run(run)
    signals: list[ResearchSignal] = []
    proposals: list[ResearchIntentProposal] = []
    traces: list[ResearchDecisionTrace] = []
    errors: list[dict[str, Any]] = []
    try:
        for asof_timestamp in timestamps:
            for market in markets:
                for definition in definitions:
                    try:
                        step_signals = service.generate_research_signals(
                            market.market_id,
                            asof_timestamp,
                            strategy_ids=[definition.strategy_id],
                            force=config.force,
                        )
                        step_proposals = service.generate_research_proposals(
                            market.market_id,
                            asof_timestamp,
                            strategy_ids=[definition.strategy_id],
                            force=config.force,
                        )
                        if len(proposals) + len(step_proposals) > config.max_proposals:
                            raise ResearchRunError("too_many_research_proposals")
                        signals.extend(step_signals)
                        proposals.extend(step_proposals)
                        for proposal in step_proposals:
                            trace = service.evaluate_research_proposal(
                                proposal.proposal_id,
                                enable_paper_simulation=config.enable_paper_simulation,
                                paper_policy_id=config.paper_policy_id,
                                research_run_id=run.research_run_id,
                                initial_cash_simulated=(
                                    config.initial_cash_simulated or Decimal("0")
                                ),
                            )
                            traces.append(trace)
                    except (ResearchServiceError, ResearchRunError) as exc:
                        errors.append(
                            {
                                "market_id": market.market_id,
                                "strategy_id": definition.strategy_id,
                                "asof_timestamp": asof_timestamp.isoformat(),
                                "error_code": exc.code,
                                "error_message": exc.message,
                            }
                        )
        summary = build_research_run_summary(run.research_run_id, repo)
        repo.save_research_run_summary(summary)
        attribution = build_research_attribution_report(run.research_run_id, repo)
        repo.save_research_attribution_report(attribution)
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": ResearchRunStatus.COMPLETED
                if not errors
                else ResearchRunStatus.PARTIAL,
                "signals_created": len({signal.research_signal_id for signal in signals}),
                "proposals_created": len(
                    {proposal.proposal_id for proposal in proposals}
                ),
                "pretrade_checks_created": sum(
                    1 for trace in traces if trace.pretrade_decision_id
                ),
                "paper_orders_created": sum(1 for trace in traces if trace.paper_order_id),
                "paper_fills_created": sum(len(trace.paper_fill_ids) for trace in traces),
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_research_run(completed)
        return ResearchRunResult(
            run=completed,
            signals=signals,
            proposals=proposals,
            traces=traces,
            summary=summary,
            attribution=attribution,
        )
    except Exception:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": ResearchRunStatus.FAILED,
                "errors_count": max(1, len(errors)),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_research_run(failed)
        raise


def _resolve_definitions(
    service: ResearchService,
    strategy_ids: list[str] | None,
) -> list[Any]:
    service.create_default_research_strategies_if_missing()
    if strategy_ids is None:
        definitions = [
            definition
            for definition in service.list_research_strategies(limit=1000)
            if definition.is_active
        ]
        return definitions
    return [service.get_research_strategy(strategy_id) for strategy_id in strategy_ids]
