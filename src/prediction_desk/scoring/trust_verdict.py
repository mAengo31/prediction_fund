"""Build deterministic market trust verdicts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.domain.models import Market, MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.scoring.resolution_risk import score_resolution_risk

SCORER_VERSION = "trust_verdict_v0"


def build_trust_verdict(
    market: Market,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    asof_timestamp: datetime,
) -> TrustVerdict:
    resolution_result = score_resolution_risk(market, rule_snapshot)
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
    }

    return TrustVerdict(
        verdict_id=_build_verdict_id(market.market_id, asof_timestamp, data_versions),
        market_id=market.market_id,
        asof_timestamp=asof_timestamp,
        price_integrity_score=100 if orderbook_snapshot is not None else 50,
        resolution_risk_score=resolution_result.resolution_risk_score,
        liquidity_risk_score=liquidity_risk_score,
        cross_venue_consistency_score=100,
        information_freshness_score=100,
        manipulation_risk_score=0,
        action=action,
        reason_codes=reason_codes,
        source_refs=source_refs,
        model_versions={
            "liquidity_scorer": "liquidity_v0",
            "resolution_risk_scorer": "resolution_risk_v0",
            "trust_verdict_builder": SCORER_VERSION,
        },
        data_versions=data_versions,
        metadata={},
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


def _source_refs(
    rule_snapshot: MarketRuleSnapshot | None, orderbook_snapshot: OrderBookSnapshot | None
) -> list[str]:
    refs: list[str] = []
    if rule_snapshot is not None:
        refs.append(f"rule_snapshot:{rule_snapshot.rule_snapshot_id}")
    if orderbook_snapshot is not None:
        refs.append(f"orderbook_snapshot:{orderbook_snapshot.snapshot_id}")
    return refs


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
