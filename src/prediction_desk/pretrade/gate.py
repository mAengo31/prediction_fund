"""Deterministic pre-trade admissibility gate."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.divergence.enums import DivergenceStatus
from prediction_desk.domain.enums import MarketStatus, VerdictAction
from prediction_desk.domain.models import (
    Event,
    Market,
    MarketRuleSnapshot,
    OrderBookSnapshot,
    Venue,
)
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.equivalence.enums import ComparisonPermission
from prediction_desk.integrity.enums import IntegrityActionHint
from prediction_desk.marketdata.models import MarketDataQualityReport, MarketLiquiditySnapshot
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import (
    PreTradeAction,
    StrategyContext,
    TradeIntentType,
    TradeSide,
)
from prediction_desk.pretrade.exposure import evaluate_exposure_limits, get_latest_exposure_asof
from prediction_desk.pretrade.models import (
    DEFAULT_PRETRADE_POLICY_NAME,
    ExposureSnapshot,
    PreTradeCheckResponse,
    PreTradeDecision,
    PreTradeInputSnapshot,
    PreTradePolicy,
    TradeIntent,
    compute_decision_output_hash,
    compute_input_hash,
    compute_trade_intent_id,
)
from prediction_desk.pretrade.policies import build_default_pretrade_policy
from prediction_desk.pretrade.restrictions import (
    ACTION_RANK,
    apply_restrictions,
    find_applicable_restrictions,
)
from prediction_desk.resolution.service import ResolutionCorpusError, ResolutionCorpusService
from prediction_desk.scoring.trust_verdict import build_trust_verdict


class PreTradeGateError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def evaluate_pretrade_gate(
    intent: TradeIntent,
    policy: PreTradePolicy | None = None,
    force_recompute_context: bool = False,
    *,
    repo: PredictionMarketRepository | None = None,
    database_url: str | None = None,
) -> PreTradeCheckResponse:
    if repo is not None:
        return _evaluate_pretrade_gate(
            repo,
            intent,
            policy=policy,
            force_recompute_context=force_recompute_context,
        )
    with session_scope(database_url) as session:
        return _evaluate_pretrade_gate(
            PredictionMarketRepository(session),
            intent,
            policy=policy,
            force_recompute_context=force_recompute_context,
        )


def _evaluate_pretrade_gate(
    repo: PredictionMarketRepository,
    intent: TradeIntent,
    *,
    policy: PreTradePolicy | None,
    force_recompute_context: bool,
) -> PreTradeCheckResponse:
    market = repo.get_market(intent.market_id)
    if market is None:
        raise PreTradeGateError("market_not_found")
    event = repo.get_event(market.event_id)
    venue = repo.get_venue(market.venue_id)
    active_policy = policy or _active_or_default_policy(repo, intent.asof_timestamp)

    rule_snapshot = repo.get_latest_rule_snapshot_asof(market.market_id, intent.asof_timestamp)
    resolution_analysis = None
    if rule_snapshot is not None:
        resolution_analysis = repo.get_latest_resolution_analysis_asof(
            market.market_id,
            intent.asof_timestamp,
        )
        if (
            resolution_analysis is None
            or resolution_analysis.rule_snapshot.rule_snapshot_id
            != rule_snapshot.rule_snapshot_id
        ):
            try:
                resolution_analysis = ResolutionCorpusService(repo).analyze_rule_snapshot(
                    market.market_id,
                    rule_snapshot.rule_snapshot_id,
                )
            except ResolutionCorpusError:
                resolution_analysis = None
    orderbook = repo.get_latest_orderbook_snapshot_asof(market.market_id, intent.asof_timestamp)
    trust_verdict = _trust_verdict_asof(
        repo=repo,
        market=market,
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=orderbook,
        resolution_analysis=resolution_analysis,
        asof_timestamp=intent.asof_timestamp,
        force_recompute=force_recompute_context,
    )
    quality_report = repo.get_latest_quality_report_asof(
        market.market_id,
        intent.asof_timestamp,
    )
    integrity_assessment = repo.get_latest_integrity_assessment_asof(
        market.market_id,
        intent.asof_timestamp,
    )
    equivalence_assessments = repo.list_latest_equivalence_assessments_for_market_asof(
        market.market_id,
        intent.asof_timestamp,
    )
    divergence_assessments = repo.list_latest_divergence_assessments_for_market_asof(
        market.market_id,
        intent.asof_timestamp,
    )
    price_snapshot = repo.get_latest_price_snapshot_asof(market.market_id, intent.asof_timestamp)
    liquidity_snapshot = repo.get_latest_liquidity_snapshot_asof(
        market.market_id,
        intent.asof_timestamp,
    )
    exposure_snapshot = get_latest_exposure_asof(
        repo,
        market_id=market.market_id,
        event_id=market.event_id,
        venue_id=market.venue_id,
        strategy_context=intent.strategy_context.value,
        asof_timestamp=intent.asof_timestamp,
    )
    restrictions = find_applicable_restrictions(
        market,
        event,
        venue,
        intent.asof_timestamp,
        repo.list_market_restriction_rules(limit=10000),
    )
    input_snapshot = _build_input_snapshot(
        intent=intent,
        market=market,
        policy=active_policy,
        rule_snapshot_id=rule_snapshot.rule_snapshot_id if rule_snapshot else None,
        rule_snapshot_hash=rule_snapshot.rule_hash if rule_snapshot else None,
        trust_verdict=trust_verdict,
        quality_report=quality_report,
        integrity_assessment_id=(
            integrity_assessment.integrity_assessment_id if integrity_assessment else None
        ),
        integrity_risk_score=(
            integrity_assessment.overall_risk_score if integrity_assessment else None
        ),
        equivalence_assessments=equivalence_assessments,
        divergence_assessments=divergence_assessments,
        price_snapshot_id=price_snapshot.price_snapshot_id if price_snapshot else None,
        liquidity_snapshot_id=(
            liquidity_snapshot.liquidity_snapshot_id if liquidity_snapshot else None
        ),
        exposure_snapshot=exposure_snapshot,
        restriction_ids=[rule.restriction_id for rule in restrictions],
    )
    intent = repo.save_trade_intent(intent)
    input_snapshot = repo.save_pretrade_input_snapshot(input_snapshot)
    decision = _build_decision(
        intent=intent,
        input_snapshot=input_snapshot,
        policy=active_policy,
        market=market,
        event=event,
        venue=venue,
        trust_verdict=trust_verdict,
        quality_report=quality_report,
        liquidity_snapshot=liquidity_snapshot,
        integrity_action_hint=(
            integrity_assessment.action_hint if integrity_assessment else None
        ),
        restrictions=restrictions,
        exposure_snapshot=exposure_snapshot,
    )
    decision = repo.save_pretrade_decision(decision)
    return PreTradeCheckResponse(
        trade_intent=intent,
        input_snapshot=input_snapshot,
        decision=decision,
    )


def _trust_verdict_asof(
    *,
    repo: PredictionMarketRepository,
    market: Market,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    resolution_analysis: object | None,
    asof_timestamp: datetime,
    force_recompute: bool,
) -> TrustVerdict | None:
    existing = repo.get_latest_trust_verdict_asof(market.market_id, asof_timestamp)
    if existing is not None and not force_recompute and existing.asof_timestamp == asof_timestamp:
        return existing
    ambiguity = (
        getattr(resolution_analysis, "ambiguity_assessment", None)
        if resolution_analysis is not None
        else None
    )
    verdict = build_trust_verdict(
        market=market,
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=orderbook_snapshot,
        asof_timestamp=asof_timestamp,
        ambiguity_assessment=ambiguity,
        integrity_assessment=repo.get_latest_integrity_assessment_asof(
            market.market_id,
            asof_timestamp,
        ),
        equivalence_assessments=repo.list_latest_equivalence_assessments_for_market_asof(
            market.market_id,
            asof_timestamp,
        ),
        divergence_assessments=repo.list_latest_divergence_assessments_for_market_asof(
            market.market_id,
            asof_timestamp,
        ),
    )
    return repo.save_trust_verdict(verdict)


def _build_input_snapshot(
    *,
    intent: TradeIntent,
    market: Market,
    policy: PreTradePolicy,
    rule_snapshot_id: str | None,
    rule_snapshot_hash: str | None,
    trust_verdict: TrustVerdict | None,
    quality_report: MarketDataQualityReport | None,
    integrity_assessment_id: str | None,
    integrity_risk_score: int | None,
    equivalence_assessments: list[Any],
    divergence_assessments: list[Any],
    price_snapshot_id: str | None,
    liquidity_snapshot_id: str | None,
    exposure_snapshot: ExposureSnapshot | None,
    restriction_ids: list[str],
) -> PreTradeInputSnapshot:
    equivalence_counts = _equivalence_counts(market.market_id, equivalence_assessments)
    divergence_counts = _divergence_counts(divergence_assessments)
    snapshot = PreTradeInputSnapshot(
        input_snapshot_id="pending",
        trade_intent_id=intent.trade_intent_id,
        market_id=market.market_id,
        asof_timestamp=intent.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=intent.asof_timestamp,
        market_status=market.status.value,
        event_id=market.event_id,
        venue_id=market.venue_id,
        latest_rule_snapshot_id=rule_snapshot_id,
        latest_rule_snapshot_hash=rule_snapshot_hash,
        latest_trust_verdict_id=trust_verdict.verdict_id if trust_verdict else None,
        latest_quality_report_id=(
            quality_report.quality_report_id if quality_report else None
        ),
        latest_integrity_assessment_id=integrity_assessment_id,
        latest_equivalence_assessment_ids=sorted(
            item.equivalence_assessment_id for item in equivalence_assessments
        ),
        latest_divergence_assessment_ids=sorted(
            item.divergence_assessment_id for item in divergence_assessments
        ),
        latest_price_snapshot_id=price_snapshot_id,
        latest_liquidity_snapshot_id=liquidity_snapshot_id,
        exposure_snapshot_id=(
            exposure_snapshot.exposure_snapshot_id if exposure_snapshot else None
        ),
        policy_id=policy.policy_id,
        restriction_ids=sorted(restriction_ids),
        resolution_risk_score=(
            trust_verdict.resolution_risk_score if trust_verdict else None
        ),
        market_data_quality_score=(
            quality_report.quality_score if quality_report else None
        ),
        integrity_risk_score=integrity_risk_score,
        max_divergence_score=divergence_counts["max_divergence_score"],
        comparable_market_count=equivalence_counts["comparable_market_count"],
        manual_review_equivalence_count=equivalence_counts[
            "manual_review_equivalence_count"
        ],
        do_not_compare_equivalence_count=equivalence_counts[
            "do_not_compare_equivalence_count"
        ],
        divergence_watch_count=int(divergence_counts["divergence_watch_count"] or 0),
        material_divergence_count=int(
            divergence_counts["material_divergence_count"] or 0
        ),
        divergence_needs_review_count=int(
            divergence_counts["divergence_needs_review_count"] or 0
        ),
        divergence_do_not_compare_count=int(
            divergence_counts["divergence_do_not_compare_count"] or 0
        ),
        current_market_exposure_units=(
            exposure_snapshot.market_exposure_units if exposure_snapshot else None
        ),
        current_event_exposure_units=(
            exposure_snapshot.event_exposure_units if exposure_snapshot else None
        ),
        current_venue_exposure_units=(
            exposure_snapshot.venue_exposure_units if exposure_snapshot else None
        ),
        current_strategy_exposure_units=(
            exposure_snapshot.strategy_exposure_units if exposure_snapshot else None
        ),
        input_hash="pending",
        metadata={"input_version": "pretrade_input_snapshot_v1"},
    )
    input_hash = compute_input_hash(snapshot)
    return snapshot.model_copy(
        update={
            "input_snapshot_id": f"pretrade_input_{input_hash[:24]}",
            "input_hash": input_hash,
        }
    )


def _build_decision(
    *,
    intent: TradeIntent,
    input_snapshot: PreTradeInputSnapshot,
    policy: PreTradePolicy,
    market: Market,
    event: Event | None,
    venue: Venue | None,
    trust_verdict: TrustVerdict | None,
    quality_report: MarketDataQualityReport | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
    integrity_action_hint: IntegrityActionHint | None,
    restrictions: list[Any],
    exposure_snapshot: ExposureSnapshot | None,
) -> PreTradeDecision:
    action = PreTradeAction.ALLOW
    hard_blockers: list[str] = []
    warnings: list[str] = []
    reason_codes: list[str] = []
    evidence: dict[str, Any] = {}
    max_allowed_size = intent.requested_size_units

    if policy.require_active_market and market.status != MarketStatus.ACTIVE:
        action = PreTradeAction.NO_TRADE
        hard_blockers.append("MARKET_NOT_ACTIVE")
        reason_codes.append("MARKET_NOT_ACTIVE")
    if policy.require_rule_snapshot and input_snapshot.latest_rule_snapshot_id is None:
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
        warnings.append("MISSING_RULE_SNAPSHOT")
        reason_codes.append("MISSING_RULE_SNAPSHOT")
    if policy.require_trust_verdict and trust_verdict is None:
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
        warnings.append("MISSING_TRUST_VERDICT")
        reason_codes.append("MISSING_TRUST_VERDICT")

    restriction_result = apply_restrictions(
        action,
        restrictions,
        intent.requested_size_units,
    )
    action = restriction_result.action
    max_allowed_size = min(max_allowed_size, restriction_result.max_allowed_size_units)
    hard_blockers.extend(restriction_result.hard_blockers)
    warnings.extend(restriction_result.warnings)
    reason_codes.extend(restriction_result.reason_codes)
    evidence["restrictions"] = restriction_result.evidence

    if trust_verdict is not None:
        action = _apply_trust_verdict(action, trust_verdict.action)
        reason_codes.extend(f"TRUST_{code}" for code in trust_verdict.reason_codes)
    resolution_risk = input_snapshot.resolution_risk_score
    if resolution_risk is not None and resolution_risk >= policy.max_resolution_risk_score:
        action = PreTradeAction.NO_TRADE if resolution_risk >= 80 else _max_action(
            action,
            PreTradeAction.MANUAL_REVIEW,
        )
        reason_codes.append("RESOLUTION_RISK_ABOVE_POLICY_LIMIT")
        if resolution_risk >= 80:
            hard_blockers.append("RESOLUTION_RISK_ABOVE_POLICY_LIMIT")
        else:
            warnings.append("RESOLUTION_RISK_ABOVE_POLICY_LIMIT")

    _apply_quality(
        policy,
        quality_report,
        liquidity_snapshot,
        reason_codes,
        warnings,
        hard_blockers,
        evidence,
    )
    if (
        quality_report is not None
        and quality_report.quality_score < policy.min_market_data_quality_score
    ):
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
    if (
        quality_report is None
        and policy.require_market_data_quality
    ):
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
    if "STALE_MARKET_DATA" in warnings:
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
    if (
        "SPREAD_ABOVE_POLICY_LIMIT" in warnings
        or "SPREAD_BPS_ABOVE_POLICY_LIMIT" in warnings
    ):
        action = _max_action(action, PreTradeAction.PASSIVE_ONLY)

    integrity_risk = input_snapshot.integrity_risk_score
    if integrity_risk is not None and integrity_risk >= policy.max_integrity_risk_score:
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
        warnings.append("INTEGRITY_RISK_ABOVE_POLICY_LIMIT")
        reason_codes.append("INTEGRITY_RISK_ABOVE_POLICY_LIMIT")
    if integrity_action_hint == IntegrityActionHint.NO_TRADE:
        action = PreTradeAction.NO_TRADE
        hard_blockers.append("INTEGRITY_ACTION_HINT_NO_TRADE")
        reason_codes.append("INTEGRITY_ACTION_HINT_NO_TRADE")
    elif integrity_action_hint == IntegrityActionHint.MANUAL_REVIEW:
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
        warnings.append("INTEGRITY_ACTION_HINT_MANUAL_REVIEW")
        reason_codes.append("INTEGRITY_ACTION_HINT_MANUAL_REVIEW")

    _apply_divergence_context(
        intent,
        policy,
        input_snapshot,
        reason_codes,
        warnings,
        hard_blockers,
    )
    if intent.strategy_context == StrategyContext.CROSS_VENUE_COMPARISON:
        if input_snapshot.divergence_do_not_compare_count > 0:
            action = PreTradeAction.NO_TRADE
        elif (
            input_snapshot.divergence_needs_review_count > 0
            or (input_snapshot.max_divergence_score or 0)
            > policy.max_divergence_score_without_review
            or not input_snapshot.latest_equivalence_assessment_ids
            or not input_snapshot.latest_divergence_assessment_ids
        ):
            action = _max_action(action, PreTradeAction.MANUAL_REVIEW)

    if action == PreTradeAction.PASSIVE_ONLY and intent.intent_type in {
        TradeIntentType.AGGRESSIVE_LIMIT,
        TradeIntentType.MARKET_LIKE,
    }:
        action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
        warnings.append("AGGRESSIVE_INTENT_BLOCKED_BY_PASSIVE_ONLY")
        reason_codes.append("AGGRESSIVE_INTENT_BLOCKED_BY_PASSIVE_ONLY")

    exposure = evaluate_exposure_limits(intent, policy, exposure_snapshot)
    max_allowed_size = min(max_allowed_size, exposure.max_allowed_size_units)
    action = _max_action(action, exposure.action)
    hard_blockers.extend(exposure.hard_blockers)
    warnings.extend(exposure.warnings)
    reason_codes.extend(exposure.reason_codes)
    evidence["exposure"] = exposure.evidence

    if action == PreTradeAction.NO_TRADE:
        max_allowed_size = Decimal("0")
    final_allowed = min(intent.requested_size_units, max_allowed_size)
    if final_allowed < intent.requested_size_units and action == PreTradeAction.ALLOW:
        action = PreTradeAction.ALLOW_SMALLER_SIZE
    if action in {PreTradeAction.MANUAL_REVIEW, PreTradeAction.NO_TRADE}:
        final_allowed = Decimal("0")
    multiplier = (
        Decimal("0")
        if intent.requested_size_units == 0
        else final_allowed / intent.requested_size_units
    )
    composite = _composite_risk(input_snapshot, exposure.exposure_risk_score)
    decision = PreTradeDecision(
        pretrade_decision_id="pending",
        trade_intent_id=intent.trade_intent_id,
        input_snapshot_id=input_snapshot.input_snapshot_id,
        market_id=market.market_id,
        asof_timestamp=intent.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=intent.asof_timestamp,
        policy_id=policy.policy_id,
        policy_name=policy.policy_name,
        policy_version=policy.policy_version,
        action=action,
        allowed_size_multiplier=multiplier,
        requested_size_units=intent.requested_size_units,
        max_allowed_size_units=max_allowed_size,
        final_allowed_size_units=final_allowed,
        passive_only=action == PreTradeAction.PASSIVE_ONLY,
        manual_review_required=action == PreTradeAction.MANUAL_REVIEW,
        hard_blocked=action == PreTradeAction.NO_TRADE,
        composite_risk_score=composite,
        resolution_risk_score=input_snapshot.resolution_risk_score,
        market_data_quality_score=input_snapshot.market_data_quality_score,
        integrity_risk_score=input_snapshot.integrity_risk_score,
        max_divergence_score=input_snapshot.max_divergence_score,
        exposure_risk_score=exposure.exposure_risk_score,
        hard_blockers=sorted(set(hard_blockers)),
        warnings=sorted(set(warnings)),
        reason_codes=sorted(set(reason_codes)),
        evidence={
            **evidence,
            "market_id": market.market_id,
            "event_id": event.event_id if event else None,
            "venue_id": venue.venue_id if venue else market.venue_id,
        },
        input_hash=input_snapshot.input_hash,
        output_hash="pending",
        metadata={"decision_version": "pretrade_decision_v1"},
    )
    output_hash = compute_decision_output_hash(decision)
    return decision.model_copy(
        update={
            "pretrade_decision_id": f"pretrade_decision_{output_hash[:24]}",
            "output_hash": output_hash,
        }
    )


def _apply_quality(
    policy: PreTradePolicy,
    quality_report: MarketDataQualityReport | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
    reason_codes: list[str],
    warnings: list[str],
    hard_blockers: list[str],
    evidence: dict[str, Any],
) -> None:
    del hard_blockers
    if quality_report is None:
        if policy.require_market_data_quality:
            reason_codes.append("MISSING_MARKET_DATA_QUALITY")
            warnings.append("MISSING_MARKET_DATA_QUALITY")
        return
    if quality_report.quality_score < policy.min_market_data_quality_score:
        reason_codes.append("LOW_MARKET_DATA_QUALITY")
        warnings.append("LOW_MARKET_DATA_QUALITY")
    if (
        quality_report.freshness_seconds is not None
        and quality_report.freshness_seconds > policy.max_staleness_seconds
    ):
        reason_codes.append("STALE_MARKET_DATA")
        warnings.append("STALE_MARKET_DATA")
    if liquidity_snapshot is not None:
        evidence["liquidity"] = {
            "spread": str(liquidity_snapshot.spread),
            "spread_bps": str(liquidity_snapshot.spread_bps),
        }
        if (
            policy.max_spread is not None
            and liquidity_snapshot.spread is not None
            and liquidity_snapshot.spread > policy.max_spread
        ):
            reason_codes.append("SPREAD_ABOVE_POLICY_LIMIT")
            warnings.append("SPREAD_ABOVE_POLICY_LIMIT")
        if (
            policy.max_spread_bps is not None
            and liquidity_snapshot.spread_bps is not None
            and liquidity_snapshot.spread_bps > policy.max_spread_bps
        ):
            reason_codes.append("SPREAD_BPS_ABOVE_POLICY_LIMIT")
            warnings.append("SPREAD_BPS_ABOVE_POLICY_LIMIT")


def _apply_divergence_context(
    intent: TradeIntent,
    policy: PreTradePolicy,
    input_snapshot: PreTradeInputSnapshot,
    reason_codes: list[str],
    warnings: list[str],
    hard_blockers: list[str],
) -> None:
    del policy
    if intent.strategy_context == StrategyContext.CROSS_VENUE_COMPARISON:
        if not input_snapshot.latest_equivalence_assessment_ids:
            reason_codes.append("MISSING_EQUIVALENCE_CONTEXT")
            warnings.append("MISSING_EQUIVALENCE_CONTEXT")
        if not input_snapshot.latest_divergence_assessment_ids:
            reason_codes.append("MISSING_DIVERGENCE_CONTEXT")
            warnings.append("MISSING_DIVERGENCE_CONTEXT")
    if input_snapshot.divergence_do_not_compare_count > 0:
        reason_codes.append("DIVERGENCE_DO_NOT_COMPARE_CONTEXT")
        hard_blockers.append("DIVERGENCE_DO_NOT_COMPARE_CONTEXT")
    if input_snapshot.divergence_needs_review_count > 0:
        reason_codes.append("DIVERGENCE_NEEDS_REVIEW_CONTEXT")
        warnings.append("DIVERGENCE_NEEDS_REVIEW_CONTEXT")
    if (
        input_snapshot.max_divergence_score is not None
        and input_snapshot.max_divergence_score >= 70
    ):
        reason_codes.append("DIVERGENCE_SCORE_REQUIRES_REVIEW")
        warnings.append("DIVERGENCE_SCORE_REQUIRES_REVIEW")


def _active_or_default_policy(
    repo: PredictionMarketRepository,
    asof_timestamp: datetime,
) -> PreTradePolicy:
    policy = repo.get_active_pretrade_policy(
        DEFAULT_PRETRADE_POLICY_NAME,
        asof_timestamp,
    )
    if policy is not None:
        return policy
    return repo.save_pretrade_policy(build_default_pretrade_policy())


def _apply_trust_verdict(action: PreTradeAction, verdict_action: VerdictAction) -> PreTradeAction:
    mapping = {
        VerdictAction.ALLOW: PreTradeAction.ALLOW,
        VerdictAction.ALLOW_SMALLER_SIZE: PreTradeAction.ALLOW_SMALLER_SIZE,
        VerdictAction.PASSIVE_ONLY: PreTradeAction.PASSIVE_ONLY,
        VerdictAction.MANUAL_REVIEW: PreTradeAction.MANUAL_REVIEW,
        VerdictAction.NO_TRADE: PreTradeAction.NO_TRADE,
    }
    return _max_action(action, mapping[verdict_action])


def _max_action(left: PreTradeAction, right: PreTradeAction) -> PreTradeAction:
    return left if ACTION_RANK[left] >= ACTION_RANK[right] else right


def _equivalence_counts(
    market_id: str,
    assessments: list[Any],
) -> dict[str, int]:
    comparable = {ComparisonPermission.COMPARABLE, ComparisonPermission.COMPARABLE_WITH_HAIRCUT}
    comparable_markets: set[str] = set()
    manual_review = 0
    do_not_compare = 0
    for assessment in assessments:
        other = (
            assessment.right_market_id
            if assessment.left_market_id == market_id
            else assessment.left_market_id
        )
        if assessment.comparison_permission in comparable:
            comparable_markets.add(other)
        elif assessment.comparison_permission == ComparisonPermission.MANUAL_REVIEW:
            manual_review += 1
        elif assessment.comparison_permission == ComparisonPermission.DO_NOT_COMPARE:
            do_not_compare += 1
    return {
        "comparable_market_count": len(comparable_markets),
        "manual_review_equivalence_count": manual_review,
        "do_not_compare_equivalence_count": do_not_compare,
    }


def _divergence_counts(assessments: list[Any]) -> dict[str, int | None]:
    counts = {status.value: 0 for status in DivergenceStatus}
    max_score: int | None = None
    for assessment in assessments:
        counts[assessment.status.value] = counts.get(assessment.status.value, 0) + 1
        max_score = (
            assessment.overall_divergence_score
            if max_score is None
            else max(max_score, assessment.overall_divergence_score)
        )
    return {
        "divergence_watch_count": counts[DivergenceStatus.WATCH.value],
        "material_divergence_count": counts[DivergenceStatus.MATERIAL_DIVERGENCE.value],
        "divergence_needs_review_count": counts[DivergenceStatus.NEEDS_REVIEW.value],
        "divergence_do_not_compare_count": counts[DivergenceStatus.DO_NOT_COMPARE.value],
        "max_divergence_score": max_score,
    }


def _composite_risk(
    input_snapshot: PreTradeInputSnapshot,
    exposure_risk_score: int | None,
) -> int:
    quality_risk = (
        100 - input_snapshot.market_data_quality_score
        if input_snapshot.market_data_quality_score is not None
        else 50
    )
    return max(
        input_snapshot.resolution_risk_score or 0,
        input_snapshot.integrity_risk_score or 0,
        input_snapshot.max_divergence_score or 0,
        exposure_risk_score or 0,
        quality_risk,
    )


def build_trade_intent_from_defaults(
    *,
    market_id: str,
    asof_timestamp: datetime,
    strategy_context: StrategyContext = StrategyContext.RESEARCH,
    intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY,
    requested_size_units: Decimal = Decimal("1"),
) -> TradeIntent:
    intent = TradeIntent(
        trade_intent_id="pending",
        market_id=market_id,
        outcome_id=None,
        venue_id=None,
        strategy_context=strategy_context,
        side=TradeSide.BUY,
        intent_type=intent_type,
        requested_price=None,
        requested_size_units=requested_size_units,
        requested_notional_usd=None,
        asof_timestamp=asof_timestamp,
        metadata={},
    )
    return intent.model_copy(update={"trade_intent_id": compute_trade_intent_id(intent)})
