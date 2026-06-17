"""Derive canonical market-data snapshots from stored orderbooks."""

from __future__ import annotations

from datetime import datetime

from prediction_desk.domain.models import Market, OrderBookSnapshot, Venue
from prediction_desk.marketdata.enums import MarketPriceSource
from prediction_desk.marketdata.liquidity import (
    best_ask,
    best_bid,
    book_imbalance,
    depth_at_price,
    mid_price,
    spread,
    spread_bps,
    total_depth,
)
from prediction_desk.marketdata.models import (
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
    compute_market_liquidity_hash,
    compute_market_price_hash,
)


def derive_price_snapshot_from_orderbook(
    market: Market,
    orderbook_snapshot: OrderBookSnapshot,
    venue: Venue,
    *,
    source_payload_id: str | None = None,
    observed_at: datetime | None = None,
    captured_at: datetime | None = None,
    available_at: datetime | None = None,
) -> MarketPriceSnapshot:
    observed = observed_at or orderbook_snapshot.captured_at
    captured = captured_at or orderbook_snapshot.captured_at
    available = available_at or captured
    bid = best_bid(orderbook_snapshot.bids)
    ask = best_ask(orderbook_snapshot.asks)
    mid = mid_price(bid, ask)
    spread_value = spread(bid, ask)
    snapshot = MarketPriceSnapshot(
        price_snapshot_id="pending",
        market_id=market.market_id,
        outcome_id=None,
        venue_id=venue.venue_id,
        venue_name=venue.name,
        source=MarketPriceSource.ORDERBOOK_DERIVED,
        observed_at=observed,
        captured_at=captured,
        available_at=available,
        price=mid,
        bid=bid,
        ask=ask,
        mid=mid,
        spread=spread_value,
        last_trade_price=None,
        volume=None,
        open_interest=None,
        source_payload_id=source_payload_id
        or orderbook_snapshot.metadata.get("source_payload_id"),
        orderbook_snapshot_id=orderbook_snapshot.snapshot_id,
        external_market_id=_external_market_id(market, orderbook_snapshot),
        external_outcome_id=None,
        data_hash="pending",
        metadata={"derivation": "orderbook_best_bid_ask_v1"},
    )
    data_hash = compute_market_price_hash(snapshot)
    return snapshot.model_copy(
        update={
            "price_snapshot_id": f"price_{data_hash[:24]}",
            "data_hash": data_hash,
        }
    )


def derive_liquidity_snapshot_from_orderbook(
    market: Market,
    orderbook_snapshot: OrderBookSnapshot,
    venue: Venue,
    *,
    source_payload_id: str | None = None,
    observed_at: datetime | None = None,
    captured_at: datetime | None = None,
    available_at: datetime | None = None,
) -> MarketLiquiditySnapshot:
    observed = observed_at or orderbook_snapshot.captured_at
    captured = captured_at or orderbook_snapshot.captured_at
    available = available_at or captured
    bid = best_bid(orderbook_snapshot.bids)
    ask = best_ask(orderbook_snapshot.asks)
    mid = mid_price(bid, ask)
    spread_value = spread(bid, ask)
    bid_depth = depth_at_price(orderbook_snapshot.bids, bid)
    ask_depth = depth_at_price(orderbook_snapshot.asks, ask)
    total_bid = total_depth(orderbook_snapshot.bids)
    total_ask = total_depth(orderbook_snapshot.asks)
    snapshot = MarketLiquiditySnapshot(
        liquidity_snapshot_id="pending",
        market_id=market.market_id,
        venue_id=venue.venue_id,
        venue_name=venue.name,
        observed_at=observed,
        captured_at=captured,
        available_at=available,
        best_bid=bid,
        best_ask=ask,
        mid_price=mid,
        spread=spread_value,
        spread_bps=spread_bps(spread_value, mid),
        bid_depth=bid_depth,
        ask_depth=ask_depth,
        total_bid_depth=total_bid,
        total_ask_depth=total_ask,
        book_imbalance=book_imbalance(total_bid, total_ask),
        is_empty_book=not orderbook_snapshot.bids and not orderbook_snapshot.asks,
        is_crossed_book=bid is not None and ask is not None and bid > ask,
        source_payload_id=source_payload_id
        or orderbook_snapshot.metadata.get("source_payload_id"),
        orderbook_snapshot_id=orderbook_snapshot.snapshot_id,
        data_hash="pending",
        metadata={"derivation": "orderbook_liquidity_v1"},
    )
    data_hash = compute_market_liquidity_hash(snapshot)
    return snapshot.model_copy(
        update={
            "liquidity_snapshot_id": f"liquidity_{data_hash[:24]}",
            "data_hash": data_hash,
        }
    )


def _external_market_id(market: Market, orderbook_snapshot: OrderBookSnapshot) -> str | None:
    for source in (orderbook_snapshot.metadata, market.metadata):
        for key in ("external_market_id", "ticker", "condition_id"):
            value = source.get(key)
            if value is not None:
                return str(value)
    return None
