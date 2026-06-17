"""Deterministic replay admissibility policies."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.domain.models import Market, MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.integrity.enums import IntegrityActionHint
from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import StrategyContext, TradeIntentType
from prediction_desk.pretrade.gate import build_trade_intent_from_defaults
from prediction_desk.pretrade.service import PreTradeService, PreTradeServiceError
from prediction_desk.replay.models import ReplayDecision
from prediction_desk.resolution.models import ResolutionAnalysis

ACTION_MULTIPLIERS: dict[str, Decimal] = {
    VerdictAction.ALLOW.value: Decimal("1.0"),
    VerdictAction.ALLOW_SMALLER_SIZE.value: Decimal("0.5"),
    VerdictAction.PASSIVE_ONLY.value: Decimal("0.25"),
    VerdictAction.MANUAL_REVIEW.value: Decimal("0.0"),
    VerdictAction.NO_TRADE.value: Decimal("0.0"),
}


class ReplayPolicy(Protocol):
    policy_name: str
    policy_version: str

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        """Returns a deterministic replay decision."""


class AllowAllPolicy:
    policy_name = "allow_all_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del market, rule_snapshot, orderbook_snapshot, resolution_analysis
        del integrity_assessment, trust_verdict
        del asof_timestamp, repo
        return ReplayDecision(
            action=VerdictAction.ALLOW.value,
            allowed_size_multiplier=Decimal("1.0"),
            reason_codes=["BASELINE_ALLOW_ALL"],
            scores=_empty_scores(),
            metadata={"policy": self.policy_name},
        )


class TrustVerdictPolicy:
    policy_name = "trust_verdict_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del market, rule_snapshot, orderbook_snapshot, resolution_analysis
        del integrity_assessment, asof_timestamp, repo
        if trust_verdict is None:
            return ReplayDecision(
                action=VerdictAction.NO_TRADE.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["MISSING_TRUST_VERDICT"],
                scores=_empty_scores(),
                metadata={"policy": self.policy_name},
            )
        action = trust_verdict.action.value
        return ReplayDecision(
            action=action,
            allowed_size_multiplier=ACTION_MULTIPLIERS[action],
            reason_codes=list(trust_verdict.reason_codes),
            trust_verdict_id=trust_verdict.verdict_id,
            scores=_scores_from_verdict(trust_verdict),
            metadata={"policy": self.policy_name},
        )


class ResolutionRiskOnlyPolicy:
    policy_name = "resolution_risk_only_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del market, rule_snapshot, orderbook_snapshot, integrity_assessment, asof_timestamp
        del repo
        resolution_risk_score = _resolution_risk_score(resolution_analysis, trust_verdict)
        reason_codes = _resolution_reason_codes(resolution_analysis, trust_verdict)
        if resolution_risk_score >= 80:
            action = VerdictAction.NO_TRADE.value
        elif resolution_risk_score >= 50:
            action = VerdictAction.MANUAL_REVIEW.value
        else:
            action = VerdictAction.ALLOW.value
        return ReplayDecision(
            action=action,
            allowed_size_multiplier=ACTION_MULTIPLIERS[action],
            reason_codes=reason_codes,
            trust_verdict_id=trust_verdict.verdict_id if trust_verdict else None,
            scores={
                **_empty_scores(),
                "resolution_risk_score": resolution_risk_score,
            },
            metadata={"policy": self.policy_name},
        )


class IntegrityGatePolicy:
    policy_name = "integrity_gate_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del market, rule_snapshot, orderbook_snapshot, resolution_analysis
        del trust_verdict, asof_timestamp, repo
        if integrity_assessment is None:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["MISSING_INTEGRITY_ASSESSMENT"],
                scores=_empty_scores(),
                metadata={"policy": self.policy_name},
            )
        action = _action_from_integrity_hint(integrity_assessment.action_hint)
        return ReplayDecision(
            action=action,
            allowed_size_multiplier=ACTION_MULTIPLIERS[action],
            reason_codes=list(integrity_assessment.reason_codes),
            scores=_empty_scores(),
            metadata={
                "policy": self.policy_name,
                "integrity_assessment_id": integrity_assessment.integrity_assessment_id,
                "integrity_overall_risk_score": integrity_assessment.overall_risk_score,
                "integrity_action_hint": integrity_assessment.action_hint.value,
            },
        )


class PreTradeGatePolicy:
    policy_name = "pretrade_gate_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del rule_snapshot, orderbook_snapshot, resolution_analysis
        del integrity_assessment, trust_verdict
        if repo is None:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["PRETRADE_REPOSITORY_UNAVAILABLE"],
                scores=_empty_scores(),
                metadata={"policy": self.policy_name},
            )
        intent = build_trade_intent_from_defaults(
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            strategy_context=StrategyContext.RESEARCH,
            intent_type=TradeIntentType.RESEARCH_ONLY,
            requested_size_units=Decimal("1"),
        )
        try:
            result = PreTradeService(repo).check_pretrade_intent(intent)
        except PreTradeServiceError as exc:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["PRETRADE_GATE_ERROR", exc.code],
                scores=_empty_scores(),
                metadata={
                    "policy": self.policy_name,
                    "pretrade_error_code": exc.code,
                    "pretrade_error_message": exc.message,
                },
            )
        decision = result.decision
        action = decision.action.value
        return ReplayDecision(
            action=action,
            allowed_size_multiplier=decision.allowed_size_multiplier,
            reason_codes=list(decision.reason_codes),
            trust_verdict_id=result.input_snapshot.latest_trust_verdict_id,
            scores={
                **_empty_scores(),
                "resolution_risk_score": decision.resolution_risk_score,
            },
            metadata={
                "policy": self.policy_name,
                "pretrade_decision_id": decision.pretrade_decision_id,
                "pretrade_action": decision.action.value,
                "pretrade_final_allowed_size_units": str(
                    decision.final_allowed_size_units
                ),
                "pretrade_hard_blockers": list(decision.hard_blockers),
                "pretrade_warnings": list(decision.warnings),
                "pretrade_composite_risk_score": decision.composite_risk_score,
            },
        )


class PaperSimGatePolicy:
    policy_name = "paper_sim_gate_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del rule_snapshot, orderbook_snapshot, resolution_analysis
        del integrity_assessment, trust_verdict
        if repo is None:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["PAPER_REPOSITORY_UNAVAILABLE"],
                scores=_empty_scores(),
                metadata={"policy": self.policy_name},
            )
        position = repo.get_latest_paper_position_asof(
            market.market_id,
            asof_timestamp=asof_timestamp,
        )
        intent = build_trade_intent_from_defaults(
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            strategy_context=StrategyContext.RESEARCH,
            intent_type=TradeIntentType.RESEARCH_ONLY,
            requested_size_units=Decimal("1"),
        )
        try:
            result = PreTradeService(repo).check_pretrade_intent(intent)
        except PreTradeServiceError as exc:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["PAPER_PRETRADE_GATE_ERROR", exc.code],
                scores=_empty_scores(),
                metadata={
                    "policy": self.policy_name,
                    "paper_pretrade_error_code": exc.code,
                },
            )
        decision = result.decision
        return ReplayDecision(
            action=decision.action.value,
            allowed_size_multiplier=decision.allowed_size_multiplier,
            reason_codes=list(decision.reason_codes),
            trust_verdict_id=result.input_snapshot.latest_trust_verdict_id,
            scores={
                **_empty_scores(),
                "resolution_risk_score": decision.resolution_risk_score,
            },
            metadata={
                "policy": self.policy_name,
                "pretrade_decision_id": decision.pretrade_decision_id,
                "paper_position_snapshot_id": (
                    position.position_snapshot_id if position else None
                ),
                "paper_position_units": str(position.position_units) if position else None,
                "paper_simulated_exposure_present": bool(
                    position and position.position_units != Decimal("0")
                ),
            },
        )


class ResearchPolicy:
    policy_name = "research_policy_v1"
    policy_version = "1.0.0"

    def decide(
        self,
        *,
        market: Market,
        rule_snapshot: MarketRuleSnapshot | None,
        orderbook_snapshot: OrderBookSnapshot | None,
        resolution_analysis: ResolutionAnalysis | None,
        integrity_assessment: IntegrityAssessment | None,
        trust_verdict: TrustVerdict | None,
        asof_timestamp: datetime,
        repo: PredictionMarketRepository | None = None,
    ) -> ReplayDecision:
        del rule_snapshot, orderbook_snapshot, resolution_analysis
        del integrity_assessment, trust_verdict
        if repo is None:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["RESEARCH_REPOSITORY_UNAVAILABLE"],
                scores=_empty_scores(),
                metadata={"policy": self.policy_name},
            )
        traces = repo.list_research_decision_traces(
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            limit=1,
        )
        if not traces:
            return ReplayDecision(
                action=VerdictAction.MANUAL_REVIEW.value,
                allowed_size_multiplier=Decimal("0.0"),
                reason_codes=["MISSING_RESEARCH_TRACE"],
                scores=_empty_scores(),
                metadata={"policy": self.policy_name},
            )
        trace = traces[0]
        action = trace.pretrade_action or VerdictAction.MANUAL_REVIEW.value
        if action not in ACTION_MULTIPLIERS:
            action = VerdictAction.MANUAL_REVIEW.value
        return ReplayDecision(
            action=action,
            allowed_size_multiplier=ACTION_MULTIPLIERS[action],
            reason_codes=list(trace.reason_codes) or ["RESEARCH_TRACE_AVAILABLE"],
            scores=_empty_scores(),
            metadata={
                "policy": self.policy_name,
                "research_trace_id": trace.trace_id,
                "research_signal_id": trace.research_signal_id,
                "research_proposal_id": trace.proposal_id,
                "research_pretrade_action": trace.pretrade_action,
            },
        )


def get_policy(policy_name: str) -> ReplayPolicy:
    policies: dict[str, ReplayPolicy] = {
        AllowAllPolicy.policy_name: AllowAllPolicy(),
        TrustVerdictPolicy.policy_name: TrustVerdictPolicy(),
        ResolutionRiskOnlyPolicy.policy_name: ResolutionRiskOnlyPolicy(),
        IntegrityGatePolicy.policy_name: IntegrityGatePolicy(),
        PreTradeGatePolicy.policy_name: PreTradeGatePolicy(),
        PaperSimGatePolicy.policy_name: PaperSimGatePolicy(),
        ResearchPolicy.policy_name: ResearchPolicy(),
    }
    try:
        return policies[policy_name]
    except KeyError as exc:
        raise ValueError(f"unknown replay policy: {policy_name}") from exc


def _resolution_risk_score(
    resolution_analysis: ResolutionAnalysis | None,
    trust_verdict: TrustVerdict | None,
) -> int:
    if trust_verdict is not None:
        return trust_verdict.resolution_risk_score
    if resolution_analysis is not None:
        return resolution_analysis.ambiguity_assessment.overall_score
    return 100


def _resolution_reason_codes(
    resolution_analysis: ResolutionAnalysis | None,
    trust_verdict: TrustVerdict | None,
) -> list[str]:
    if resolution_analysis is not None:
        return list(resolution_analysis.ambiguity_assessment.reason_codes)
    if trust_verdict is not None:
        return list(trust_verdict.reason_codes)
    return ["MISSING_RESOLUTION_ANALYSIS"]


def _scores_from_verdict(verdict: TrustVerdict) -> dict[str, int | None]:
    return {
        "price_integrity_score": verdict.price_integrity_score,
        "resolution_risk_score": verdict.resolution_risk_score,
        "liquidity_risk_score": verdict.liquidity_risk_score,
        "cross_venue_consistency_score": verdict.cross_venue_consistency_score,
        "information_freshness_score": verdict.information_freshness_score,
        "manipulation_risk_score": verdict.manipulation_risk_score,
    }


def _empty_scores() -> dict[str, int | None]:
    return {
        "price_integrity_score": None,
        "resolution_risk_score": None,
        "liquidity_risk_score": None,
        "cross_venue_consistency_score": None,
        "information_freshness_score": None,
        "manipulation_risk_score": None,
    }


def _action_from_integrity_hint(action_hint: IntegrityActionHint) -> str:
    if action_hint == IntegrityActionHint.NO_TRADE:
        return VerdictAction.NO_TRADE.value
    if action_hint == IntegrityActionHint.MANUAL_REVIEW:
        return VerdictAction.MANUAL_REVIEW.value
    if action_hint == IntegrityActionHint.PASSIVE_ONLY:
        return VerdictAction.PASSIVE_ONLY.value
    if action_hint == IntegrityActionHint.ALLOW_SMALLER_SIZE:
        return VerdictAction.ALLOW_SMALLER_SIZE.value
    return VerdictAction.ALLOW.value
