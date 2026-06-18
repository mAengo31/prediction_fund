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
        return self.fetch_market_detail_by_gamma_id(
            external_market_id,
            allow_network=allow_network,
            captured_at=captured_at,
        )

    def fetch_market_detail_by_gamma_id(
        self,
        gamma_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_id(
                VenueEndpointType.MARKET_DETAIL,
                gamma_market_id,
                captured_at=captured_at,
            )
        return self._get(
            source_url=f"{POLYMARKET_GAMMA_BASE_URL}/markets/{gamma_market_id}",
            endpoint_type=VenueEndpointType.MARKET_DETAIL,
            external_id=gamma_market_id,
            params={},
            captured_at=captured_at,
        )

    def fetch_market_detail_by_slug(
        self,
        slug: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_id(
                VenueEndpointType.MARKET_DETAIL,
                slug,
                captured_at=captured_at,
            )
        return self._get(
            source_url=f"{POLYMARKET_GAMMA_BASE_URL}/markets/slug/{slug}",
            endpoint_type=VenueEndpointType.MARKET_DETAIL,
            external_id=slug,
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
        return self.fetch_orderbook_by_token_id(
            external_market_id,
            allow_network=allow_network,
            captured_at=captured_at,
        )

    def fetch_orderbook_by_token_id(
        self,
        token_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_token_id(
                VenueEndpointType.ORDERBOOK,
                token_id,
                captured_at=captured_at,
            )
        return self._get(
            source_url=f"{POLYMARKET_CLOB_BASE_URL}/book",
            endpoint_type=VenueEndpointType.ORDERBOOK,
            external_id=token_id,
            params={"token_id": token_id},
            captured_at=captured_at,
        )

    def fetch_price_history(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        return self.fetch_price_history_by_token_id(
            external_market_id,
            allow_network=allow_network,
            captured_at=captured_at,
        )

    def fetch_price_history_by_token_id(
        self,
        token_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        if not allow_network:
            return self._fixture_by_type_and_token_id(
                VenueEndpointType.PRICE_HISTORY,
                token_id,
                captured_at=captured_at,
            )
        return self._get(
            source_url=f"{POLYMARKET_CLOB_BASE_URL}/prices-history",
            endpoint_type=VenueEndpointType.PRICE_HISTORY,
            external_id=token_id,
            params={"market": token_id},
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
        self,
        endpoint_type: VenueEndpointType,
        external_market_id: str,
        *,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        for payload in self.fixture_payloads(captured_at):
            if payload.endpoint_type != endpoint_type:
                continue
            if payload.external_id == external_market_id:
                return payload
            market_payload = payload.response_payload.get("market", payload.response_payload)
            if isinstance(market_payload, dict):
                identifiers = {
                    market_payload.get("id"),
                    market_payload.get("conditionId"),
                    market_payload.get("condition_id"),
                    market_payload.get("slug"),
                    payload.request_params.get("id"),
                }
                if external_market_id in {str(item) for item in identifiers if item is not None}:
                    return payload
        raise FileNotFoundError(f"No Polymarket fixture for {endpoint_type}:{external_market_id}")

    def _fixture_by_type_and_token_id(
        self,
        endpoint_type: VenueEndpointType,
        token_id: str,
        *,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        for payload in self.fixture_payloads(captured_at):
            if payload.endpoint_type != endpoint_type:
                continue
            if payload.external_id == token_id:
                return payload
            identifiers = {
                payload.request_params.get("token_id"),
                payload.request_params.get("market"),
                payload.response_payload.get("asset_id"),
                payload.response_payload.get("token_id"),
                payload.response_payload.get("market"),
            }
            history = payload.response_payload.get("history")
            if isinstance(history, list):
                for point in history:
                    if isinstance(point, dict):
                        identifiers.add(point.get("token_id"))
                        identifiers.add(point.get("asset_id"))
            if token_id in {str(item) for item in identifiers if item is not None}:
                return payload
        raise FileNotFoundError(f"No Polymarket fixture for {endpoint_type}:{token_id}")
