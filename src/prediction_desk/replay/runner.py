"""Point-in-time replay runner."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.divergence.enums import DivergenceStatus
from prediction_desk.divergence.models import CrossVenueDivergenceAssessment
from prediction_desk.domain.enums import VerdictAction
from prediction_desk.domain.models import Market, MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.equivalence.enums import ComparisonPermission
from prediction_desk.equivalence.models import MarketEquivalenceAssessment
from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.marketdata.models import (
    MarketDataQualityReport,
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
)
from prediction_desk.paper.models import PaperPortfolioSnapshot, PaperPositionSnapshot
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.enums import ReplayRunStatus
from prediction_desk.replay.evaluation import summarize_replay_steps
from prediction_desk.replay.models import (
    ReplayDecision,
    ReplayRun,
    ReplayRunConfig,
    ReplayRunResult,
    ReplayStep,
)
from prediction_desk.replay.policies import ReplayPolicy, get_policy
from prediction_desk.research.models import (
    ResearchDecisionTrace,
    ResearchIntentProposal,
    ResearchSignal,
)
from prediction_desk.resolution.models import ResolutionAnalysis
from prediction_desk.resolution.service import ResolutionCorpusError, ResolutionCorpusService
from prediction_desk.scoring.trust_verdict import build_trust_verdict

RUNNER_VERSION = "replay_runner_v1"


class ReplayError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_replay(
    config: ReplayRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> ReplayRunResult:
    if repo is not None:
        return _run_replay(config, repo)
    with session_scope(database_url) as session:
        return _run_replay(config, PredictionMarketRepository(session))


def compute_input_hash(payload: dict[str, Any]) -> str:
    return _hash_payload(payload)


def compute_output_hash(payload: dict[str, Any]) -> str:
    normalized = dict(payload)
    if "reason_codes" in normalized:
        normalized["reason_codes"] = sorted(normalized["reason_codes"])
    return _hash_payload(normalized)


def generate_replay_timestamps(
    start_time: datetime, end_time: datetime, interval_seconds: int
) -> list[datetime]:
    timestamps: list[datetime] = []
    current = start_time
    interval = timedelta(seconds=interval_seconds)
    while current <= end_time:
        timestamps.append(current)
        current += interval
    return timestamps


def _run_replay(config: ReplayRunConfig, repo: PredictionMarketRepository) -> ReplayRunResult:
    policy = _policy(config.policy_name)
    timestamps = generate_replay_timestamps(
        config.start_time,
        config.end_time,
        config.interval_seconds,
    )
    markets = repo.list_markets_for_replay(
        market_ids=config.market_ids,
        start_time=config.start_time,
        end_time=config.end_time,
    )
    total_requested_steps = len(timestamps) * len(markets)
    if total_requested_steps > config.max_steps:
        raise ReplayError(
            "too_many_steps",
            f"Replay would create {total_requested_steps} steps; max_steps={config.max_steps}.",
        )

    now = datetime.now(tz=UTC)
    run = ReplayRun(
        run_id=f"replay_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=ReplayRunStatus.RUNNING,
        policy_name=policy.policy_name,
        policy_version=policy.policy_version,
        start_time=config.start_time,
        end_time=config.end_time,
        interval_seconds=config.interval_seconds,
        market_ids=[market.market_id for market in markets],
        max_steps=config.max_steps,
        config={
            **config.model_dump(mode="json"),
            "runner_version": RUNNER_VERSION,
            "timestamp_window": "inclusive_start_inclusive_end",
        },
        metadata=dict(config.metadata),
    )
    repo.save_replay_run(run)

    steps: list[ReplayStep] = []
    try:
        for asof_timestamp in timestamps:
            for market in markets:
                step = _run_step(
                    repo=repo,
                    policy=policy,
                    run=run,
                    market=market,
                    asof_timestamp=asof_timestamp,
                    force_recompute_verdicts=config.force_recompute_verdicts,
                )
                steps.append(step)
                if config.persist_steps:
                    repo.save_replay_step(step)

        summary = summarize_replay_steps(run.run_id, steps)
        repo.save_replay_summary(summary)
        completed_at = datetime.now(tz=UTC)
        completed = repo.update_replay_run_status(
            run.run_id,
            ReplayRunStatus.COMPLETED,
            completed_at=completed_at,
        )
        if completed is not None:
            run = completed
        return ReplayRunResult(run=run, steps=steps, summary=summary)
    except Exception:
        repo.update_replay_run_status(
            run.run_id,
            ReplayRunStatus.FAILED,
            completed_at=datetime.now(tz=UTC),
        )
        raise


def _run_step(
    *,
    repo: PredictionMarketRepository,
    policy: ReplayPolicy,
    run: ReplayRun,
    market: Market,
    asof_timestamp: datetime,
    force_recompute_verdicts: bool,
) -> ReplayStep:
    try:
        rule_snapshot = repo.get_latest_rule_snapshot_asof(market.market_id, asof_timestamp)
        orderbook_snapshot = repo.get_latest_orderbook_snapshot_asof(
            market.market_id,
            asof_timestamp,
        )
        resolution_analysis = _resolution_analysis_asof(
            repo,
            market,
            rule_snapshot,
            asof_timestamp,
        )
        price_snapshot = repo.get_latest_price_snapshot_asof(market.market_id, asof_timestamp)
        liquidity_snapshot = repo.get_latest_liquidity_snapshot_asof(
            market.market_id,
            asof_timestamp,
        )
        quality_report = repo.get_latest_quality_report_asof(market.market_id, asof_timestamp)
        integrity_assessment = repo.get_latest_integrity_assessment_asof(
            market.market_id,
            asof_timestamp,
        )
        equivalence_assessments = repo.list_latest_equivalence_assessments_for_market_asof(
            market.market_id,
            asof_timestamp,
        )
        divergence_assessments = repo.list_latest_divergence_assessments_for_market_asof(
            market.market_id,
            asof_timestamp,
        )
        paper_position = repo.get_latest_paper_position_asof(
            market.market_id,
            asof_timestamp=asof_timestamp,
        )
        paper_portfolio = repo.get_latest_paper_portfolio_asof(
            asof_timestamp=asof_timestamp,
        )
        research_signals = repo.list_research_signals(
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            limit=500,
        )
        research_proposals = repo.list_research_intent_proposals(
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            limit=500,
        )
        research_traces = repo.list_research_decision_traces(
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            limit=500,
        )
        trust_verdict = _trust_verdict_asof(
            repo=repo,
            market=market,
            rule_snapshot=rule_snapshot,
            orderbook_snapshot=orderbook_snapshot,
            resolution_analysis=resolution_analysis,
            integrity_assessment=integrity_assessment,
            equivalence_assessments=equivalence_assessments,
            divergence_assessments=divergence_assessments,
            asof_timestamp=asof_timestamp,
            force_recompute=force_recompute_verdicts,
        )
        decision = policy.decide(
            market=market,
            rule_snapshot=rule_snapshot,
            orderbook_snapshot=orderbook_snapshot,
            resolution_analysis=resolution_analysis,
            integrity_assessment=integrity_assessment,
            trust_verdict=trust_verdict,
            asof_timestamp=asof_timestamp,
            repo=repo,
        )
        return _step_from_decision(
            run=run,
            market=market,
            asof_timestamp=asof_timestamp,
            policy=policy,
            rule_snapshot=rule_snapshot,
            orderbook_snapshot=orderbook_snapshot,
            resolution_analysis=resolution_analysis,
            price_snapshot=price_snapshot,
            liquidity_snapshot=liquidity_snapshot,
            quality_report=quality_report,
            integrity_assessment=integrity_assessment,
            equivalence_assessments=equivalence_assessments,
            divergence_assessments=divergence_assessments,
            paper_position=paper_position,
            paper_portfolio=paper_portfolio,
            research_signals=research_signals,
            research_proposals=research_proposals,
            research_traces=research_traces,
            trust_verdict=trust_verdict,
            decision=decision,
            error_code=None,
            error_message=None,
        )
    except Exception as exc:
        return _error_step(run, market, asof_timestamp, policy, exc)


def _resolution_analysis_asof(
    repo: PredictionMarketRepository,
    market: Market,
    rule_snapshot: MarketRuleSnapshot | None,
    asof_timestamp: datetime,
) -> ResolutionAnalysis | None:
    if rule_snapshot is None:
        return None
    existing = repo.get_latest_resolution_analysis_asof(market.market_id, asof_timestamp)
    if (
        existing is not None
        and existing.rule_snapshot.rule_snapshot_id == rule_snapshot.rule_snapshot_id
    ):
        return existing
    try:
        return ResolutionCorpusService(repo).analyze_rule_snapshot(
            market.market_id,
            rule_snapshot.rule_snapshot_id,
        )
    except ResolutionCorpusError:
        return None


def _trust_verdict_asof(
    *,
    repo: PredictionMarketRepository,
    market: Market,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    resolution_analysis: ResolutionAnalysis | None,
    integrity_assessment: IntegrityAssessment | None,
    equivalence_assessments: list[MarketEquivalenceAssessment],
    divergence_assessments: list[CrossVenueDivergenceAssessment],
    asof_timestamp: datetime,
    force_recompute: bool,
) -> TrustVerdict:
    ambiguity_assessment = (
        resolution_analysis.ambiguity_assessment if resolution_analysis is not None else None
    )
    existing = repo.get_latest_trust_verdict_asof(market.market_id, asof_timestamp)
    if (
        existing is not None
        and not force_recompute
        and _verdict_matches_inputs(
            existing,
            asof_timestamp,
            rule_snapshot,
            orderbook_snapshot,
            ambiguity_assessment,
            integrity_assessment,
            equivalence_assessments,
            divergence_assessments,
        )
    ):
        return existing
    verdict = build_trust_verdict(
        market=market,
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=orderbook_snapshot,
        asof_timestamp=asof_timestamp,
        ambiguity_assessment=ambiguity_assessment,
        integrity_assessment=integrity_assessment,
        equivalence_assessments=equivalence_assessments,
        divergence_assessments=divergence_assessments,
    )
    return repo.save_trust_verdict(verdict)


def _verdict_matches_inputs(
    verdict: TrustVerdict,
    asof_timestamp: datetime,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    ambiguity_assessment: object | None,
    integrity_assessment: IntegrityAssessment | None,
    equivalence_assessments: list[MarketEquivalenceAssessment],
    divergence_assessments: list[CrossVenueDivergenceAssessment],
) -> bool:
    data_versions = verdict.data_versions
    return (
        verdict.asof_timestamp == asof_timestamp
        and data_versions.get("rule_snapshot_id")
        == (rule_snapshot.rule_snapshot_id if rule_snapshot else None)
        and data_versions.get("orderbook_snapshot_id")
        == (orderbook_snapshot.snapshot_id if orderbook_snapshot else None)
        and data_versions.get("ambiguity_assessment_id")
        == (getattr(ambiguity_assessment, "assessment_id", None))
        and data_versions.get("integrity_assessment_id")
        == (
            integrity_assessment.integrity_assessment_id
            if integrity_assessment is not None
            else None
        )
        and data_versions.get("equivalence_assessment_ids")
        == sorted(
            assessment.equivalence_assessment_id for assessment in equivalence_assessments
        )
        and data_versions.get("divergence_assessment_ids")
        == sorted(
            assessment.divergence_assessment_id for assessment in divergence_assessments
        )
    )


def _step_from_decision(
    *,
    run: ReplayRun,
    market: Market,
    asof_timestamp: datetime,
    policy: ReplayPolicy,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    resolution_analysis: ResolutionAnalysis | None,
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
    quality_report: MarketDataQualityReport | None,
    integrity_assessment: IntegrityAssessment | None,
    equivalence_assessments: list[MarketEquivalenceAssessment],
    divergence_assessments: list[CrossVenueDivergenceAssessment],
    paper_position: PaperPositionSnapshot | None,
    paper_portfolio: PaperPortfolioSnapshot | None,
    research_signals: list[ResearchSignal],
    research_proposals: list[ResearchIntentProposal],
    research_traces: list[ResearchDecisionTrace],
    trust_verdict: TrustVerdict | None,
    decision: ReplayDecision,
    error_code: str | None,
    error_message: str | None,
) -> ReplayStep:
    scores = decision.scores
    input_payload = _input_payload(
        market=market,
        asof_timestamp=asof_timestamp,
        policy=policy,
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=orderbook_snapshot,
        resolution_analysis=resolution_analysis,
        price_snapshot=price_snapshot,
        liquidity_snapshot=liquidity_snapshot,
        quality_report=quality_report,
        integrity_assessment=integrity_assessment,
        equivalence_assessments=equivalence_assessments,
        divergence_assessments=divergence_assessments,
        paper_position=paper_position,
        paper_portfolio=paper_portfolio,
        research_signals=research_signals,
        research_proposals=research_proposals,
        research_traces=research_traces,
        trust_verdict=trust_verdict,
    )
    output_payload = {
        "action": decision.action,
        "allowed_size_multiplier": str(decision.allowed_size_multiplier),
        "reason_codes": list(decision.reason_codes),
        "scores": scores,
        "metadata": decision.metadata,
        "trust_verdict_id": decision.trust_verdict_id
        or (trust_verdict.verdict_id if trust_verdict else None),
    }
    return ReplayStep(
        step_id=_step_id(run.run_id, market.market_id, asof_timestamp),
        run_id=run.run_id,
        market_id=market.market_id,
        asof_timestamp=asof_timestamp,
        market_status=market.status.value,
        rule_snapshot_id=rule_snapshot.rule_snapshot_id if rule_snapshot else None,
        rule_snapshot_hash=rule_snapshot.rule_hash if rule_snapshot else None,
        orderbook_snapshot_id=orderbook_snapshot.snapshot_id if orderbook_snapshot else None,
        resolution_predicate_id=(
            resolution_analysis.predicate.predicate_id if resolution_analysis else None
        ),
        ambiguity_assessment_id=(
            resolution_analysis.ambiguity_assessment.assessment_id
            if resolution_analysis
            else None
        ),
        trust_verdict_id=decision.trust_verdict_id
        or (trust_verdict.verdict_id if trust_verdict else None),
        action=decision.action,
        allowed_size_multiplier=decision.allowed_size_multiplier,
        price_integrity_score=scores.get("price_integrity_score"),
        resolution_risk_score=scores.get("resolution_risk_score"),
        liquidity_risk_score=scores.get("liquidity_risk_score"),
        cross_venue_consistency_score=scores.get("cross_venue_consistency_score"),
        information_freshness_score=scores.get("information_freshness_score"),
        manipulation_risk_score=scores.get("manipulation_risk_score"),
        reason_codes=list(decision.reason_codes),
        input_hash=compute_input_hash(input_payload),
        output_hash=compute_output_hash(output_payload),
        error_code=error_code,
        error_message=error_message,
        metadata={
            "runner_version": RUNNER_VERSION,
            "policy_name": policy.policy_name,
            "policy_version": policy.policy_version,
            "latest_price_snapshot_id": (
                price_snapshot.price_snapshot_id if price_snapshot else None
            ),
            "latest_liquidity_snapshot_id": (
                liquidity_snapshot.liquidity_snapshot_id if liquidity_snapshot else None
            ),
            "latest_quality_report_id": (
                quality_report.quality_report_id if quality_report else None
            ),
            "market_data_quality_score": (
                quality_report.quality_score if quality_report else None
            ),
            "market_data_quality_reason_codes": (
                list(quality_report.reason_codes) if quality_report else []
            ),
            "latest_integrity_assessment_id": (
                integrity_assessment.integrity_assessment_id
                if integrity_assessment
                else None
            ),
            "integrity_overall_risk_score": (
                integrity_assessment.overall_risk_score if integrity_assessment else None
            ),
            "integrity_action_hint": (
                integrity_assessment.action_hint.value if integrity_assessment else None
            ),
            "integrity_reason_codes": (
                list(integrity_assessment.reason_codes) if integrity_assessment else []
            ),
            **_equivalence_metadata(market.market_id, equivalence_assessments),
            **_divergence_metadata(divergence_assessments),
            **_paper_metadata(paper_position, paper_portfolio),
            **_research_metadata(research_signals, research_proposals, research_traces),
            **decision.metadata,
        },
    )


def _error_step(
    run: ReplayRun,
    market: Market,
    asof_timestamp: datetime,
    policy: ReplayPolicy,
    exc: Exception,
) -> ReplayStep:
    decision = ReplayDecision(
        action=VerdictAction.NO_TRADE.value,
        allowed_size_multiplier=Decimal("0.0"),
        reason_codes=["REPLAY_STEP_ERROR"],
        scores={
            "price_integrity_score": None,
            "resolution_risk_score": None,
            "liquidity_risk_score": None,
            "cross_venue_consistency_score": None,
            "information_freshness_score": None,
            "manipulation_risk_score": None,
        },
    )
    return _step_from_decision(
        run=run,
        market=market,
        asof_timestamp=asof_timestamp,
        policy=policy,
        rule_snapshot=None,
        orderbook_snapshot=None,
        resolution_analysis=None,
        price_snapshot=None,
        liquidity_snapshot=None,
        quality_report=None,
        integrity_assessment=None,
        equivalence_assessments=[],
        divergence_assessments=[],
        paper_position=None,
        paper_portfolio=None,
        research_signals=[],
        research_proposals=[],
        research_traces=[],
        trust_verdict=None,
        decision=decision,
        error_code=exc.__class__.__name__,
        error_message=str(exc),
    )


def _input_payload(
    *,
    market: Market,
    asof_timestamp: datetime,
    policy: ReplayPolicy,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    resolution_analysis: ResolutionAnalysis | None,
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
    quality_report: MarketDataQualityReport | None,
    integrity_assessment: IntegrityAssessment | None,
    equivalence_assessments: list[MarketEquivalenceAssessment],
    divergence_assessments: list[CrossVenueDivergenceAssessment],
    paper_position: PaperPositionSnapshot | None,
    paper_portfolio: PaperPortfolioSnapshot | None,
    research_signals: list[ResearchSignal],
    research_proposals: list[ResearchIntentProposal],
    research_traces: list[ResearchDecisionTrace],
    trust_verdict: TrustVerdict | None,
) -> dict[str, Any]:
    return {
        "market_id": market.market_id,
        "asof_timestamp": asof_timestamp.isoformat(),
        "rule_snapshot_id": rule_snapshot.rule_snapshot_id if rule_snapshot else None,
        "rule_snapshot_hash": rule_snapshot.rule_hash if rule_snapshot else None,
        "orderbook_snapshot_id": orderbook_snapshot.snapshot_id if orderbook_snapshot else None,
        "latest_price_snapshot_id": price_snapshot.price_snapshot_id if price_snapshot else None,
        "latest_liquidity_snapshot_id": (
            liquidity_snapshot.liquidity_snapshot_id if liquidity_snapshot else None
        ),
        "latest_quality_report_id": quality_report.quality_report_id if quality_report else None,
        "market_data_quality_score": quality_report.quality_score if quality_report else None,
        "market_data_quality_reason_codes": (
            sorted(quality_report.reason_codes) if quality_report else []
        ),
        "latest_integrity_assessment_id": (
            integrity_assessment.integrity_assessment_id if integrity_assessment else None
        ),
        "integrity_overall_risk_score": (
            integrity_assessment.overall_risk_score if integrity_assessment else None
        ),
        "integrity_action_hint": (
            integrity_assessment.action_hint.value if integrity_assessment else None
        ),
        "integrity_reason_codes": (
            sorted(integrity_assessment.reason_codes) if integrity_assessment else []
        ),
        **_equivalence_metadata(market.market_id, equivalence_assessments),
        **_divergence_metadata(divergence_assessments),
        **_paper_metadata(paper_position, paper_portfolio),
        **_research_metadata(research_signals, research_proposals, research_traces),
        "ambiguity_assessment_id": (
            resolution_analysis.ambiguity_assessment.assessment_id
            if resolution_analysis
            else None
        ),
        "resolution_predicate_id": (
            resolution_analysis.predicate.predicate_id if resolution_analysis else None
        ),
        "policy_name": policy.policy_name,
        "policy_version": policy.policy_version,
        "runner_version": RUNNER_VERSION,
        "model_versions": trust_verdict.model_versions if trust_verdict else {},
    }


def _paper_metadata(
    paper_position: PaperPositionSnapshot | None,
    paper_portfolio: PaperPortfolioSnapshot | None,
) -> dict[str, Any]:
    return {
        "latest_paper_position_snapshot_id": (
            paper_position.position_snapshot_id if paper_position else None
        ),
        "paper_position_units": (
            str(paper_position.position_units) if paper_position else None
        ),
        "paper_unrealized_pnl_simulated": (
            str(paper_position.unrealized_pnl_simulated) if paper_position else None
        ),
        "latest_paper_portfolio_snapshot_id": (
            paper_portfolio.portfolio_snapshot_id if paper_portfolio else None
        ),
        "paper_total_equity_simulated": (
            str(paper_portfolio.total_equity_simulated) if paper_portfolio else None
        ),
    }


def _research_metadata(
    signals: list[ResearchSignal],
    proposals: list[ResearchIntentProposal],
    traces: list[ResearchDecisionTrace],
) -> dict[str, Any]:
    pretrade_action_counts: dict[str, int] = {}
    for trace in traces:
        if trace.pretrade_action is not None:
            pretrade_action_counts[trace.pretrade_action] = (
                pretrade_action_counts.get(trace.pretrade_action, 0) + 1
            )
    return {
        "latest_research_signal_ids": sorted(
            signal.research_signal_id for signal in signals
        ),
        "latest_research_proposal_ids": sorted(
            proposal.proposal_id for proposal in proposals
        ),
        "latest_research_trace_ids": sorted(trace.trace_id for trace in traces),
        "research_signal_count": len(signals),
        "research_proposal_count": len(proposals),
        "research_pretrade_action_counts": dict(sorted(pretrade_action_counts.items())),
    }


def _equivalence_metadata(
    market_id: str,
    assessments: list[MarketEquivalenceAssessment],
) -> dict[str, Any]:
    comparable_permissions = {
        ComparisonPermission.COMPARABLE,
        ComparisonPermission.COMPARABLE_WITH_HAIRCUT,
    }
    comparable: set[str] = set()
    manual_review: set[str] = set()
    do_not_compare: set[str] = set()
    assessment_ids: list[str] = []
    for assessment in assessments:
        assessment_ids.append(assessment.equivalence_assessment_id)
        other_market_id = (
            assessment.right_market_id
            if assessment.left_market_id == market_id
            else assessment.left_market_id
        )
        if assessment.comparison_permission in comparable_permissions:
            comparable.add(other_market_id)
        elif assessment.comparison_permission == ComparisonPermission.MANUAL_REVIEW:
            manual_review.add(other_market_id)
        elif assessment.comparison_permission == ComparisonPermission.DO_NOT_COMPARE:
            do_not_compare.add(other_market_id)
    return {
        "latest_equivalence_assessment_ids": sorted(assessment_ids),
        "count_comparable_markets": len(comparable),
        "count_manual_review_equivalence": len(manual_review),
        "count_do_not_compare_equivalence": len(do_not_compare),
    }


def _divergence_metadata(
    assessments: list[CrossVenueDivergenceAssessment],
) -> dict[str, Any]:
    status_counts = {status.value: 0 for status in DivergenceStatus}
    max_score: int | None = None
    assessment_ids: list[str] = []
    for assessment in assessments:
        assessment_ids.append(assessment.divergence_assessment_id)
        status_counts[assessment.status.value] = status_counts.get(
            assessment.status.value,
            0,
        ) + 1
        max_score = (
            assessment.overall_divergence_score
            if max_score is None
            else max(max_score, assessment.overall_divergence_score)
        )
    return {
        "latest_divergence_assessment_ids": sorted(assessment_ids),
        "divergence_watch_count": status_counts[DivergenceStatus.WATCH.value],
        "material_divergence_count": status_counts[
            DivergenceStatus.MATERIAL_DIVERGENCE.value
        ],
        "divergence_needs_review_count": status_counts[
            DivergenceStatus.NEEDS_REVIEW.value
        ],
        "divergence_do_not_compare_count": status_counts[
            DivergenceStatus.DO_NOT_COMPARE.value
        ],
        "max_divergence_score": max_score,
    }


def _policy(policy_name: str) -> ReplayPolicy:
    try:
        return get_policy(policy_name)
    except ValueError as exc:
        raise ReplayError("unknown_policy", str(exc)) from exc


def _step_id(run_id: str, market_id: str, asof_timestamp: datetime) -> str:
    digest = _hash_payload(
        {
            "run_id": run_id,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp.isoformat(),
            "step_version": "replay_step_v1",
        }
    )
    return f"replay_step_{digest[:24]}"


def _hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode()
    ).hexdigest()
