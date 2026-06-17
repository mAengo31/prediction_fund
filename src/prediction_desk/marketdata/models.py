"""Pydantic models for canonical market-data snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prediction_desk.marketdata.enums import (
    MarketDataQualitySeverity,
    MarketPriceSource,
)


class MarketDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketPriceSnapshot(MarketDataModel):
    price_snapshot_id: str
    market_id: str
    outcome_id: str | None = None
    venue_id: str
    venue_name: str
    source: MarketPriceSource
    observed_at: datetime
    captured_at: datetime
    available_at: datetime
    price: Decimal | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal | None = None
    spread: Decimal | None = None
    last_trade_price: Decimal | None = None
    volume: Decimal | None = None
    open_interest: Decimal | None = None
    source_payload_id: str | None = None
    orderbook_snapshot_id: str | None = None
    external_market_id: str | None = None
    external_outcome_id: str | None = None
    data_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketLiquiditySnapshot(MarketDataModel):
    liquidity_snapshot_id: str
    market_id: str
    venue_id: str
    venue_name: str
    observed_at: datetime
    captured_at: datetime
    available_at: datetime
    best_bid: Decimal | None = None
    best_ask: Decimal | None = None
    mid_price: Decimal | None = None
    spread: Decimal | None = None
    spread_bps: Decimal | None = None
    bid_depth: Decimal = Decimal("0")
    ask_depth: Decimal = Decimal("0")
    total_bid_depth: Decimal = Decimal("0")
    total_ask_depth: Decimal = Decimal("0")
    book_imbalance: Decimal | None = None
    is_empty_book: bool
    is_crossed_book: bool
    source_payload_id: str | None = None
    orderbook_snapshot_id: str | None = None
    data_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketDataQualityReport(MarketDataModel):
    quality_report_id: str
    market_id: str
    asof_timestamp: datetime
    created_at: datetime
    latest_price_snapshot_id: str | None = None
    latest_liquidity_snapshot_id: str | None = None
    latest_orderbook_snapshot_id: str | None = None
    latest_rule_snapshot_id: str | None = None
    freshness_seconds: int | None = None
    quality_score: int = Field(ge=0, le=100)
    severity: MarketDataQualitySeverity
    has_recent_price: bool
    has_recent_orderbook: bool
    has_rule_snapshot: bool
    has_venue_mapping: bool
    stale_market_data: bool
    crossed_book: bool
    empty_book: bool
    wide_spread: bool
    out_of_bounds_price: bool
    missing_bid_or_ask: bool
    reason_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketDataLatest(MarketDataModel):
    market_id: str
    asof_timestamp: datetime
    price_snapshot: MarketPriceSnapshot | None = None
    liquidity_snapshot: MarketLiquiditySnapshot | None = None
    quality_report: MarketDataQualityReport | None = None


class DataQualityRequest(MarketDataModel):
    asof_timestamp: datetime | None = None
    freshness_threshold_seconds: int = Field(default=3600, gt=0)
    wide_spread_threshold: Decimal = Decimal("0.10")


class MarketDataDerivationResult(MarketDataModel):
    market_id: str | None = None
    price_snapshots_created: int = 0
    liquidity_snapshots_created: int = 0
    quality_reports_created: int = 0
    price_snapshots: list[MarketPriceSnapshot] = Field(default_factory=list)
    liquidity_snapshots: list[MarketLiquiditySnapshot] = Field(default_factory=list)
    quality_reports: list[MarketDataQualityReport] = Field(default_factory=list)


def compute_market_price_hash(snapshot: MarketPriceSnapshot) -> str:
    return _hash_payload(
        {
            "ask": snapshot.ask,
            "available_at": snapshot.available_at,
            "bid": snapshot.bid,
            "captured_at": snapshot.captured_at,
            "external_market_id": snapshot.external_market_id,
            "external_outcome_id": snapshot.external_outcome_id,
            "last_trade_price": snapshot.last_trade_price,
            "market_id": snapshot.market_id,
            "mid": snapshot.mid,
            "observed_at": snapshot.observed_at,
            "open_interest": snapshot.open_interest,
            "orderbook_snapshot_id": snapshot.orderbook_snapshot_id,
            "outcome_id": snapshot.outcome_id,
            "price": snapshot.price,
            "source": snapshot.source.value,
            "source_payload_id": snapshot.source_payload_id,
            "spread": snapshot.spread,
            "venue_id": snapshot.venue_id,
            "venue_name": snapshot.venue_name,
            "volume": snapshot.volume,
        }
    )


def compute_market_liquidity_hash(snapshot: MarketLiquiditySnapshot) -> str:
    return _hash_payload(
        {
            "available_at": snapshot.available_at,
            "ask_depth": snapshot.ask_depth,
            "best_ask": snapshot.best_ask,
            "best_bid": snapshot.best_bid,
            "bid_depth": snapshot.bid_depth,
            "book_imbalance": snapshot.book_imbalance,
            "captured_at": snapshot.captured_at,
            "is_crossed_book": snapshot.is_crossed_book,
            "is_empty_book": snapshot.is_empty_book,
            "market_id": snapshot.market_id,
            "mid_price": snapshot.mid_price,
            "observed_at": snapshot.observed_at,
            "orderbook_snapshot_id": snapshot.orderbook_snapshot_id,
            "source_payload_id": snapshot.source_payload_id,
            "spread": snapshot.spread,
            "spread_bps": snapshot.spread_bps,
            "total_ask_depth": snapshot.total_ask_depth,
            "total_bid_depth": snapshot.total_bid_depth,
            "venue_id": snapshot.venue_id,
            "venue_name": snapshot.venue_name,
        }
    )


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _json_safe(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value
