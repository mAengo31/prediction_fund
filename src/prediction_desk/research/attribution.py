"""Research run summary and simulated attribution helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.research.models import (
    ResearchAttributionReport,
    ResearchDecisionTrace,
    ResearchRunSummary,
)


def build_research_run_summary(
    research_run_id: str,
    repo: PredictionMarketRepository | None = None,
) -> ResearchRunSummary:
    if repo is not None:
        return _build_research_run_summary(research_run_id, repo)
    with session_scope() as session:
        return _build_research_run_summary(
            research_run_id,
            PredictionMarketRepository(session),
        )


def build_research_attribution_report(
    research_run_id: str,
    repo: PredictionMarketRepository | None = None,
) -> ResearchAttributionReport:
    if repo is not None:
        return _build_research_attribution_report(research_run_id, repo)
    with session_scope() as session:
        return _build_research_attribution_report(
            research_run_id,
            PredictionMarketRepository(session),
        )


def _build_research_run_summary(
    research_run_id: str,
    repo: PredictionMarketRepository,
) -> ResearchRunSummary:
    traces = repo.list_research_decision_traces(research_run_id=research_run_id, limit=10000)
    signals = _signals_for_traces(repo, traces)
    proposals = _proposals_for_traces(repo, traces)
    strategy_counts = Counter(trace.strategy_id for trace in traces)
    signal_type_counts = Counter(signal.signal_type.value for signal in signals.values())
    pretrade_action_counts = Counter(
        trace.pretrade_action for trace in traces if trace.pretrade_action
    )
    paper_status_counts = Counter(
        trace.paper_order_status for trace in traces if trace.paper_order_status
    )
    reason_counts: Counter[str] = Counter()
    for trace in traces:
        reason_counts.update(trace.reason_codes)
    requested_size = sum(
        (proposal.requested_size_units for proposal in proposals.values()),
        Decimal("0"),
    )
    allowed_size = sum(
        (
            _decimal_metadata_or_zero(trace, "pretrade_final_allowed_size_units")
            for trace in traces
        ),
        Decimal("0"),
    )
    filled_size = sum(
        (trace.filled_size_units_simulated for trace in traces),
        Decimal("0"),
    )
    signal_strengths = [
        Decimal(signal.signal_strength_score) for signal in signals.values()
    ]
    confidence_scores = [Decimal(signal.confidence_score) for signal in signals.values()]
    latest_portfolio = _latest_trace_portfolio(traces)
    total_proposals = len(proposals)
    passed = sum(
        1
        for trace in traces
        if trace.pretrade_action in {"ALLOW", "ALLOW_SMALLER_SIZE", "PASSIVE_ONLY"}
    )
    filled_traces = sum(1 for trace in traces if trace.filled_size_units_simulated > 0)
    return ResearchRunSummary(
        summary_id=f"research_summary_{uuid4().hex[:24]}",
        research_run_id=research_run_id,
        created_at=datetime.now(tz=UTC),
        total_steps=len(traces),
        total_signals=len(signals),
        total_proposals=total_proposals,
        total_pretrade_checks=sum(1 for trace in traces if trace.pretrade_decision_id),
        total_paper_orders=sum(1 for trace in traces if trace.paper_order_id),
        total_paper_fills=sum(len(trace.paper_fill_ids) for trace in traces),
        strategy_counts=dict(strategy_counts),
        signal_type_counts=dict(signal_type_counts),
        pretrade_action_counts=dict(pretrade_action_counts),
        paper_order_status_counts=dict(paper_status_counts),
        reason_code_counts=dict(reason_counts),
        average_scores={
            "signal_strength_score": _avg(signal_strengths),
            "confidence_score": _avg(confidence_scores),
        },
        total_requested_size_units=requested_size,
        total_pretrade_allowed_size_units=allowed_size,
        total_filled_size_units_simulated=filled_size,
        final_portfolio_equity_simulated=latest_portfolio.get("equity"),
        final_realized_pnl_simulated=latest_portfolio.get("realized_pnl"),
        final_unrealized_pnl_simulated=latest_portfolio.get("unrealized_pnl"),
        proposal_to_pretrade_pass_rate=_rate(passed, total_proposals),
        paper_fill_rate=_rate(filled_traces, total_proposals),
        metadata={"summary_version": "research_run_summary_v1"},
    )


def _build_research_attribution_report(
    research_run_id: str,
    repo: PredictionMarketRepository,
) -> ResearchAttributionReport:
    traces = repo.list_research_decision_traces(research_run_id=research_run_id, limit=10000)
    signals = _signals_for_traces(repo, traces)
    by_strategy: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_market: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_reason: Counter[str] = Counter()
    by_pretrade: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_signal_type: Counter[str] = Counter()
    simulated_by_strategy: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    simulated_by_market: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for trace in traces:
        _add_trace(by_strategy[trace.strategy_id], trace)
        _add_trace(by_market[trace.market_id], trace)
        by_reason.update(trace.reason_codes)
        if trace.pretrade_action:
            by_pretrade[trace.pretrade_action] += 1
        if trace.paper_order_status:
            by_status[trace.paper_order_status] += 1
        if trace.research_signal_id and trace.research_signal_id in signals:
            by_signal_type[signals[trace.research_signal_id].signal_type.value] += 1
        simulated_value = _decimal_metadata_or_zero(
            trace,
            "paper_unrealized_pnl_simulated",
        )
        simulated_by_strategy[trace.strategy_id] += simulated_value
        simulated_by_market[trace.market_id] += simulated_value
    return ResearchAttributionReport(
        attribution_report_id=f"research_attr_{uuid4().hex[:24]}",
        research_run_id=research_run_id,
        created_at=datetime.now(tz=UTC),
        by_strategy=dict(by_strategy),
        by_market=dict(by_market),
        by_venue={},
        by_reason_code=dict(by_reason),
        by_signal_type=dict(by_signal_type),
        by_pretrade_action=dict(by_pretrade),
        by_paper_order_status=dict(by_status),
        simulated_pnl_by_strategy={
            key: str(value) for key, value in simulated_by_strategy.items()
        },
        simulated_pnl_by_market={
            key: str(value) for key, value in simulated_by_market.items()
        },
        metadata={"attribution_version": "research_attribution_v1"},
    )


def _signals_for_traces(
    repo: PredictionMarketRepository,
    traces: list[ResearchDecisionTrace],
) -> dict[str, Any]:
    signal_ids = {trace.research_signal_id for trace in traces if trace.research_signal_id}
    if not signal_ids:
        return {}
    return {
        signal.research_signal_id: signal
        for signal in repo.list_research_signals(limit=10000)
        if signal.research_signal_id in signal_ids
    }


def _proposals_for_traces(
    repo: PredictionMarketRepository,
    traces: list[ResearchDecisionTrace],
) -> dict[str, Any]:
    proposal_ids = {trace.proposal_id for trace in traces if trace.proposal_id}
    if not proposal_ids:
        return {}
    return {
        proposal.proposal_id: proposal
        for proposal in repo.list_research_intent_proposals(limit=10000)
        if proposal.proposal_id in proposal_ids
    }


def _bucket() -> dict[str, Any]:
    return {
        "traces": 0,
        "paper_fills": 0,
        "filled_size_units_simulated": "0",
    }


def _add_trace(bucket: dict[str, Any], trace: ResearchDecisionTrace) -> None:
    bucket["traces"] += 1
    bucket["paper_fills"] += len(trace.paper_fill_ids)
    bucket["filled_size_units_simulated"] = str(
        Decimal(str(bucket["filled_size_units_simulated"]))
        + trace.filled_size_units_simulated
    )


def _latest_trace_portfolio(
    traces: list[ResearchDecisionTrace],
) -> dict[str, Decimal | None]:
    latest = None
    for trace in traces:
        if trace.paper_portfolio_snapshot_id is not None:
            latest = trace
    if latest is None:
        return {"equity": None, "realized_pnl": None, "unrealized_pnl": None}
    return {
        "equity": _decimal_metadata(latest, "paper_total_equity_simulated"),
        "realized_pnl": _decimal_metadata(latest, "paper_realized_pnl_simulated"),
        "unrealized_pnl": _decimal_metadata(latest, "paper_unrealized_pnl_simulated"),
    }


def _decimal_metadata(trace: ResearchDecisionTrace, key: str) -> Decimal | None:
    value = trace.metadata.get(key)
    return Decimal(str(value)) if value not in {None, "None", ""} else None


def _decimal_metadata_or_zero(trace: ResearchDecisionTrace, key: str) -> Decimal:
    return _decimal_metadata(trace, key) or Decimal("0")


def _avg(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    return sum(values, Decimal("0")) / Decimal(len(values))


def _rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)
