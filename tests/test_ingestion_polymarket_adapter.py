from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from prediction_desk.ingestion.adapters.polymarket import (
    POLYMARKET_CLOB_BASE_URL,
    PolymarketReadOnlyAdapter,
)
from prediction_desk.ingestion.enums import VenueEndpointType
from prediction_desk.ingestion.models import RawVenuePayload


def test_polymarket_price_history_public_request_uses_interval_and_fidelity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_get(
        self: PolymarketReadOnlyAdapter,
        *,
        source_url: str,
        endpoint_type: VenueEndpointType,
        external_id: str | None,
        params: dict[str, str | int | float | bool | None],
        captured_at: datetime | None,
    ) -> RawVenuePayload:
        captured.update(
            {
                "source_url": source_url,
                "endpoint_type": endpoint_type,
                "external_id": external_id,
                "params": params,
            }
        )
        return RawVenuePayload.from_payload(
            venue_id="polymarket",
            venue_name="Polymarket",
            endpoint_type=endpoint_type,
            external_id=external_id,
            captured_at=captured_at or datetime(2026, 6, 18, 8, 0, tzinfo=UTC),
            source_url=source_url,
            request_params=dict(params),
            response_payload={"history": []},
        )

    monkeypatch.setattr(PolymarketReadOnlyAdapter, "_get", fake_get)

    payload = PolymarketReadOnlyAdapter().fetch_price_history_by_token_id(
        "12345",
        allow_network=True,
    )

    assert captured == {
        "source_url": f"{POLYMARKET_CLOB_BASE_URL}/prices-history",
        "endpoint_type": VenueEndpointType.PRICE_HISTORY,
        "external_id": "12345",
        "params": {"market": "12345", "interval": "1d", "fidelity": 60},
    }
    assert payload.request_params == {"market": "12345", "interval": "1d", "fidelity": 60}
