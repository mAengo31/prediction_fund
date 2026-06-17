from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.ingestion.enums import VenueEndpointType
from prediction_desk.ingestion.models import RawVenuePayload


def test_raw_venue_payload_hash_is_deterministic() -> None:
    captured_at = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)

    first = RawVenuePayload.from_payload(
        venue_id="kalshi",
        venue_name="Kalshi",
        endpoint_type=VenueEndpointType.MARKET_DETAIL,
        external_id="KXTEST",
        captured_at=captured_at,
        source_url="fixture://kalshi/test",
        request_params={"limit": 1},
        response_payload={"market": {"ticker": "KXTEST", "status": "active"}},
    )
    second = RawVenuePayload.from_payload(
        venue_id="kalshi",
        venue_name="Kalshi",
        endpoint_type=VenueEndpointType.MARKET_DETAIL,
        external_id="KXTEST",
        captured_at=captured_at,
        source_url="fixture://kalshi/test",
        request_params={"limit": 1},
        response_payload={"market": {"status": "active", "ticker": "KXTEST"}},
    )

    assert first.response_hash == second.response_hash
    assert first.payload_id == second.payload_id


def test_raw_venue_payload_hash_changes_when_payload_changes() -> None:
    captured_at = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    base = {
        "venue_id": "kalshi",
        "venue_name": "Kalshi",
        "endpoint_type": VenueEndpointType.MARKET_DETAIL,
        "external_id": "KXTEST",
        "captured_at": captured_at,
        "source_url": "fixture://kalshi/test",
        "request_params": {"limit": 1},
    }

    first = RawVenuePayload.from_payload(
        **base,
        response_payload={"market": {"ticker": "KXTEST", "status": "active"}},
    )
    second = RawVenuePayload.from_payload(
        **base,
        response_payload={"market": {"ticker": "KXTEST", "status": "closed"}},
    )

    assert first.response_hash != second.response_hash
