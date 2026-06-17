"""Pydantic models for fixture-backed and read-only venue ingestion."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prediction_desk.domain.models import (
    Event,
    Market,
    MarketRuleSnapshot,
    OrderBookSnapshot,
    Outcome,
    Venue,
)
from prediction_desk.ingestion.enums import (
    IngestionCursorStatus,
    IngestionMode,
    IngestionRunStatus,
    IngestionSource,
    VenueEndpointType,
    VenueMappingStatus,
)
from prediction_desk.marketdata.models import MarketPriceSnapshot


class IngestionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def compute_response_hash(
    *,
    endpoint_type: VenueEndpointType,
    external_id: str | None,
    source_url: str | None,
    request_params: dict[str, Any],
    response_payload: dict[str, Any],
) -> str:
    """Return a deterministic SHA-256 hash for a raw venue response."""

    payload = {
        "endpoint_type": endpoint_type.value,
        "external_id": external_id,
        "request_params": request_params,
        "response_payload": response_payload,
        "source_url": source_url,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class RawVenuePayload(IngestionModel):
    payload_id: str
    venue_id: str
    venue_name: str
    endpoint_type: VenueEndpointType
    external_id: str | None = None
    captured_at: datetime
    source_url: str | None = None
    request_params: dict[str, Any] = Field(default_factory=dict)
    response_payload: dict[str, Any]
    response_hash: str
    schema_version: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_payload(
        cls,
        *,
        payload_id: str | None = None,
        venue_id: str,
        venue_name: str,
        endpoint_type: VenueEndpointType,
        external_id: str | None,
        captured_at: datetime,
        source_url: str | None,
        request_params: dict[str, Any] | None,
        response_payload: dict[str, Any],
        schema_version: str = "raw_venue_payload_v1",
        metadata: dict[str, Any] | None = None,
    ) -> RawVenuePayload:
        safe_request_params = _safe_request_params(request_params or {})
        response_hash = compute_response_hash(
            endpoint_type=endpoint_type,
            external_id=external_id,
            source_url=source_url,
            request_params=safe_request_params,
            response_payload=response_payload,
        )
        resolved_payload_id = payload_id or f"raw_payload_{response_hash[:24]}"
        return cls(
            payload_id=resolved_payload_id,
            venue_id=venue_id,
            venue_name=venue_name,
            endpoint_type=endpoint_type,
            external_id=external_id,
            captured_at=captured_at,
            source_url=source_url,
            request_params=safe_request_params,
            response_payload=response_payload,
            response_hash=response_hash,
            schema_version=schema_version,
            metadata=metadata or {},
        )


class VenueMarketMapping(IngestionModel):
    mapping_id: str
    venue_id: str
    venue_name: str
    external_event_id: str | None = None
    external_market_id: str
    external_symbol: str | None = None
    canonical_event_id: str | None = None
    canonical_market_id: str | None = None
    external_url: str | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    status: VenueMappingStatus
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionRun(IngestionModel):
    ingestion_run_id: str
    venue_id: str
    venue_name: str
    started_at: datetime
    completed_at: datetime | None = None
    status: IngestionRunStatus
    mode: IngestionMode
    source: IngestionSource
    endpoint_types: list[str] = Field(default_factory=list)
    markets_seen: int = 0
    markets_created: int = 0
    markets_updated: int = 0
    rule_snapshots_created: int = 0
    orderbook_snapshots_created: int = 0
    price_snapshots_created: int = 0
    liquidity_snapshots_created: int = 0
    quality_reports_created: int = 0
    payloads_archived: int = 0
    errors_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionError(IngestionModel):
    error_id: str
    ingestion_run_id: str
    venue_id: str
    external_id: str | None = None
    endpoint_type: str | None = None
    occurred_at: datetime
    error_code: str
    error_message: str
    payload_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedVenuePayload(IngestionModel):
    venue: Venue | None = None
    event: Event | None = None
    market: Market | None = None
    outcomes: list[Outcome] = Field(default_factory=list)
    rule_snapshot: MarketRuleSnapshot | None = None
    orderbook_snapshot: OrderBookSnapshot | None = None
    price_snapshots: list[MarketPriceSnapshot] = Field(default_factory=list)
    mapping: VenueMarketMapping | None = None


class IngestionRunResult(IngestionModel):
    run: IngestionRun
    errors: list[IngestionError] = Field(default_factory=list)


class IngestionCursor(IngestionModel):
    cursor_id: str
    venue_id: str
    venue_name: str
    endpoint_type: str
    external_market_id: str | None = None
    canonical_market_id: str | None = None
    cursor_value: str | None = None
    last_observed_at: datetime | None = None
    last_captured_at: datetime | None = None
    last_available_at: datetime | None = None
    last_success_at: datetime | None = None
    status: IngestionCursorStatus
    metadata: dict[str, Any] = Field(default_factory=dict)


class FixtureIngestionRequest(IngestionModel):
    fixture_dir: str | None = None
    captured_at: datetime | None = None
    analyze_rules: bool = True
    recompute_verdicts: bool = True


class PublicSampleIngestionRequest(IngestionModel):
    limit: int = Field(default=10, ge=1, le=100)
    allow_network: bool = False
    analyze_rules: bool = True
    recompute_verdicts: bool = True


def _safe_request_params(params: dict[str, Any]) -> dict[str, Any]:
    blocked_fragments = ("secret", "token", "key", "password", "authorization", "wallet")
    return {
        key: value
        for key, value in params.items()
        if all(fragment not in key.lower() for fragment in blocked_fragments)
    }
