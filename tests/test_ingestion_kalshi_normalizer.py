from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.enums import MarketStatus, MarketType
from prediction_desk.ingestion.fixtures import load_fixture_payloads
from prediction_desk.ingestion.normalizers.kalshi import normalize_kalshi_payload


def test_kalshi_normalizer_maps_market_detail_into_canonical_objects() -> None:
    payload = _payload("market_detail_weather.json")
    [normalized] = normalize_kalshi_payload(payload)

    assert normalized.market is not None
    assert normalized.rule_snapshot is not None
    assert normalized.mapping is not None
    assert normalized.market.market_id == "kalshi_market_kxweather_nyc_rain_20260930"
    assert normalized.market.market_type is MarketType.BINARY
    assert normalized.market.status is MarketStatus.ACTIVE
    assert "National Weather Service" in normalized.rule_snapshot.raw_rule_text
    assert normalized.rule_snapshot.resolution_source == "National Weather Service"
    assert {outcome.label for outcome in normalized.outcomes} == {"YES", "NO"}
    assert normalized.mapping.external_market_id == "KXWEATHER-NYC-RAIN-20260930"


def test_kalshi_orderbook_converts_no_bids_into_yes_side_asks() -> None:
    payload = _payload("orderbook_weather.json")
    [normalized] = normalize_kalshi_payload(payload)

    assert normalized.orderbook_snapshot is not None
    orderbook = normalized.orderbook_snapshot
    assert orderbook.bids[0].price == Decimal("0.58")
    assert orderbook.asks[0].price == Decimal("0.61")
    assert orderbook.asks[0].quantity == Decimal("110")
    assert orderbook.metadata["no_bids_raw"][0] == [39, 110]


def test_kalshi_normalizer_uses_decimal_prices_not_float() -> None:
    payload = _payload("orderbook_weather.json")
    [normalized] = normalize_kalshi_payload(payload)

    assert normalized.orderbook_snapshot is not None
    assert isinstance(normalized.orderbook_snapshot.bids[0].price, Decimal)
    assert isinstance(normalized.orderbook_snapshot.asks[0].price, Decimal)


def _payload(name: str):
    fixture_dir = Path("sample_data/venue_payloads/kalshi")
    payloads = load_fixture_payloads(
        venue_id="kalshi",
        venue_name="Kalshi",
        fixture_dir=fixture_dir,
    )
    for payload in payloads:
        if payload.metadata["fixture_file"] == name:
            return payload
    raise AssertionError(name)
