"""Helpers for run-once ingestion cursor updates."""

from __future__ import annotations

from datetime import datetime

from prediction_desk.ingestion.enums import IngestionCursorStatus
from prediction_desk.ingestion.models import IngestionCursor, IngestionRun, VenueMarketMapping


def cursor_from_mapping(
    *,
    run: IngestionRun,
    mapping: VenueMarketMapping,
    endpoint_type: str,
    last_success_at: datetime,
) -> IngestionCursor:
    cursor_id = (
        f"cursor_{mapping.venue_id}_{endpoint_type.lower()}_"
        f"{mapping.external_market_id.lower().replace('-', '_')}"
    )
    return IngestionCursor(
        cursor_id=cursor_id,
        venue_id=mapping.venue_id,
        venue_name=mapping.venue_name,
        endpoint_type=endpoint_type,
        external_market_id=mapping.external_market_id,
        canonical_market_id=mapping.canonical_market_id,
        cursor_value=run.ingestion_run_id,
        last_observed_at=mapping.last_seen_at,
        last_captured_at=mapping.last_seen_at,
        last_available_at=mapping.last_seen_at,
        last_success_at=last_success_at,
        status=IngestionCursorStatus.ACTIVE,
        metadata={"last_ingestion_run_id": run.ingestion_run_id},
    )
