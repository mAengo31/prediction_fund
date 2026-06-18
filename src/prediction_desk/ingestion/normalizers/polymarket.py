"""Deterministic Polymarket payload normalization."""

from __future__ import annotations

import json
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
from prediction_desk.ingestion.enums import (
    VenueEndpointType,
    VenueMappingStatus,
    VenueOutcomeTokenSide,
    VenueOutcomeTokenStatus,
)
from prediction_desk.ingestion.models import (
    NormalizedVenuePayload,
    RawVenuePayload,
    VenueMarketMapping,
    VenueOutcomeTokenMapping,
)
from prediction_desk.marketdata.enums import MarketPriceSource
from prediction_desk.marketdata.models import MarketPriceSnapshot, compute_market_price_hash


def normalize_polymarket_payload(payload: RawVenuePayload) -> list[NormalizedVenuePayload]:
    if payload.endpoint_type == VenueEndpointType.MARKET_LIST:
        markets = payload.response_payload.get("markets", payload.response_payload.get("data", []))
        if not isinstance(markets, list):
            return []
        return [
            _normalize_market_payload(payload, market)
            for market in markets
            if isinstance(market, dict)
        ]
    if payload.endpoint_type in {VenueEndpointType.MARKET_DETAIL, VenueEndpointType.EVENT_DETAIL}:
        market_payload = payload.response_payload.get("market", payload.response_payload)
        if not isinstance(market_payload, dict):
            return []
        return [_normalize_market_payload(payload, market_payload)]
    if payload.endpoint_type == VenueEndpointType.ORDERBOOK:
        return [_normalize_orderbook_payload(payload)]
    if payload.endpoint_type == VenueEndpointType.PRICE_HISTORY:
        return [_normalize_price_history_payload(payload)]
    return []


def _normalize_market_payload(
    raw_payload: RawVenuePayload, market_payload: dict[str, Any]
) -> NormalizedVenuePayload:
    external_market_id = _external_market_id(market_payload, raw_payload)
    condition_id = _optional_str(
        market_payload.get("conditionId") or market_payload.get("condition_id")
    )
    question_id = _optional_str(
        market_payload.get("questionID") or market_payload.get("question_id")
    )
    gamma_market_id = _optional_str(
        market_payload.get("id") or market_payload.get("gamma_market_id")
    )
    gamma_event_id = _optional_str(
        market_payload.get("eventId")
        or market_payload.get("event_id")
        or market_payload.get("gamma_event_id")
    )
    market_address = _optional_str(
        market_payload.get("marketMakerAddress")
        or market_payload.get("market_address")
        or market_payload.get("marketAddress")
    )
    enable_orderbook = _optional_bool(
        _first_present(market_payload, "enableOrderBook", "enable_orderbook")
    )
    event_external_id = _optional_str(
        gamma_event_id
        or market_payload.get("slug")
    )
    market_id = _market_id(condition_id or external_market_id)
    event_id = _event_id(event_external_id or condition_id or external_market_id)
    outcome_labels = _outcome_labels(market_payload)
    token_ids = _token_ids(market_payload)
    market_type = MarketType.BINARY if len(outcome_labels) <= 2 else MarketType.MULTI_OUTCOME
    raw_rule_text = _rule_text(market_payload)
    rule_snapshot = None
    if raw_rule_text:
        rule_snapshot = MarketRuleSnapshot.from_rule_text(
            rule_snapshot_id="rule_polymarket_"
            f"{_slug(condition_id or external_market_id)}_"
            f"{_rule_identity(raw_rule_text, market_payload)[:16]}",
            market_id=market_id,
            captured_at=raw_payload.captured_at,
            raw_rule_text=raw_rule_text,
            normalized_rule_text=_normalize_space(raw_rule_text),
            resolution_source=_optional_str(
                market_payload.get("resolutionSource")
                or market_payload.get("resolution_source")
                or market_payload.get("resolution_source_url")
            ),
            settlement_authority=_optional_str(
                market_payload.get("settlementAuthority")
                or market_payload.get("settlement_authority")
                or "Polymarket"
            ),
            time_zone=_optional_str(
                market_payload.get("timezone") or market_payload.get("time_zone")
            ),
            metadata={
                "venue": "polymarket",
                "condition_id": condition_id,
                "question_id": question_id,
                "gamma_market_id": gamma_market_id,
                "gamma_event_id": gamma_event_id,
                "token_ids": token_ids,
                "enable_orderbook": enable_orderbook,
                "source_payload_id": raw_payload.payload_id,
            },
        )

    return NormalizedVenuePayload(
        venue=Venue(
            venue_id="polymarket",
            name="Polymarket",
            jurisdiction=None,
            venue_type=VenueType.CRYPTO_CLOB,
            metadata={"source": "polymarket_public"},
        ),
        event=Event(
            event_id=event_id,
            venue_id="polymarket",
            title=str(
                market_payload.get("eventTitle")
                or market_payload.get("event_title")
                or market_payload.get("question")
                or external_market_id
            ),
            category=_optional_str(market_payload.get("category")),
            start_time=_parse_datetime(
                market_payload.get("startDate") or market_payload.get("start_date")
            ),
            end_time=_parse_datetime(
                market_payload.get("endDate") or market_payload.get("end_date")
            ),
            metadata={
                "external_event_id": event_external_id,
                "gamma_event_id": gamma_event_id,
            },
        ),
        market=Market(
            market_id=market_id,
            venue_id="polymarket",
            event_id=event_id,
            title=str(
                market_payload.get("question")
                or market_payload.get("title")
                or external_market_id
            ),
            description=_optional_str(market_payload.get("description")),
            market_type=market_type,
            status=_map_status(market_payload),
            created_time=_parse_datetime(
                market_payload.get("createdAt") or market_payload.get("created_at")
            ),
            close_time=_parse_datetime(
                market_payload.get("endDate") or market_payload.get("end_date")
            ),
            settlement_time=_parse_datetime(
                market_payload.get("resolvedAt") or market_payload.get("resolved_at")
            ),
            metadata={
                "venue": "polymarket",
                "external_market_id": external_market_id,
                "condition_id": condition_id,
                "question_id": question_id,
                "gamma_market_id": gamma_market_id,
                "gamma_event_id": gamma_event_id,
                "market_address": market_address,
                "enable_orderbook": enable_orderbook,
                "token_ids": token_ids,
                "source_payload_id": raw_payload.payload_id,
            },
        ),
        outcomes=[
            Outcome(
                outcome_id=f"{market_id}_{_slug(label)}",
                market_id=market_id,
                label=label,
                payout=Decimal("1"),
                metadata={
                    "venue": "polymarket",
                    "token_id": token_ids[index] if index < len(token_ids) else None,
                    "asset_id": token_ids[index] if index < len(token_ids) else None,
                    "token_side": _token_side(label).value,
                },
            )
            for index, label in enumerate(outcome_labels)
        ],
        rule_snapshot=rule_snapshot,
        mapping=_mapping(
            raw_payload=raw_payload,
            external_event_id=event_external_id,
            external_market_id=external_market_id,
            external_symbol=condition_id,
            event_id=event_id,
            market_id=market_id,
            external_url=_optional_str(market_payload.get("url") or market_payload.get("slug")),
            metadata={
                "condition_id": condition_id,
                "question_id": question_id,
                "gamma_market_id": gamma_market_id,
                "gamma_event_id": gamma_event_id,
                "market_address": market_address,
                "enable_orderbook": enable_orderbook,
                "token_ids": token_ids,
                "outcome_labels": outcome_labels,
            },
        ),
        outcome_token_mappings=_outcome_token_mappings(
            raw_payload=raw_payload,
            market_id=market_id,
            outcome_labels=outcome_labels,
            token_ids=token_ids,
            external_market_id=external_market_id,
            condition_id=condition_id,
            question_id=question_id,
            gamma_market_id=gamma_market_id,
            gamma_event_id=gamma_event_id,
            market_address=market_address,
            enable_orderbook=enable_orderbook,
        ),
    )


def _normalize_orderbook_payload(raw_payload: RawVenuePayload) -> NormalizedVenuePayload:
    body = raw_payload.response_payload
    metadata = raw_payload.metadata
    condition_id = _optional_str(
        metadata.get("condition_id") or body.get("condition_id") or body.get("conditionId")
    )
    token_id = _optional_str(
        metadata.get("token_id")
        or metadata.get("asset_id")
        or body.get("asset_id")
        or body.get("token_id")
        or raw_payload.request_params.get("token_id")
    )
    external_market_id = str(
        condition_id
        or metadata.get("external_market_id")
        or body.get("market")
        or body.get("market_id")
        or token_id
        or raw_payload.external_id
        or ""
    ).strip()
    if not external_market_id:
        raise ValueError("Polymarket orderbook payload is missing market identifier.")
    market_id = _optional_str(metadata.get("canonical_market_id")) or _market_id(external_market_id)
    bids = [
        PriceLevel(price=_price(price), quantity=_decimal(size))
        for price, size in _levels(body.get("bids", []))
        if _decimal(size) > 0
    ]
    asks = [
        PriceLevel(price=_price(price), quantity=_decimal(size))
        for price, size in _levels(body.get("asks", []))
        if _decimal(size) > 0
    ]
    bids.sort(key=lambda level: level.price, reverse=True)
    asks.sort(key=lambda level: level.price)
    return NormalizedVenuePayload(
        orderbook_snapshot=OrderBookSnapshot(
            snapshot_id=(
                f"ob_polymarket_{_slug(external_market_id)}_"
                f"{_slug(token_id or 'unknown')}_{raw_payload.response_hash[:16]}"
            ),
            market_id=market_id,
            captured_at=raw_payload.captured_at,
            bids=bids,
            asks=asks,
            metadata={
                "venue": "polymarket",
                "condition_id": condition_id,
                "token_id": token_id,
                "asset_id": token_id,
                "source_payload_id": raw_payload.payload_id,
                "bids_raw": body.get("bids", []),
                "asks_raw": body.get("asks", []),
            },
        ),
        mapping=_mapping(
            raw_payload=raw_payload,
            external_event_id=None,
            external_market_id=external_market_id,
            external_symbol=condition_id,
            event_id=None,
            market_id=market_id,
            external_url=None,
            metadata={"condition_id": condition_id, "token_id": token_id},
        ),
    )


def _normalize_price_history_payload(raw_payload: RawVenuePayload) -> NormalizedVenuePayload:
    body = raw_payload.response_payload
    metadata = raw_payload.metadata
    external_market_id = _optional_str(
        metadata.get("condition_id")
        or metadata.get("external_market_id")
        or raw_payload.external_id
        or raw_payload.request_params.get("market")
        or body.get("market")
    )
    if not external_market_id:
        raise ValueError("Polymarket price history payload is missing market identifier.")
    market_id = _optional_str(metadata.get("canonical_market_id")) or _market_id(external_market_id)
    history = body.get("history", [])
    if not isinstance(history, list):
        return NormalizedVenuePayload()

    snapshots: list[MarketPriceSnapshot] = []
    for point in history:
        if not isinstance(point, dict) or point.get("t") is None or point.get("p") is None:
            continue
        observed_at = _parse_datetime(point.get("t"))
        if observed_at is None:
            continue
        available_at = _parse_datetime(point.get("available_at")) or raw_payload.captured_at
        price = _price(point.get("p"))
        snapshot = MarketPriceSnapshot(
            price_snapshot_id="pending",
            market_id=market_id,
            outcome_id=None,
            venue_id="polymarket",
            venue_name="Polymarket",
            source=MarketPriceSource.VENUE_PRICE_HISTORY,
            observed_at=observed_at,
            captured_at=raw_payload.captured_at,
            available_at=available_at,
            price=price,
            bid=None,
            ask=None,
            mid=price,
            spread=None,
            last_trade_price=price,
            volume=_optional_decimal(point.get("volume")),
            open_interest=None,
            source_payload_id=raw_payload.payload_id,
            orderbook_snapshot_id=None,
            external_market_id=external_market_id,
            external_outcome_id=_optional_str(
                point.get("token_id")
                or point.get("asset_id")
                or metadata.get("token_id")
                or metadata.get("asset_id")
            ),
            data_hash="pending",
            metadata={
                "raw_point": point,
                "token_id": _optional_str(metadata.get("token_id") or metadata.get("asset_id")),
            },
        )
        data_hash = compute_market_price_hash(snapshot)
        snapshots.append(
            snapshot.model_copy(
                update={
                    "price_snapshot_id": f"price_{data_hash[:24]}",
                    "data_hash": data_hash,
                }
            )
        )

    return NormalizedVenuePayload(
        price_snapshots=snapshots,
        mapping=_mapping(
            raw_payload=raw_payload,
            external_event_id=None,
            external_market_id=external_market_id,
            external_symbol=None,
            event_id=None,
            market_id=market_id,
            external_url=None,
            metadata={"source": "polymarket_price_history"},
        ),
    )


def _mapping(
    *,
    raw_payload: RawVenuePayload,
    external_event_id: str | None,
    external_market_id: str,
    external_symbol: str | None,
    event_id: str | None,
    market_id: str,
    external_url: str | None,
    metadata: dict[str, Any],
) -> VenueMarketMapping:
    return VenueMarketMapping(
        mapping_id=f"mapping_polymarket_{_slug(external_market_id)}",
        venue_id="polymarket",
        venue_name="Polymarket",
        external_event_id=external_event_id,
        external_market_id=external_market_id,
        external_symbol=external_symbol,
        canonical_event_id=event_id,
        canonical_market_id=market_id,
        external_url=external_url,
        first_seen_at=raw_payload.captured_at,
        last_seen_at=raw_payload.captured_at,
        status=VenueMappingStatus.ACTIVE,
        metadata={"source_payload_id": raw_payload.payload_id, **metadata},
    )


def _outcome_token_mappings(
    *,
    raw_payload: RawVenuePayload,
    market_id: str,
    outcome_labels: list[str],
    token_ids: list[str],
    external_market_id: str,
    condition_id: str | None,
    question_id: str | None,
    gamma_market_id: str | None,
    gamma_event_id: str | None,
    market_address: str | None,
    enable_orderbook: bool | None,
) -> list[VenueOutcomeTokenMapping]:
    mappings: list[VenueOutcomeTokenMapping] = []
    for index, label in enumerate(outcome_labels):
        token_id = token_ids[index] if index < len(token_ids) else None
        side = _token_side(label)
        status = (
            VenueOutcomeTokenStatus.ACTIVE
            if token_id
            else VenueOutcomeTokenStatus.MISSING_TOKEN
        )
        mapping_key = token_id or f"{condition_id or external_market_id}_{side.value}_{index}"
        mappings.append(
            VenueOutcomeTokenMapping(
                mapping_id=f"token_mapping_polymarket_{_slug(mapping_key)}",
                venue_id="polymarket",
                venue_name="Polymarket",
                canonical_market_id=market_id,
                canonical_outcome_id=f"{market_id}_{_slug(label)}",
                outcome_label=label,
                external_market_id=external_market_id,
                condition_id=condition_id,
                question_id=question_id,
                gamma_market_id=gamma_market_id,
                gamma_event_id=gamma_event_id,
                market_address=market_address,
                token_id=token_id,
                asset_id=token_id,
                token_side=side,
                enable_orderbook=enable_orderbook,
                first_seen_at=raw_payload.captured_at,
                last_seen_at=raw_payload.captured_at,
                status=status,
                metadata={
                    "source_payload_id": raw_payload.payload_id,
                    "token_index": index,
                    "fixture_file": raw_payload.metadata.get("fixture_file"),
                },
            )
        )
    return mappings


def _rule_text(market_payload: dict[str, Any]) -> str:
    parts = [
        _optional_str(
            market_payload.get("resolutionRules") or market_payload.get("resolution_rules")
        ),
        _optional_str(market_payload.get("rules")),
        _optional_str(market_payload.get("description")),
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
            market_payload.get("resolutionSource")
            or market_payload.get("resolution_source")
            or market_payload.get("resolution_source_url")
        ),
        settlement_authority=_optional_str(
            market_payload.get("settlementAuthority")
            or market_payload.get("settlement_authority")
            or "Polymarket"
        ),
        time_zone=_optional_str(market_payload.get("timezone") or market_payload.get("time_zone")),
    )
    return snapshot.rule_hash


def _external_market_id(
    market_payload: dict[str, Any], raw_payload: RawVenuePayload
) -> str:
    for key in ("conditionId", "condition_id", "id", "marketId", "market_id", "questionID"):
        value = _optional_str(market_payload.get(key))
        if value:
            return value
    if raw_payload.external_id:
        return raw_payload.external_id
    raise ValueError("Polymarket market payload is missing external market ID.")


def _outcome_labels(market_payload: dict[str, Any]) -> list[str]:
    value = market_payload.get("outcomes")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    tokens = market_payload.get("tokens")
    if isinstance(tokens, list) and tokens:
        labels = [
            str(token.get("outcome") or token.get("name"))
            for token in tokens
            if isinstance(token, dict) and (token.get("outcome") or token.get("name"))
        ]
        if labels:
            return labels
    return ["Yes", "No"]


def _token_ids(market_payload: dict[str, Any]) -> list[str]:
    value = market_payload.get("clobTokenIds") or market_payload.get("clob_token_ids")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except json.JSONDecodeError:
            return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    tokens = market_payload.get("tokens")
    if isinstance(tokens, list):
        return [
            str(token.get("token_id") or token.get("id"))
            for token in tokens
            if isinstance(token, dict) and (token.get("token_id") or token.get("id"))
        ]
    return []


def _token_side(label: str) -> VenueOutcomeTokenSide:
    normalized = _normalize_space(label).casefold()
    if normalized == "yes":
        return VenueOutcomeTokenSide.YES
    if normalized == "no":
        return VenueOutcomeTokenSide.NO
    return VenueOutcomeTokenSide.OTHER


def _map_status(market_payload: dict[str, Any]) -> MarketStatus:
    if bool(market_payload.get("resolved")):
        return MarketStatus.SETTLED
    if bool(market_payload.get("closed")):
        return MarketStatus.CLOSED
    if bool(market_payload.get("active", True)):
        return MarketStatus.ACTIVE
    return MarketStatus.CLOSED


def _levels(value: object) -> list[tuple[object, object]]:
    if not isinstance(value, list):
        return []
    levels: list[tuple[object, object]] = []
    for item in value:
        if isinstance(item, list | tuple) and len(item) >= 2:
            levels.append((item[0], item[1]))
        elif isinstance(item, dict):
            price = item.get("price")
            size = item.get("size") or item.get("quantity")
            if price is not None and size is not None:
                levels.append((price, size))
    return levels


def _price(value: object) -> Decimal:
    price = _decimal(value)
    if price < Decimal("0") or price > Decimal("1"):
        raise ValueError(f"Polymarket price outside [0, 1]: {price}")
    return price


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return _decimal(value)


def _market_id(external_market_id: str) -> str:
    return f"polymarket_market_{_slug(external_market_id)}"


def _event_id(external_event_id: str) -> str:
    return f"polymarket_event_{_slug(external_event_id)}"


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


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().casefold()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    return None


def _first_present(source: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in source:
            return source[key]
    return None


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
