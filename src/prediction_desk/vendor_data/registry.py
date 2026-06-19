"""Deterministic vendor source helpers."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from prediction_desk.vendor_data.enums import VendorLicenseStatus
from prediction_desk.vendor_data.models import VendorDatasetSource


def stable_vendor_source_id(vendor_name: str, dataset_name: str, dataset_version: str) -> str:
    slug = _slug(f"{vendor_name}-{dataset_name}-{dataset_version}")[:48]
    digest = hashlib.sha256(
        f"{vendor_name}|{dataset_name}|{dataset_version}".lower().encode()
    ).hexdigest()[:16]
    return f"vendor_source_{slug}_{digest}"


def build_vendor_source(
    *,
    vendor_name: str,
    dataset_name: str,
    dataset_version: str,
    contact_url: str | None = None,
    license_status: VendorLicenseStatus = VendorLicenseStatus.UNKNOWN,
    supported_file_types: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> VendorDatasetSource:
    return VendorDatasetSource(
        vendor_source_id=stable_vendor_source_id(vendor_name, dataset_name, dataset_version),
        vendor_name=vendor_name.strip(),
        dataset_name=dataset_name.strip(),
        dataset_version=dataset_version.strip(),
        created_at=created_at or datetime.now(tz=UTC),
        contact_url=contact_url,
        license_status=license_status,
        supported_file_types=list(supported_file_types or ["CSV", "JSON", "JSONL"]),
        metadata=dict(metadata or {}),
    )


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "dataset"
