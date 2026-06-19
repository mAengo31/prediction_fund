"""Pydantic models for vendor dataset sample evaluation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from prediction_desk.vendor_data.enums import (
    VendorEvaluationStatus,
    VendorFileType,
    VendorImportDryRunStatus,
    VendorLicenseStatus,
    VendorSampleKind,
    VendorValidationStatus,
)

VENDOR_DATA_VERSION = "vendor_data_evaluation_v1"


class VendorDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VendorDatasetSource(VendorDataModel):
    vendor_source_id: str
    vendor_name: str
    dataset_name: str
    dataset_version: str
    created_at: datetime
    contact_url: str | None = None
    license_status: VendorLicenseStatus = VendorLicenseStatus.UNKNOWN
    supported_file_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorSampleFile(VendorDataModel):
    sample_file_id: str
    vendor_source_id: str
    file_name: str
    file_type: VendorFileType
    local_path: str
    imported_at: datetime
    file_size_bytes: int = Field(ge=0)
    file_hash: str
    row_count: int | None = Field(default=None, ge=0)
    schema_summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorSchemaInspection(VendorDataModel):
    schema_inspection_id: str
    sample_file_id: str
    inspected_at: datetime
    detected_columns: list[str] = Field(default_factory=list)
    detected_types: dict[str, str] = Field(default_factory=dict)
    timestamp_columns: list[str] = Field(default_factory=list)
    market_identifier_columns: list[str] = Field(default_factory=list)
    token_identifier_columns: list[str] = Field(default_factory=list)
    price_columns: list[str] = Field(default_factory=list)
    size_columns: list[str] = Field(default_factory=list)
    orderbook_columns: list[str] = Field(default_factory=list)
    trade_columns: list[str] = Field(default_factory=list)
    resolution_columns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorDataValidationReport(VendorDataModel):
    validation_report_id: str
    sample_file_id: str
    created_at: datetime
    validation_status: VendorValidationStatus
    row_count: int = Field(ge=0)
    missing_required_columns: list[str] = Field(default_factory=list)
    token_mapping_issues: list[str] = Field(default_factory=list)
    timestamp_issues: list[str] = Field(default_factory=list)
    price_issues: list[str] = Field(default_factory=list)
    duplicate_issues: list[str] = Field(default_factory=list)
    point_in_time_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorImportDryRun(VendorDataModel):
    dry_run_id: str
    sample_file_id: str
    created_at: datetime
    status: VendorImportDryRunStatus
    rows_examined: int = Field(ge=0)
    canonical_markets_detected: int = Field(ge=0)
    canonical_orderbooks_detected: int = Field(ge=0)
    canonical_price_snapshots_detected: int = Field(ge=0)
    canonical_trade_prints_detected: int = Field(ge=0)
    canonical_resolution_events_detected: int = Field(ge=0)
    would_create_counts: dict[str, int] = Field(default_factory=dict)
    would_skip_counts: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorEvaluationReport(VendorDataModel):
    evaluation_report_id: str
    vendor_source_id: str
    created_at: datetime
    sample_file_ids: list[str] = Field(default_factory=list)
    overall_status: VendorEvaluationStatus
    coverage_score: int = Field(ge=0, le=100)
    token_mapping_score: int = Field(ge=0, le=100)
    timestamp_quality_score: int = Field(ge=0, le=100)
    orderbook_quality_score: int = Field(ge=0, le=100)
    price_history_quality_score: int = Field(ge=0, le=100)
    replay_safety_score: int = Field(ge=0, le=100)
    license_readiness_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    questions_for_vendor: list[str] = Field(default_factory=list)
    recommendation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorDatasetSourceCreate(VendorDataModel):
    vendor_name: str
    dataset_name: str
    dataset_version: str
    contact_url: str | None = None
    license_status: VendorLicenseStatus = VendorLicenseStatus.UNKNOWN
    supported_file_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("vendor_name", "dataset_name", "dataset_version")
    @classmethod
    def _require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value required")
        return value.strip()


class VendorSampleLoadRequest(VendorDataModel):
    vendor_source_id: str
    file_path: str
    max_size_mb: int = Field(default=100, gt=0, le=10_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VendorDryRunImportRequest(VendorDataModel):
    sample_kind: VendorSampleKind | None = None


class VendorEvaluateRequest(VendorDataModel):
    vendor_source_id: str
    sample_file_ids: list[str] = Field(default_factory=list)
