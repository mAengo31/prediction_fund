"""Helpers for deterministic venue fixture loading."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prediction_desk.ingestion.enums import VenueEndpointType
from prediction_desk.ingestion.models import RawVenuePayload

FIXTURE_SCHEMA_VERSION = "venue_fixture_payload_v1"


def default_fixture_root() -> Path:
    candidates = [
        Path.cwd() / "sample_data" / "venue_payloads",
        Path(__file__).resolve().parents[3] / "sample_data" / "venue_payloads",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_fixture_payloads(
    *,
    venue_id: str,
    venue_name: str,
    fixture_dir: Path,
    captured_at: datetime | None = None,
) -> list[RawVenuePayload]:
    resolved_captured_at = captured_at or datetime.now(tz=UTC)
    payloads: list[RawVenuePayload] = []
    for path in sorted(fixture_dir.glob("*.json")):
        data = _read_fixture(path)
        endpoint_type = VenueEndpointType(data.get("endpoint_type", VenueEndpointType.UNKNOWN))
        external_id = data.get("external_id")
        payloads.append(
            RawVenuePayload.from_payload(
                venue_id=venue_id,
                venue_name=venue_name,
                endpoint_type=endpoint_type,
                external_id=external_id,
                captured_at=_fixture_captured_at(data, resolved_captured_at),
                source_url=data.get("source_url"),
                request_params=data.get("request_params", {}),
                response_payload=data.get("response_payload", {}),
                schema_version=data.get("schema_version", FIXTURE_SCHEMA_VERSION),
                metadata={"fixture_file": str(path.name), **data.get("metadata", {})},
            )
        )
    return payloads


def _read_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Fixture {path} must contain a JSON object.")
    return value


def _fixture_captured_at(data: dict[str, Any], fallback: datetime) -> datetime:
    value = data.get("captured_at")
    if not value:
        return fallback
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
