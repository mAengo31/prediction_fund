"""Decision-card builders for the desk workbench."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.workbench.evidence import latest_data_gaps_for_market
from prediction_desk.workbench.models import (
    CrossVenueComparisonCard,
    MarketDecisionCard,
    compute_decision_card_input_hash,
    compute_decision_card_output_hash,
    hash_payload,
    workbench_object_id,
)
from prediction_desk.workbench.scoring import recommended_action, score_review_context


def build_market_decision_card(
    market_id: str,
    asof_timestamp: datetime,
    *,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> MarketDecisionCard:
    if repo is not None:
        return _build_market_decision_card(repo, market_id, asof_timestamp, force=force)
    with session_scope() as session:
        return _build_market_decision_card(
            PredictionMarketRepository(session),
            market_id,
            asof_timestamp,
            force=force,
        )


def build_cross_venue_comparison_card(
    equivalence_assessment_id: str,
    asof_timestamp: datetime,
    *,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> CrossVenueComparisonCard:
    if repo is not None:
        return _build_cross_venue_comparison_card(
            repo,
            equivalence_assessment_id,
            asof_timestamp,
            force=force,
        )
    with session_scope() as session:
        return _build_cross_venue_comparison_card(
            PredictionMarketRepository(session),
            equivalence_assessment_id,
            asof_timestamp,
            force=force,
        )


def _build_market_decision_card(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
    *,
    force: bool,
) -> MarketDecisionCard:
    market = repo.get_market(market_id)
    if market is None:
        raise ValueError("market_not_found")
    venue = repo.get_venue(market.venue_id)
    event = repo.get_event(market.event_id)
    price = repo.get_latest_price_snapshot_asof(market_id, asof_timestamp)
    liquidity = repo.get_latest_liquidity_snapshot_asof(market_id, asof_timestamp)
    quality = repo.get_latest_quality_report_asof(market_id, asof_timestamp)
    rule = repo.get_latest_rule_snapshot_asof(market_id, asof_timestamp)
    integrity = repo.get_latest_integrity_assessment_asof(market_id, asof_timestamp)
    equivalences = repo.list_latest_equivalence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
        limit=25,
    )
    divergences = repo.list_latest_divergence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
        limit=25,
    )
    pretrade = repo.get_latest_pretrade_decision_asof(market_id, asof_timestamp)
    paper_orders = [
        order
        for order in repo.list_paper_orders(market_id=market_id, limit=25)
        if _as_utc(order.available_at) <= _as_utc(asof_timestamp)
    ]
    paper_position = repo.get_latest_paper_position_asof(
        market_id,
        asof_timestamp=asof_timestamp,
    )
    paper_portfolio = repo.get_latest_paper_portfolio_asof(asof_timestamp=asof_timestamp)
    research_signals = repo.list_research_signals(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        limit=25,
    )
    research_proposals = repo.list_research_intent_proposals(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        limit=25,
    )
    research_traces = repo.list_research_decision_traces(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        limit=25,
    )
    scenario = repo.get_latest_scenario_feature_asof(market_id, asof_timestamp)
    gaps = latest_data_gaps_for_market(repo, market_id, asof_timestamp, limit=100)
    priority_score, reason_codes = score_review_context(
        quality_report=quality,
        integrity_assessment=integrity,
        divergence_assessments=divergences,
        pretrade_decision=pretrade,
        research_signals=research_signals,
        data_gaps=gaps,
        scenario_feature=scenario,
    )
    source_ref_ids = _dedupe(
        [
            price.price_snapshot_id if price else None,
            liquidity.liquidity_snapshot_id if liquidity else None,
            quality.quality_report_id if quality else None,
            rule.rule_snapshot_id if rule else None,
            integrity.integrity_assessment_id if integrity else None,
            pretrade.pretrade_decision_id if pretrade else None,
            scenario.scenario_feature_snapshot_id if scenario else None,
            *[item.equivalence_assessment_id for item in equivalences],
            *[item.divergence_assessment_id for item in divergences],
            *[item.research_signal_id for item in research_signals],
            *[item.proposal_id for item in research_proposals],
            *[item.trace_id for item in research_traces],
            *[item.paper_order_id for item in paper_orders],
            *[item.data_gap_id for item in gaps],
        ]
    )
    input_hash = compute_decision_card_input_hash(market_id, asof_timestamp, source_ref_ids)
    existing = repo.find_market_decision_card_by_hash(input_hash)
    if existing is not None and not force:
        return existing

    card = MarketDecisionCard(
        decision_card_id=workbench_object_id("decision_card", {"input_hash": input_hash}),
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=asof_timestamp,
        title=market.title,
        venue_name=venue.name if venue else market.venue_id,
        market_status=market.status.value,
        category=event.category if event else None,
        latest_price=(
            price.price if price and price.price is not None else price.mid if price else None
        ),
        bid=price.bid if price else None,
        ask=price.ask if price else None,
        spread=liquidity.spread if liquidity else price.spread if price else None,
        liquidity_summary=_liquidity_summary(liquidity),
        data_quality_summary=_quality_summary(quality),
        rule_summary=_rule_summary(rule),
        integrity_summary=_integrity_summary(integrity),
        equivalence_summary=_equivalence_summary(equivalences),
        divergence_summary=_divergence_summary(divergences),
        pretrade_summary=_pretrade_summary(pretrade),
        paper_summary=_paper_summary(paper_orders, paper_position, paper_portfolio),
        research_summary=_research_summary(research_signals, research_proposals, research_traces),
        scenario_summary=_scenario_summary(scenario),
        data_gap_summary=_data_gap_summary(gaps),
        review_priority_score=priority_score,
        review_reason_codes=reason_codes,
        recommended_next_review_action=recommended_action(reason_codes),
        source_ref_ids=source_ref_ids,
        input_hash=input_hash,
        output_hash="pending",
        metadata={"workbench_version": "desk_workbench_v1"},
    )
    return repo.save_market_decision_card(
        card.model_copy(update={"output_hash": compute_decision_card_output_hash(card)})
    )


def _build_cross_venue_comparison_card(
    repo: PredictionMarketRepository,
    equivalence_assessment_id: str,
    asof_timestamp: datetime,
    *,
    force: bool,
) -> CrossVenueComparisonCard:
    equivalence = repo.get_market_equivalence_assessment(equivalence_assessment_id)
    if equivalence is None or _as_utc(equivalence.available_at) > _as_utc(asof_timestamp):
        raise ValueError("equivalence_assessment_not_found")
    divergence = repo.get_latest_divergence_assessment_asof(
        equivalence.left_market_id,
        equivalence.right_market_id,
        asof_timestamp,
    )
    source_ref_ids = _dedupe(
        [
            equivalence.equivalence_assessment_id,
            divergence.divergence_assessment_id if divergence else None,
            equivalence.left_rule_snapshot_id,
            equivalence.right_rule_snapshot_id,
        ]
    )
    card_id = workbench_object_id(
        "comparison_card",
        {
            "version": "cross_venue_comparison_card_v1",
            "equivalence_assessment_id": equivalence.equivalence_assessment_id,
            "divergence_assessment_id": (
                divergence.divergence_assessment_id if divergence else None
            ),
            "asof_timestamp": asof_timestamp,
        },
    )
    existing = repo.get_cross_venue_comparison_card(card_id)
    if existing is not None and not force:
        return existing

    left_price = repo.get_latest_price_snapshot_asof(
        equivalence.left_market_id,
        asof_timestamp,
    )
    right_price = repo.get_latest_price_snapshot_asof(
        equivalence.right_market_id,
        asof_timestamp,
    )
    left_liquidity = repo.get_latest_liquidity_snapshot_asof(
        equivalence.left_market_id,
        asof_timestamp,
    )
    right_liquidity = repo.get_latest_liquidity_snapshot_asof(
        equivalence.right_market_id,
        asof_timestamp,
    )
    left_quality = repo.get_latest_quality_report_asof(
        equivalence.left_market_id,
        asof_timestamp,
    )
    right_quality = repo.get_latest_quality_report_asof(
        equivalence.right_market_id,
        asof_timestamp,
    )
    left_integrity = repo.get_latest_integrity_assessment_asof(
        equivalence.left_market_id,
        asof_timestamp,
    )
    right_integrity = repo.get_latest_integrity_assessment_asof(
        equivalence.right_market_id,
        asof_timestamp,
    )
    reason_codes = _dedupe(
        [
            *equivalence.reason_codes,
            *(divergence.reason_codes if divergence else []),
        ]
    )
    if divergence is not None:
        action = recommended_action(["DIVERGENCE_REVIEW", *reason_codes])
    elif equivalence.comparison_permission.value != "COMPARE":
        action = recommended_action(["DIVERGENCE_NEEDS_REVIEW", *reason_codes])
    else:
        action = recommended_action(reason_codes)
    card = CrossVenueComparisonCard(
        comparison_card_id=card_id,
        equivalence_assessment_id=equivalence.equivalence_assessment_id,
        divergence_assessment_id=divergence.divergence_assessment_id if divergence else None,
        asof_timestamp=asof_timestamp,
        left_market_id=equivalence.left_market_id,
        right_market_id=equivalence.right_market_id,
        equivalence_status=equivalence.status.value,
        comparison_permission=equivalence.comparison_permission.value,
        equivalence_score=equivalence.overall_score,
        divergence_status=divergence.status.value if divergence else None,
        divergence_score=divergence.overall_divergence_score if divergence else None,
        aligned_price_summary={
            "left_price": left_price.price if left_price else None,
            "right_price": right_price.price if right_price else None,
            "left_mid": left_price.mid if left_price else None,
            "right_mid": right_price.mid if right_price else None,
            "absolute_mid_gap": divergence.absolute_mid_gap if divergence else None,
            "spread_adjusted_gap": divergence.spread_adjusted_gap if divergence else None,
        },
        liquidity_comparison={
            "left_spread": left_liquidity.spread if left_liquidity else None,
            "right_spread": right_liquidity.spread if right_liquidity else None,
            "left_total_depth": (
                left_liquidity.total_bid_depth + left_liquidity.total_ask_depth
                if left_liquidity
                else None
            ),
            "right_total_depth": (
                right_liquidity.total_bid_depth + right_liquidity.total_ask_depth
                if right_liquidity
                else None
            ),
        },
        data_quality_comparison={
            "left_quality_score": left_quality.quality_score if left_quality else None,
            "right_quality_score": right_quality.quality_score if right_quality else None,
            "left_reason_codes": list(left_quality.reason_codes) if left_quality else [],
            "right_reason_codes": list(right_quality.reason_codes) if right_quality else [],
        },
        rule_comparison={
            "left_rule_snapshot_id": equivalence.left_rule_snapshot_id,
            "right_rule_snapshot_id": equivalence.right_rule_snapshot_id,
            "predicate_similarity_score": equivalence.predicate_similarity_score,
            "resolution_source_mismatch": equivalence.resolution_source_mismatch,
            "deadline_mismatch": equivalence.deadline_mismatch,
        },
        integrity_comparison={
            "left_integrity_risk_score": (
                left_integrity.overall_risk_score if left_integrity else None
            ),
            "right_integrity_risk_score": (
                right_integrity.overall_risk_score if right_integrity else None
            ),
        },
        reason_codes=reason_codes,
        recommended_next_review_action=action,
        source_ref_ids=source_ref_ids,
        metadata={
            "workbench_version": "desk_workbench_v1",
            "input_hash": hash_payload({"source_ref_ids": source_ref_ids}),
        },
    )
    return repo.save_cross_venue_comparison_card(card)


def _liquidity_summary(liquidity: Any | None) -> dict[str, Any]:
    if liquidity is None:
        return {"available": False}
    return {
        "available": True,
        "liquidity_snapshot_id": liquidity.liquidity_snapshot_id,
        "best_bid": liquidity.best_bid,
        "best_ask": liquidity.best_ask,
        "mid_price": liquidity.mid_price,
        "spread": liquidity.spread,
        "spread_bps": liquidity.spread_bps,
        "total_bid_depth": liquidity.total_bid_depth,
        "total_ask_depth": liquidity.total_ask_depth,
        "is_empty_book": liquidity.is_empty_book,
        "is_crossed_book": liquidity.is_crossed_book,
    }


def _quality_summary(quality: Any | None) -> dict[str, Any]:
    if quality is None:
        return {"available": False, "reason_codes": ["NO_QUALITY_REPORT"]}
    return {
        "available": True,
        "quality_report_id": quality.quality_report_id,
        "quality_score": quality.quality_score,
        "severity": quality.severity.value,
        "freshness_seconds": quality.freshness_seconds,
        "reason_codes": list(quality.reason_codes),
    }


def _rule_summary(rule: Any | None) -> dict[str, Any]:
    if rule is None:
        return {"available": False, "reason_codes": ["NO_RULE_SNAPSHOT"]}
    return {
        "available": True,
        "rule_snapshot_id": rule.rule_snapshot_id,
        "rule_hash": rule.rule_hash,
        "resolution_source": rule.resolution_source,
        "settlement_authority": rule.settlement_authority,
        "has_normalized_rule_text": bool(rule.normalized_rule_text),
    }


def _integrity_summary(integrity: Any | None) -> dict[str, Any]:
    if integrity is None:
        return {"available": False}
    return {
        "available": True,
        "integrity_assessment_id": integrity.integrity_assessment_id,
        "overall_risk_score": integrity.overall_risk_score,
        "severity": integrity.severity.value,
        "action_hint": integrity.action_hint.value,
        "reason_codes": list(integrity.reason_codes),
    }


def _equivalence_summary(equivalences: list[Any]) -> dict[str, Any]:
    return {
        "count": len(equivalences),
        "assessment_ids": [item.equivalence_assessment_id for item in equivalences],
        "status_counts": dict(Counter(item.status.value for item in equivalences)),
        "permission_counts": dict(
            Counter(item.comparison_permission.value for item in equivalences)
        ),
        "max_score": max((item.overall_score for item in equivalences), default=None),
    }


def _divergence_summary(divergences: list[Any]) -> dict[str, Any]:
    return {
        "count": len(divergences),
        "assessment_ids": [item.divergence_assessment_id for item in divergences],
        "status_counts": dict(Counter(item.status.value for item in divergences)),
        "max_score": max((item.overall_divergence_score for item in divergences), default=None),
        "reason_codes": _dedupe(
            [reason for item in divergences for reason in item.reason_codes]
        ),
    }


def _pretrade_summary(pretrade: Any | None) -> dict[str, Any]:
    if pretrade is None:
        return {"available": False}
    return {
        "available": True,
        "pretrade_decision_id": pretrade.pretrade_decision_id,
        "action": pretrade.action.value,
        "final_allowed_size_units": pretrade.final_allowed_size_units,
        "reason_codes": list(pretrade.reason_codes),
    }


def _paper_summary(
    paper_orders: list[Any],
    paper_position: Any | None,
    paper_portfolio: Any | None,
) -> dict[str, Any]:
    return {
        "paper_order_count": len(paper_orders),
        "paper_order_ids": [item.paper_order_id for item in paper_orders],
        "paper_order_status_counts": dict(Counter(item.status.value for item in paper_orders)),
        "position_snapshot_id": (
            paper_position.position_snapshot_id if paper_position else None
        ),
        "position_units_simulated": (
            paper_position.position_units if paper_position else None
        ),
        "portfolio_snapshot_id": (
            paper_portfolio.portfolio_snapshot_id if paper_portfolio else None
        ),
        "portfolio_equity_simulated": (
            paper_portfolio.total_equity_simulated if paper_portfolio else None
        ),
        "is_simulated": True,
    }


def _research_summary(
    signals: list[Any],
    proposals: list[Any],
    traces: list[Any],
) -> dict[str, Any]:
    return {
        "signal_count": len(signals),
        "proposal_count": len(proposals),
        "trace_count": len(traces),
        "signal_ids": [item.research_signal_id for item in signals],
        "proposal_ids": [item.proposal_id for item in proposals],
        "trace_ids": [item.trace_id for item in traces],
        "signal_type_counts": dict(Counter(item.signal_type.value for item in signals)),
        "pretrade_action_counts": dict(
            Counter(item.pretrade_action for item in traces if item.pretrade_action)
        ),
    }


def _scenario_summary(scenario: Any | None) -> dict[str, Any]:
    if scenario is None:
        return {"available": False}
    return {
        "available": True,
        "scenario_feature_snapshot_id": scenario.scenario_feature_snapshot_id,
        "scenario_confidence_score": scenario.scenario_confidence_score,
        "scenario_uncertainty_score": scenario.scenario_uncertainty_score,
        "reason_codes": list(scenario.reason_codes),
        "key_scenario_labels": list(scenario.key_scenario_labels),
    }


def _data_gap_summary(gaps: list[Any]) -> dict[str, Any]:
    return {
        "gap_count": len(gaps),
        "gap_ids": [gap.data_gap_id for gap in gaps],
        "gap_type_counts": dict(Counter(gap.gap_type.value for gap in gaps)),
        "severity_counts": dict(Counter(gap.severity.value for gap in gaps)),
        "reason_codes": _dedupe([gap.reason_code for gap in gaps]),
    }


def _dedupe(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
