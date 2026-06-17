"""Build deterministic market trust verdicts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from prediction_desk.divergence.enums import DivergenceStatus
from prediction_desk.divergence.models import CrossVenueDivergenceAssessment
from prediction_desk.domain.enums import VerdictAction
from prediction_desk.domain.models import Market, MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.equivalence.enums import ComparisonPermission
from prediction_desk.equivalence.models import MarketEquivalenceAssessment
from prediction_desk.integrity.enums import IntegrityActionHint
from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.resolution.models import AmbiguityAssessment
from prediction_desk.scoring.resolution_risk import score_resolution_risk

SCORER_VERSION = "trust_verdict_v0"


def build_trust_verdict(
    market: Market,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    asof_timestamp: datetime,
    ambiguity_assessment: AmbiguityAssessment | None = None,
    integrity_assessment: IntegrityAssessment | None = None,
    equivalence_assessments: list[MarketEquivalenceAssessment] | None = None,
    divergence_assessments: list[CrossVenueDivergenceAssessment] | None = None,
) -> TrustVerdict:
    resolution_result = score_resolution_risk(market, rule_snapshot, ambiguity_assessment)
    liquidity_risk_score, liquidity_reasons = _score_liquidity(orderbook_snapshot)
    reason_codes = [*resolution_result.reason_codes, *liquidity_reasons]

    if resolution_result.resolution_risk_score >= 80:
        action = VerdictAction.NO_TRADE
    elif resolution_result.resolution_risk_score >= 50 or orderbook_snapshot is None:
        action = VerdictAction.MANUAL_REVIEW
    elif liquidity_risk_score >= 70:
        action = VerdictAction.PASSIVE_ONLY
    else:
        action = VerdictAction.ALLOW

    source_refs = _source_refs(rule_snapshot, orderbook_snapshot)
    data_versions: dict[str, Any] = {
        "orderbook_snapshot_id": orderbook_snapshot.snapshot_id if orderbook_snapshot else None,
        "rule_hash": rule_snapshot.rule_hash if rule_snapshot else None,
        "rule_snapshot_id": rule_snapshot.rule_snapshot_id if rule_snapshot else None,
        "ambiguity_assessment_id": (
            ambiguity_assessment.assessment_id if ambiguity_assessment else None
        ),
        "integrity_assessment_id": (
            integrity_assessment.integrity_assessment_id if integrity_assessment else None
        ),
        "equivalence_assessment_ids": sorted(
            assessment.equivalence_assessment_id
            for assessment in (equivalence_assessments or [])
        ),
        "divergence_assessment_ids": sorted(
            assessment.divergence_assessment_id
            for assessment in (divergence_assessments or [])
        ),
    }
    price_integrity_score = 100 if orderbook_snapshot is not None else 50
    information_freshness_score = 100
    manipulation_risk_score = 0
    metadata: dict[str, Any] = {}
    model_versions: dict[str, str] = {
        "liquidity_scorer": "liquidity_v0",
        "resolution_risk_scorer": (
            "resolution_risk_v1_with_ambiguity"
            if ambiguity_assessment
            else "resolution_risk_v0"
        ),
        "trust_verdict_builder": SCORER_VERSION,
    }
    if integrity_assessment is not None:
        reason_codes = sorted(
            {*reason_codes, *(f"INTEGRITY_{code}" for code in integrity_assessment.reason_codes)}
        )
        action = _apply_integrity_action(action, integrity_assessment.action_hint)
        liquidity_risk_score = max(
            liquidity_risk_score,
            integrity_assessment.liquidity_anomaly_score,
            integrity_assessment.orderbook_structure_score,
        )
        manipulation_risk_score = max(
            manipulation_risk_score,
            integrity_assessment.manipulation_proxy_score,
        )
        price_integrity_score = min(
            price_integrity_score,
            100 - integrity_assessment.price_anomaly_score,
            100 - integrity_assessment.rule_price_coupling_score,
        )
        information_freshness_score = min(
            information_freshness_score,
            100 - integrity_assessment.freshness_risk_score,
            100 - integrity_assessment.data_quality_risk_score,
        )
        metadata["integrity"] = {
            "assessment_id": integrity_assessment.integrity_assessment_id,
            "action_hint": integrity_assessment.action_hint.value,
            "overall_risk_score": integrity_assessment.overall_risk_score,
            "price_anomaly_score": integrity_assessment.price_anomaly_score,
            "liquidity_anomaly_score": integrity_assessment.liquidity_anomaly_score,
            "freshness_risk_score": integrity_assessment.freshness_risk_score,
            "orderbook_structure_score": integrity_assessment.orderbook_structure_score,
            "rule_change_risk_score": integrity_assessment.rule_change_risk_score,
            "rule_price_coupling_score": integrity_assessment.rule_price_coupling_score,
            "data_quality_risk_score": integrity_assessment.data_quality_risk_score,
            "manipulation_proxy_score": integrity_assessment.manipulation_proxy_score,
        }
        metadata["score_convention"] = {
            "risk_scores": "higher_is_riskier",
            "price_integrity_score": "higher_is_better_reduced_by_integrity_risk",
            "information_freshness_score": "higher_is_better_reduced_by_integrity_risk",
        }
        model_versions["integrity_assessment"] = "integrity_signals_v1"

    if equivalence_assessments:
        metadata["equivalence"] = _equivalence_metadata(
            market.market_id,
            equivalence_assessments,
        )
        model_versions["equivalence_assessment"] = "equivalence_engine_v1"

    if divergence_assessments:
        metadata["divergence"] = _divergence_metadata(divergence_assessments)
        model_versions["divergence_assessment"] = "divergence_signals_v1"

    return TrustVerdict(
        verdict_id=_build_verdict_id(market.market_id, asof_timestamp, data_versions),
        market_id=market.market_id,
        asof_timestamp=asof_timestamp,
        price_integrity_score=price_integrity_score,
        resolution_risk_score=resolution_result.resolution_risk_score,
        liquidity_risk_score=liquidity_risk_score,
        cross_venue_consistency_score=100,
        information_freshness_score=information_freshness_score,
        manipulation_risk_score=manipulation_risk_score,
        action=action,
        reason_codes=reason_codes,
        source_refs=source_refs,
        model_versions=model_versions,
        data_versions=data_versions,
        metadata=metadata,
    )


def _score_liquidity(orderbook_snapshot: OrderBookSnapshot | None) -> tuple[int, list[str]]:
    if orderbook_snapshot is None:
        return 90, ["missing_orderbook_snapshot"]

    if not orderbook_snapshot.bids or not orderbook_snapshot.asks:
        return 80, ["empty_orderbook_side"]

    best_bid = max(level.price for level in orderbook_snapshot.bids)
    best_ask = min(level.price for level in orderbook_snapshot.asks)
    spread = best_ask - best_bid

    if _binary_style_price(best_bid) and _binary_style_price(best_ask) and spread > Decimal("0.10"):
        return 70, ["wide_binary_spread"]

    return 10, []


def _binary_style_price(price: Decimal) -> bool:
    return Decimal("0") <= price <= Decimal("1")


def _apply_integrity_action(
    action: VerdictAction,
    action_hint: IntegrityActionHint,
) -> VerdictAction:
    if action_hint == IntegrityActionHint.NO_TRADE:
        return VerdictAction.NO_TRADE
    if action_hint == IntegrityActionHint.MANUAL_REVIEW and action != VerdictAction.NO_TRADE:
        return VerdictAction.MANUAL_REVIEW
    if action_hint == IntegrityActionHint.PASSIVE_ONLY and action in {
        VerdictAction.ALLOW,
        VerdictAction.ALLOW_SMALLER_SIZE,
    }:
        return VerdictAction.PASSIVE_ONLY
    if action_hint == IntegrityActionHint.ALLOW_SMALLER_SIZE and action == VerdictAction.ALLOW:
        return VerdictAction.ALLOW_SMALLER_SIZE
    return action


def _source_refs(
    rule_snapshot: MarketRuleSnapshot | None, orderbook_snapshot: OrderBookSnapshot | None
) -> list[str]:
    refs: list[str] = []
    if rule_snapshot is not None:
        refs.append(f"rule_snapshot:{rule_snapshot.rule_snapshot_id}")
    if orderbook_snapshot is not None:
        refs.append(f"orderbook_snapshot:{orderbook_snapshot.snapshot_id}")
    return refs


def _equivalence_metadata(
    market_id: str,
    assessments: list[MarketEquivalenceAssessment],
) -> dict[str, Any]:
    comparable_permissions = {
        ComparisonPermission.COMPARABLE,
        ComparisonPermission.COMPARABLE_WITH_HAIRCUT,
    }
    comparable_ids: set[str] = set()
    manual_review_ids: set[str] = set()
    do_not_compare_ids: set[str] = set()
    assessment_ids: list[str] = []
    for assessment in assessments:
        assessment_ids.append(assessment.equivalence_assessment_id)
        other_market_id = (
            assessment.right_market_id
            if assessment.left_market_id == market_id
            else assessment.left_market_id
        )
        if assessment.comparison_permission in comparable_permissions:
            comparable_ids.add(other_market_id)
        elif assessment.comparison_permission == ComparisonPermission.MANUAL_REVIEW:
            manual_review_ids.add(other_market_id)
        elif assessment.comparison_permission == ComparisonPermission.DO_NOT_COMPARE:
            do_not_compare_ids.add(other_market_id)
    return {
        "comparable_market_count": len(comparable_ids),
        "manual_review_equivalence_count": len(manual_review_ids),
        "do_not_compare_equivalence_count": len(do_not_compare_ids),
        "latest_equivalence_assessment_ids": sorted(assessment_ids),
    }


def _divergence_metadata(
    assessments: list[CrossVenueDivergenceAssessment],
) -> dict[str, Any]:
    status_counts = {status.value: 0 for status in DivergenceStatus}
    max_score = 0
    assessment_ids: list[str] = []
    for assessment in assessments:
        assessment_ids.append(assessment.divergence_assessment_id)
        status_counts[assessment.status.value] = status_counts.get(
            assessment.status.value,
            0,
        ) + 1
        max_score = max(max_score, assessment.overall_divergence_score)
    return {
        "divergence_assessment_ids": sorted(assessment_ids),
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


def _build_verdict_id(
    market_id: str, asof_timestamp: datetime, data_versions: dict[str, Any]
) -> str:
    payload = {
        "asof_timestamp": asof_timestamp.isoformat(),
        "data_versions": data_versions,
        "market_id": market_id,
        "model_version": SCORER_VERSION,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()
    return f"verdict_{digest[:24]}"
