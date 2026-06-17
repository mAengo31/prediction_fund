"""Read-only Polymarket public-data adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import httpx

from prediction_desk.ingestion.adapters.base import FixtureBackedAdapter
from prediction_desk.ingestion.enums import VenueEndpointType
from prediction_desk.ingestion.fixtures import default_fixture_root
from prediction_desk.ingestion.models import RawVenuePayload

POLYMARKET_GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
POLYMARKET_CLOB_BASE_URL = "https://clob.polymarket.com"
USER_AGENT = "prediction-desk/0.1 read-only research"


class PolymarketReadOnlyAdapter(FixtureBackedAdapter):
    venue_id = "polymarket"
    venue_name = "Polymarket"

    def __init__(self, fixture_dir: Path | None = None) -> None:
        super().__init__(fixture_dir or default_fixture_root() / "polymarket")

    def fetch_market_catalog(
        self,
        *,
        limit: int = 100,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> list[RawVenuePayload]:
        if not allow_network:
            return [
                payload
                for payload in self.fixture_payloads(captured_at)
                if payload.endpoint_type == VenueEndpointType.MARKET_LIST
            ]
        return [
            self._get(
                source_url=f"{POLYMARKET_GAMMA_BASE_URL}/markets",
                endpoint_type=VenueEndpointType.MARKET_LIST,
                external_id=None,
                params={"limit": limit},
                captured_at=captured_at,
            )
        ]

    def fetch_market_detail(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_id(VenueEndpointType.MARKET_DETAIL, external_market_id)
        return self._get(
            source_url=f"{POLYMARKET_GAMMA_BASE_URL}/markets/{external_market_id}",
            endpoint_type=VenueEndpointType.MARKET_DETAIL,
            external_id=external_market_id,
            params={},
            captured_at=captured_at,
        )

    def fetch_orderbook(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_id(VenueEndpointType.ORDERBOOK, external_market_id)
        return self._get(
            source_url=f"{POLYMARKET_CLOB_BASE_URL}/book",
            endpoint_type=VenueEndpointType.ORDERBOOK,
            external_id=external_market_id,
            params={"token_id": external_market_id},
            captured_at=captured_at,
        )

    def fetch_price_history(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_id(VenueEndpointType.PRICE_HISTORY, external_market_id)
        return self._get(
            source_url=f"{POLYMARKET_CLOB_BASE_URL}/prices-history",
            endpoint_type=VenueEndpointType.PRICE_HISTORY,
            external_id=external_market_id,
            params={"market": external_market_id},
            captured_at=captured_at,
        )

    def _get(
        self,
        *,
        source_url: str,
        endpoint_type: VenueEndpointType,
        external_id: str | None,
        params: dict[str, str | int | float | bool | None],
        captured_at: datetime | None,
    ) -> RawVenuePayload:
        self._ensure_network_allowed(True)
        with httpx.Client(
            timeout=10.0,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ) as client:
            response = client.get(source_url, params=params)
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, dict):
            payload = {"data": payload}
        return RawVenuePayload.from_payload(
            venue_id=self.venue_id,
            venue_name=self.venue_name,
            endpoint_type=endpoint_type,
            external_id=external_id,
            captured_at=captured_at or datetime.now(tz=UTC),
            source_url=source_url,
            request_params=dict(params),
            response_payload=payload,
        )

    def _fixture_by_type_and_id(
        self, endpoint_type: VenueEndpointType, external_market_id: str
    ) -> RawVenuePayload:
        for payload in self.fixture_payloads():
            if payload.endpoint_type == endpoint_type and payload.external_id == external_market_id:
                return payload
        raise FileNotFoundError(f"No Polymarket fixture for {endpoint_type}:{external_market_id}")
