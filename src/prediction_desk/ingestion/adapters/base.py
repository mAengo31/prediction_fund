"""Read-only venue adapter protocol."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from prediction_desk.ingestion.models import RawVenuePayload


class ReadOnlyVenueAdapter(Protocol):
    venue_id: str
    venue_name: str

    def fetch_market_catalog(
        self,
        *,
        limit: int = 100,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> list[RawVenuePayload]:
        """Fetch or load public market catalog payloads."""

    def fetch_market_detail(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        """Fetch or load a public market detail payload."""

    def fetch_orderbook(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        """Fetch or load a public orderbook payload."""

    def fetch_price_history(
        self,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        """Fetch or load public price history payloads."""


class NetworkDisabledError(RuntimeError):
    pass


class FixtureBackedAdapter:
    venue_id: str
    venue_name: str

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self.fixture_dir = fixture_dir

    def fixture_payloads(self, captured_at: datetime | None = None) -> list[RawVenuePayload]:
        if self.fixture_dir is None:
            raise FileNotFoundError("fixture_dir is required for fixture-backed ingestion.")
        from prediction_desk.ingestion.fixtures import load_fixture_payloads

        return load_fixture_payloads(
            venue_id=self.venue_id,
            venue_name=self.venue_name,
            fixture_dir=self.fixture_dir,
            captured_at=captured_at,
        )

    def _ensure_network_allowed(self, allow_network: bool) -> None:
        if not allow_network:
            raise NetworkDisabledError(
                "Public network fetch is disabled. Pass allow_network=True explicitly "
                "for manual read-only fetches."
            )
