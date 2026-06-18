from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.enums import MarketStatus, MarketType
from prediction_desk.ingestion.fixtures import load_fixture_payloads
from prediction_desk.ingestion.normalizers.polymarket import normalize_polymarket_payload


def test_polymarket_normalizer_maps_gamma_payload_into_market_and_outcomes() -> None:
    payload = _payload("market_detail_weather.json")
    [normalized] = normalize_polymarket_payload(payload)

    assert normalized.market is not None
    assert normalized.rule_snapshot is not None
    assert normalized.market.market_id == "polymarket_market_0xabc123nyctemp"
    assert normalized.market.market_type is MarketType.BINARY
    assert normalized.market.status is MarketStatus.ACTIVE
    assert [outcome.label for outcome in normalized.outcomes] == ["Yes", "No"]
    assert normalized.rule_snapshot.resolution_source == "National Weather Service"


def test_polymarket_orderbook_fixture_maps_into_orderbook_snapshot() -> None:
    payload = _payload("orderbook_weather.json")
    [normalized] = normalize_polymarket_payload(payload)

    assert normalized.orderbook_snapshot is not None
    orderbook = normalized.orderbook_snapshot
    assert orderbook.market_id == "polymarket_market_0xabc123nyctemp"
    assert orderbook.bids[0].price == Decimal("0.61")
    assert orderbook.asks[0].price == Decimal("0.64")


def test_polymarket_normalizer_preserves_token_and_condition_ids() -> None:
    payload = _payload("market_detail_weather.json")
    [normalized] = normalize_polymarket_payload(payload)

    assert normalized.market is not None
    assert normalized.mapping is not None
    assert normalized.market.metadata["condition_id"] == "0xabc123nyctemp"
    assert normalized.market.metadata["gamma_market_id"] == "pm-nyc-temp-20260704"
    assert normalized.market.metadata["enable_orderbook"] is True
    assert normalized.market.metadata["token_ids"][0].startswith("111111")
    assert normalized.outcomes[0].metadata["token_id"].startswith("111111")
    assert normalized.outcomes[0].metadata["token_side"] == "YES"
    assert normalized.mapping.external_symbol == "0xabc123nyctemp"
    assert normalized.mapping.metadata["gamma_market_id"] == "pm-nyc-temp-20260704"
    assert len(normalized.outcome_token_mappings) == 2
    assert normalized.outcome_token_mappings[0].gamma_market_id == "pm-nyc-temp-20260704"
    assert normalized.outcome_token_mappings[0].token_side.value == "YES"
    assert normalized.outcome_token_mappings[0].status.value == "ACTIVE"
    assert normalized.outcome_token_mappings[0].enable_orderbook is True


def test_polymarket_orderbook_can_use_token_targeting_metadata() -> None:
    payload = _payload("orderbook_weather.json")
    token_payload = payload.model_copy(
        update={
            "external_id": "1111111111111111111111111111111111111111111111111111111111111111",
            "metadata": {
                **payload.metadata,
                "canonical_market_id": "polymarket_market_0xabc123nyctemp",
                "condition_id": "0xabc123nyctemp",
                "token_id": "1111111111111111111111111111111111111111111111111111111111111111",
            },
        }
    )
    [normalized] = normalize_polymarket_payload(token_payload)

    assert normalized.orderbook_snapshot is not None
    assert normalized.orderbook_snapshot.market_id == "polymarket_market_0xabc123nyctemp"
    assert normalized.orderbook_snapshot.metadata["token_id"].startswith("111111")


def test_polymarket_orderbook_snapshot_id_stays_bounded_for_long_token_ids() -> None:
    payload = _payload("orderbook_weather.json")
    condition_id = "0x" + ("a" * 64)
    token_id = "9" * 77
    token_payload = payload.model_copy(
        update={
            "external_id": token_id,
            "response_payload": {
                **payload.response_payload,
                "asset_id": token_id,
                "market": condition_id,
            },
            "metadata": {
                **payload.metadata,
                "canonical_market_id": f"polymarket_market_{condition_id}",
                "condition_id": condition_id,
                "token_id": token_id,
            },
        }
    )

    [normalized] = normalize_polymarket_payload(token_payload)

    assert normalized.orderbook_snapshot is not None
    assert len(normalized.orderbook_snapshot.snapshot_id) <= 128


def test_polymarket_price_history_fixture_maps_into_price_snapshot() -> None:
    payload = _payload("price_history_weather.json")
    [normalized] = normalize_polymarket_payload(payload)

    assert normalized.price_snapshots
    snapshot = normalized.price_snapshots[0]
    assert snapshot.market_id == "polymarket_market_0xabc123nyctemp"
    assert snapshot.price == Decimal("0.62")
    assert snapshot.mid == Decimal("0.62")
    assert snapshot.external_outcome_id is not None
    assert snapshot.available_at.isoformat() == "2026-06-16T12:10:00+00:00"


def test_polymarket_price_history_accepts_unix_second_timestamps() -> None:
    payload = _payload("price_history_weather.json")
    token_id = "1111111111111111111111111111111111111111111111111111111111111111"
    timestamp_payload = payload.model_copy(
        update={
            "response_payload": {
                "history": [
                    {
                        "t": 1781686819,
                        "available_at": "2026-06-16T12:10:00Z",
                        "p": "0.63",
                        "token_id": token_id,
                    }
                ]
            }
        }
    )

    [normalized] = normalize_polymarket_payload(timestamp_payload)

    assert normalized.price_snapshots
    assert normalized.price_snapshots[0].observed_at.isoformat() == "2026-06-17T09:00:19+00:00"


def _payload(name: str):
    fixture_dir = Path("sample_data/venue_payloads/polymarket")
    payloads = load_fixture_payloads(
        venue_id="polymarket",
        venue_name="Polymarket",
        fixture_dir=fixture_dir,
    )
    for payload in payloads:
        if payload.metadata["fixture_file"] == name:
            return payload
    raise AssertionError(name)
