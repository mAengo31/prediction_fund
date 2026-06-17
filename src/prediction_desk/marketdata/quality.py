"""Market-data quality scoring."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.models import MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.ingestion.models import VenueMarketMapping
from prediction_desk.marketdata.enums import MarketDataQualitySeverity
from prediction_desk.marketdata.models import (
    MarketDataQualityReport,
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
)


def build_quality_report(
    *,
    market_id: str,
    asof_timestamp: datetime,
    created_at: datetime,
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
    rule_snapshot: MarketRuleSnapshot | None,
    venue_mapping: VenueMarketMapping | None,
    freshness_threshold_seconds: int,
    wide_spread_threshold: Decimal,
) -> MarketDataQualityReport:
    reason_codes: list[str] = []
    freshness_seconds = _freshness_seconds(asof_timestamp, price_snapshot, liquidity_snapshot)
    future_available_at = freshness_seconds is not None and freshness_seconds < 0
    has_recent_price = price_snapshot is not None and (
        freshness_seconds is None
        or (0 <= freshness_seconds <= freshness_threshold_seconds)
    )
    has_recent_orderbook = orderbook_snapshot is not None and (
        liquidity_snapshot is not None
        and freshness_seconds is not None
        and 0 <= freshness_seconds <= freshness_threshold_seconds
    )
    stale_market_data = (
        freshness_seconds is None
        or freshness_seconds > freshness_threshold_seconds
        or future_available_at
    )
    crossed_book = liquidity_snapshot.is_crossed_book if liquidity_snapshot else False
    empty_book = liquidity_snapshot.is_empty_book if liquidity_snapshot else False
    spread = liquidity_snapshot.spread if liquidity_snapshot else None
    wide_spread = spread is not None and spread > wide_spread_threshold
    missing_bid_or_ask = (
        liquidity_snapshot is not None
        and (liquidity_snapshot.best_bid is None or liquidity_snapshot.best_ask is None)
    )
    out_of_bounds_price = _out_of_bounds(price_snapshot)

    if price_snapshot is None:
        reason_codes.append("NO_PRICE_SNAPSHOT")
    if orderbook_snapshot is None:
        reason_codes.append("NO_ORDERBOOK_SNAPSHOT")
    if rule_snapshot is None:
        reason_codes.append("NO_RULE_SNAPSHOT")
    if venue_mapping is None:
        reason_codes.append("NO_VENUE_MAPPING")
    if stale_market_data:
        reason_codes.append("STALE_MARKET_DATA")
    if future_available_at:
        reason_codes.append("FUTURE_AVAILABLE_AT")
    if crossed_book:
        reason_codes.append("CROSSED_BOOK")
    if empty_book:
        reason_codes.append("EMPTY_BOOK")
    if wide_spread:
        reason_codes.append("WIDE_SPREAD")
    if out_of_bounds_price:
        reason_codes.append("OUT_OF_BOUNDS_PRICE")
    if missing_bid_or_ask:
        reason_codes.append("MISSING_BID_OR_ASK")

    score = 100
    penalties = {
        "NO_PRICE_SNAPSHOT": 30,
        "NO_ORDERBOOK_SNAPSHOT": 25,
        "NO_RULE_SNAPSHOT": 15,
        "NO_VENUE_MAPPING": 10,
        "STALE_MARKET_DATA": 25,
        "FUTURE_AVAILABLE_AT": 40,
        "CROSSED_BOOK": 35,
        "EMPTY_BOOK": 35,
        "WIDE_SPREAD": 15,
        "OUT_OF_BOUNDS_PRICE": 40,
        "MISSING_BID_OR_ASK": 20,
    }
    for code in reason_codes:
        score -= penalties.get(code, 0)
    quality_score = max(0, min(100, score))
    severity = _severity(quality_score, reason_codes)
    return MarketDataQualityReport(
        quality_report_id=f"quality_{market_id}_{asof_timestamp.isoformat()}",
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        created_at=created_at,
        latest_price_snapshot_id=price_snapshot.price_snapshot_id if price_snapshot else None,
        latest_liquidity_snapshot_id=(
            liquidity_snapshot.liquidity_snapshot_id if liquidity_snapshot else None
        ),
        latest_orderbook_snapshot_id=orderbook_snapshot.snapshot_id if orderbook_snapshot else None,
        latest_rule_snapshot_id=rule_snapshot.rule_snapshot_id if rule_snapshot else None,
        freshness_seconds=freshness_seconds,
        quality_score=quality_score,
        severity=severity,
        has_recent_price=has_recent_price,
        has_recent_orderbook=has_recent_orderbook,
        has_rule_snapshot=rule_snapshot is not None,
        has_venue_mapping=venue_mapping is not None,
        stale_market_data=stale_market_data,
        crossed_book=crossed_book,
        empty_book=empty_book,
        wide_spread=wide_spread,
        out_of_bounds_price=out_of_bounds_price,
        missing_bid_or_ask=missing_bid_or_ask,
        reason_codes=reason_codes,
        metadata={
            "freshness_threshold_seconds": freshness_threshold_seconds,
            "wide_spread_threshold": str(wide_spread_threshold),
        },
    )


def _freshness_seconds(
    asof_timestamp: datetime,
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
) -> int | None:
    asof = _as_utc(asof_timestamp)
    candidates = [
        _as_utc(snapshot.available_at)
        for snapshot in (price_snapshot, liquidity_snapshot)
        if snapshot is not None
    ]
    if not candidates:
        return None
    latest = max(candidates)
    return int((asof - latest).total_seconds())


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _out_of_bounds(price_snapshot: MarketPriceSnapshot | None) -> bool:
    if price_snapshot is None:
        return False
    values = [
        price_snapshot.price,
        price_snapshot.bid,
        price_snapshot.ask,
        price_snapshot.mid,
        price_snapshot.last_trade_price,
    ]
    return any(
        value is not None and (value < Decimal("0") or value > Decimal("1"))
        for value in values
    )


def _severity(score: int, reason_codes: list[str]) -> MarketDataQualitySeverity:
    if not reason_codes:
        return MarketDataQualitySeverity.OK
    if score < 50 or any(
        code in reason_codes
        for code in (
            "NO_PRICE_SNAPSHOT",
            "CROSSED_BOOK",
            "EMPTY_BOOK",
            "OUT_OF_BOUNDS_PRICE",
            "FUTURE_AVAILABLE_AT",
        )
    ):
        return MarketDataQualitySeverity.ERROR
    return MarketDataQualitySeverity.WARNING
