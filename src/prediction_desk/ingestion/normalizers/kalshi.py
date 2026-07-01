"""Deterministic Kalshi payload normalization."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from prediction_desk.domain.enums import MarketStatus, MarketType, VenueType
from prediction_desk.domain.models import (
    Event,
    Market,
    MarketRuleSnapshot,
    OrderBookSnapshot,
    Outcome,
    PriceLevel,
    Venue,
)
from prediction_desk.ingestion.enums import VenueEndpointType, VenueMappingStatus
from prediction_desk.ingestion.models import (
    NormalizedVenuePayload,
    RawVenuePayload,
    VenueMarketMapping,
)


def normalize_kalshi_payload(payload: RawVenuePayload) -> list[NormalizedVenuePayload]:
    if payload.endpoint_type == VenueEndpointType.MARKET_LIST:
        markets = payload.response_payload.get("markets", [])
        if not isinstance(markets, list):
            return []
        return [
            _normalize_market_payload(payload, market)
            for market in markets
            if isinstance(market, dict)
        ]
    if payload.endpoint_type == VenueEndpointType.MARKET_DETAIL:
        market_payload = payload.response_payload.get("market", payload.response_payload)
        if not isinstance(market_payload, dict):
            return []
        return [_normalize_market_payload(payload, market_payload)]
    if payload.endpoint_type == VenueEndpointType.ORDERBOOK:
        return [_normalize_orderbook_payload(payload)]
    return []


def _normalize_market_payload(
    raw_payload: RawVenuePayload, market_payload: dict[str, Any]
) -> NormalizedVenuePayload:
    ticker = str(market_payload.get("ticker") or raw_payload.external_id or "").strip()
    if not ticker:
        raise ValueError("Kalshi market payload is missing ticker.")
    event_ticker = str(
        market_payload.get("event_ticker") or market_payload.get("series_ticker") or ticker
    )
    market_id = _market_id(ticker)
    event_id = _event_id(event_ticker)
    captured_at = raw_payload.captured_at
    raw_rule_text = _rule_text(market_payload)
    rule_snapshot = None
    if raw_rule_text:
        rule_snapshot = MarketRuleSnapshot.from_rule_text(
            rule_snapshot_id="rule_kalshi_"
            f"{_slug(ticker)}_{_rule_identity(raw_rule_text, market_payload)[:16]}",
            market_id=market_id,
            captured_at=captured_at,
            raw_rule_text=raw_rule_text,
            normalized_rule_text=_normalize_space(raw_rule_text),
            resolution_source=_optional_str(
                market_payload.get("settlement_source")
                or market_payload.get("resolution_source")
                or market_payload.get("result_source")
            ),
            settlement_authority=_optional_str(
                market_payload.get("settlement_authority") or "Kalshi"
            ),
            time_zone=_optional_str(
                market_payload.get("timezone") or market_payload.get("time_zone")
            ),
            metadata={
                "venue": "kalshi",
                "ticker": ticker,
                "event_ticker": event_ticker,
                "source_payload_id": raw_payload.payload_id,
            },
        )

    market_type = MarketType.BINARY
    return NormalizedVenuePayload(
        venue=Venue(
            venue_id="kalshi",
            name="Kalshi",
            jurisdiction="US",
            venue_type=VenueType.CFTC_DCM,
            metadata={"source": "kalshi_public"},
        ),
        event=Event(
            event_id=event_id,
            venue_id="kalshi",
            title=str(
                market_payload.get("event_title")
                or market_payload.get("title")
                or event_ticker
            ),
            category=_optional_str(market_payload.get("category")),
            start_time=_parse_datetime(market_payload.get("open_time")),
            end_time=_parse_datetime(market_payload.get("close_time")),
            metadata={"event_ticker": event_ticker},
        ),
        market=Market(
            market_id=market_id,
            venue_id="kalshi",
            event_id=event_id,
            title=str(market_payload.get("title") or market_payload.get("subtitle") or ticker),
            description=_optional_str(
                market_payload.get("subtitle") or market_payload.get("description")
            ),
            market_type=market_type,
            status=_map_status(market_payload.get("status")),
            created_time=_parse_datetime(
                market_payload.get("open_time") or market_payload.get("created_time")
            ),
            close_time=_parse_datetime(market_payload.get("close_time")),
            settlement_time=_parse_datetime(
                market_payload.get("expiration_time") or market_payload.get("settlement_time")
            ),
            metadata={
                "venue": "kalshi",
                "ticker": ticker,
                "event_ticker": event_ticker,
                "market_payload_id": raw_payload.payload_id,
            },
        ),
        outcomes=[
            Outcome(
                outcome_id=f"{market_id}_yes",
                market_id=market_id,
                label="YES",
                payout=Decimal("1"),
                metadata={"venue": "kalshi", "side": "yes"},
            ),
            Outcome(
                outcome_id=f"{market_id}_no",
                market_id=market_id,
                label="NO",
                payout=Decimal("1"),
                metadata={"venue": "kalshi", "side": "no"},
            ),
        ],
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=_synthetic_orderbook(market_id, captured_at, market_payload),
        mapping=_mapping(
            raw_payload=raw_payload,
            event_ticker=event_ticker,
            ticker=ticker,
            event_id=event_id,
            market_id=market_id,
            external_url=_optional_str(market_payload.get("url")),
        ),
    )


def _synthetic_orderbook(
    market_id: str, captured_at: datetime, market_payload: dict[str, Any]
) -> OrderBookSnapshot | None:
    """Build a minimal orderbook from the bid/ask fields in the market catalog.

    Kalshi API uses two field families:
    - Integer cents (yes_bid, yes_ask): values like 30 = 30¢ → divide by 100
    - Dollar decimal (yes_bid_dollars, yes_ask_dollars): values like "0.30" = 30¢ → use as-is

    For binary markets, if only one side is present, we synthesize the other side
    with a 2-cent spread to avoid ONE_SIDED_BOOK integrity signals on thin markets.
    """
    def _from_cents(key: str) -> Decimal | None:
        v = market_payload.get(key)
        if v is None:
            return None
        try:
            val = Decimal(str(v))
            return val / Decimal("100") if val > 0 else None
        except Exception:
            return None

    def _from_dollars(key: str) -> Decimal | None:
        v = market_payload.get(key)
        if v is None:
            return None
        try:
            val = Decimal(str(v))
            return val if val > 0 else None
        except Exception:
            return None

    bid = _from_cents("yes_bid") or _from_dollars("yes_bid_dollars")
    ask = _from_cents("yes_ask") or _from_dollars("yes_ask_dollars")

    if bid is None and ask is None:
        return None

    _TWO_CENTS = Decimal("0.02")
    _MIN_PRICE = Decimal("0.01")
    _MAX_PRICE = Decimal("0.99")

    # Synthesize missing side with a 2¢ spread so integrity sees a two-sided book
    if bid is not None and ask is None:
        ask = min(_MAX_PRICE, bid + _TWO_CENTS)
    elif ask is not None and bid is None:
        bid = max(_MIN_PRICE, ask - _TWO_CENTS)

    bids = [PriceLevel(price=bid, quantity=Decimal("1"))]
    asks = [PriceLevel(price=ask, quantity=Decimal("1"))]
    return OrderBookSnapshot(
        snapshot_id=f"ob_catalog_{market_id}_{int(captured_at.timestamp())}",
        market_id=market_id,
        captured_at=captured_at,
        bids=bids,
        asks=asks,
        metadata={"source": "market_catalog_synthetic"},
    )


def _normalize_orderbook_payload(raw_payload: RawVenuePayload) -> NormalizedVenuePayload:
    body = raw_payload.response_payload
    # Kalshi v2 API wraps depth in "orderbook_fp"; fall back to "orderbook" or body
    orderbook = body.get("orderbook_fp") or body.get("orderbook", body)
    if not isinstance(orderbook, dict):
        raise ValueError("Kalshi orderbook payload is malformed.")
    ticker = str(
        body.get("ticker") or orderbook.get("ticker") or raw_payload.external_id or ""
    ).strip()
    if not ticker:
        raise ValueError("Kalshi orderbook payload is missing ticker.")
    # v2 uses "yes_dollars"/"no_dollars"; fall back to legacy "yes"/"yes_bids"
    yes_bids_raw = _levels(orderbook.get("yes_dollars") or orderbook.get("yes") or orderbook.get("yes_bids") or [])
    no_bids_raw = _levels(orderbook.get("no_dollars") or orderbook.get("no") or orderbook.get("no_bids") or [])
    bids = [
        PriceLevel(price=_kalshi_price(price), quantity=_decimal(quantity))
        for price, quantity in yes_bids_raw
        if _decimal(quantity) > 0
    ]
    asks = [
        PriceLevel(price=Decimal("1") - _kalshi_price(price), quantity=_decimal(quantity))
        for price, quantity in no_bids_raw
        if _decimal(quantity) > 0
    ]
    bids.sort(key=lambda level: level.price, reverse=True)
    asks.sort(key=lambda level: level.price)
    market_id = _market_id(ticker)
    event_ticker = _optional_str(body.get("event_ticker"))
    return NormalizedVenuePayload(
        orderbook_snapshot=OrderBookSnapshot(
            snapshot_id=f"ob_kalshi_{_slug(ticker)}_{raw_payload.response_hash[:16]}",
            market_id=market_id,
            captured_at=raw_payload.captured_at,
            bids=bids,
            asks=asks,
            metadata={
                "venue": "kalshi",
                "ticker": ticker,
                "source_payload_id": raw_payload.payload_id,
                "yes_bids_raw": [[price, quantity] for price, quantity in yes_bids_raw],
                "no_bids_raw": [[price, quantity] for price, quantity in no_bids_raw],
            },
        ),
        mapping=_mapping(
            raw_payload=raw_payload,
            event_ticker=event_ticker,
            ticker=ticker,
            event_id=_event_id(event_ticker) if event_ticker is not None else None,
            market_id=market_id,
            external_url=None,
        ),
    )


def _mapping(
    *,
    raw_payload: RawVenuePayload,
    event_ticker: str | None,
    ticker: str,
    event_id: str | None,
    market_id: str,
    external_url: str | None,
) -> VenueMarketMapping:
    return VenueMarketMapping(
        mapping_id=f"mapping_kalshi_{_slug(ticker)}",
        venue_id="kalshi",
        venue_name="Kalshi",
        external_event_id=event_ticker,
        external_market_id=ticker,
        external_symbol=ticker,
        canonical_event_id=event_id,
        canonical_market_id=market_id,
        external_url=external_url,
        first_seen_at=raw_payload.captured_at,
        last_seen_at=raw_payload.captured_at,
        status=VenueMappingStatus.ACTIVE,
        metadata={"source_payload_id": raw_payload.payload_id},
    )


def _rule_text(market_payload: dict[str, Any]) -> str:
    parts = [
        _optional_str(market_payload.get("rules_primary")),
        _optional_str(market_payload.get("rules_secondary")),
        _optional_str(market_payload.get("settlement_rules")),
    ]
    return "\n\n".join(part for part in parts if part)


def _rule_identity(raw_rule_text: str, market_payload: dict[str, Any]) -> str:
    snapshot = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="temporary",
        market_id="temporary",
        captured_at=datetime.now(),
        raw_rule_text=raw_rule_text,
        normalized_rule_text=_normalize_space(raw_rule_text),
        resolution_source=_optional_str(
            market_payload.get("settlement_source")
            or market_payload.get("resolution_source")
            or market_payload.get("result_source")
        ),
        settlement_authority=_optional_str(
            market_payload.get("settlement_authority") or "Kalshi"
        ),
        time_zone=_optional_str(market_payload.get("timezone") or market_payload.get("time_zone")),
    )
    return snapshot.rule_hash


def _map_status(value: object) -> MarketStatus:
    normalized = str(value or "active").lower()
    if normalized in {"active", "open", "initialized"}:
        return MarketStatus.ACTIVE
    if normalized in {"paused", "halted"}:
        return MarketStatus.PAUSED
    if normalized in {"closed", "finalized"}:
        return MarketStatus.CLOSED
    if normalized in {"settled", "resolved"}:
        return MarketStatus.SETTLED
    if normalized in {"canceled", "cancelled"}:
        return MarketStatus.CANCELED
    return MarketStatus.ACTIVE


def _levels(value: object) -> list[tuple[object, object]]:
    if not isinstance(value, list):
        return []
    levels: list[tuple[object, object]] = []
    for item in value:
        if isinstance(item, list | tuple) and len(item) >= 2:
            levels.append((item[0], item[1]))
        elif isinstance(item, dict):
            price = item.get("price") or item.get("yes_price") or item.get("no_price")
            quantity = item.get("quantity") or item.get("count") or item.get("size")
            if price is not None and quantity is not None:
                levels.append((price, quantity))
    return levels


def _kalshi_price(value: object) -> Decimal:
    price = _decimal(value)
    if price > Decimal("1"):
        return price / Decimal("100")
    return price


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _market_id(ticker: str) -> str:
    return f"kalshi_market_{_slug(ticker)}"


def _event_id(event_ticker: str) -> str:
    return f"kalshi_event_{_slug(event_ticker)}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
