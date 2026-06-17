"""Pydantic models for read-only data scaling and backfill operations."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from prediction_desk.dataops.enums import (
    BackfillJobStatus,
    BackfillSegmentStatus,
    CollectionRunMode,
    CollectionRunStatus,
    CoverageScopeType,
    DataGapSeverity,
    DataGapType,
)

DATAOPS_VERSION = "dataops_v1"


class DataOpsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketUniverseDefinition(DataOpsModel):
    universe_id: str
    universe_name: str
    universe_version: str
    created_at: datetime
    is_active: bool
    venue_names: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    market_statuses: list[str] = Field(default_factory=list)
    market_types: list[str] = Field(default_factory=list)
    include_market_ids: list[str] = Field(default_factory=list)
    exclude_market_ids: list[str] = Field(default_factory=list)
    title_include_patterns: list[str] = Field(default_factory=list)
    title_exclude_patterns: list[str] = Field(default_factory=list)
    min_market_data_quality_score: int | None = Field(default=None, ge=0, le=100)
    min_liquidity_depth: Decimal | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketUniverseMember(DataOpsModel):
    universe_member_id: str
    universe_id: str
    market_id: str
    venue_id: str | None = None
    venue_name: str | None = None
    event_id: str | None = None
    added_at: datetime
    asof_timestamp: datetime
    inclusion_reason_codes: list[str] = Field(default_factory=list)
    exclusion_reason_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionPlan(DataOpsModel):
    collection_plan_id: str
    plan_name: str
    plan_version: str
    created_at: datetime
    is_active: bool
    universe_id: str | None = None
    venue_names: list[str] = Field(default_factory=list)
    endpoint_types: list[str] = Field(default_factory=list)
    cadence_seconds: int = Field(gt=0)
    lookback_seconds: int | None = Field(default=None, ge=0)
    max_markets_per_run: int = Field(gt=0)
    max_payloads_per_run: int = Field(gt=0)
    allow_network_default: bool = False
    derive_market_data: bool = True
    compute_quality: bool = True
    analyze_rules: bool = True
    recompute_verdicts: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionRun(DataOpsModel):
    collection_run_id: str
    collection_plan_id: str | None = None
    universe_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: CollectionRunStatus
    mode: CollectionRunMode
    asof_timestamp: datetime
    allow_network: bool
    venue_names: list[str] = Field(default_factory=list)
    market_ids: list[str] = Field(default_factory=list)
    endpoint_types: list[str] = Field(default_factory=list)
    payloads_archived: int = 0
    markets_processed: int = 0
    price_snapshots_created: int = 0
    liquidity_snapshots_created: int = 0
    quality_reports_created: int = 0
    ingestion_runs_created: int = 0
    errors_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackfillJob(DataOpsModel):
    backfill_job_id: str
    job_name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: BackfillJobStatus
    venue_name: str
    market_ids: list[str] = Field(default_factory=list)
    endpoint_types: list[str] = Field(default_factory=list)
    start_time: datetime
    end_time: datetime
    interval_seconds: int | None = Field(default=None, gt=0)
    allow_network: bool
    max_segments: int = Field(default=1000, gt=0)
    segments_created: int = 0
    segments_completed: int = 0
    segments_failed: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackfillSegment(DataOpsModel):
    backfill_segment_id: str
    backfill_job_id: str
    venue_name: str
    market_id: str | None = None
    endpoint_type: str
    segment_start_time: datetime
    segment_end_time: datetime
    status: BackfillSegmentStatus
    supported: bool
    unsupported_reason: str | None = None
    payloads_archived: int = 0
    snapshots_created: int = 0
    errors_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataCoverageReport(DataOpsModel):
    coverage_report_id: str
    asof_timestamp: datetime
    created_at: datetime
    scope_type: CoverageScopeType
    universe_id: str | None = None
    market_id: str | None = None
    venue_name: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    total_markets: int = 0
    markets_with_rules: int = 0
    markets_with_orderbooks: int = 0
    markets_with_price_snapshots: int = 0
    markets_with_liquidity_snapshots: int = 0
    markets_with_quality_reports: int = 0
    stale_markets: int = 0
    missing_rule_markets: int = 0
    missing_price_markets: int = 0
    missing_liquidity_markets: int = 0
    average_quality_score: Decimal | None = None
    coverage_score: int = Field(default=0, ge=0, le=100)
    reason_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataGap(DataOpsModel):
    data_gap_id: str
    coverage_report_id: str | None = None
    market_id: str | None = None
    venue_name: str | None = None
    gap_type: DataGapType
    severity: DataGapSeverity
    start_time: datetime | None = None
    end_time: datetime | None = None
    detected_at: datetime
    expected_cadence_seconds: int | None = None
    observed_count: int = 0
    expected_count: int | None = None
    reason_code: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataRetentionPolicy(DataOpsModel):
    retention_policy_id: str
    policy_name: str
    created_at: datetime
    is_active: bool
    raw_payload_retention_days: int | None = Field(default=None, ge=0)
    orderbook_snapshot_retention_days: int | None = Field(default=None, ge=0)
    price_snapshot_retention_days: int | None = Field(default=None, ge=0)
    liquidity_snapshot_retention_days: int | None = Field(default=None, ge=0)
    quality_report_retention_days: int | None = Field(default=None, ge=0)
    archive_before_delete: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectionRunResult(DataOpsModel):
    run: CollectionRun


class BackfillJobResult(DataOpsModel):
    job: BackfillJob
    segments: list[BackfillSegment] = Field(default_factory=list)


class DataOpsCycleConfig(DataOpsModel):
    name: str | None = None
    asof_timestamp: datetime
    setup_defaults: bool = True
    run_collection: bool = True
    run_backfill: bool = False
    compute_coverage: bool = True
    detect_gaps: bool = True
    plan_id: str | None = None
    universe_id: str | None = None
    venue_names: list[str] | None = None
    market_ids: list[str] | None = None
    mode: CollectionRunMode = CollectionRunMode.FIXTURE
    allow_network: bool = False
    max_payloads: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataOpsCycleResult(DataOpsModel):
    collection_run: CollectionRun | None = None
    coverage_report: DataCoverageReport | None = None
    gaps: list[DataGap] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataOpsCollectionRunRequest(DataOpsModel):
    plan_id: str | None = None
    universe_id: str | None = None
    venue_names: list[str] | None = None
    market_ids: list[str] | None = None
    endpoint_types: list[str] | None = None
    mode: CollectionRunMode = CollectionRunMode.FIXTURE
    allow_network: bool = False
    asof_timestamp: datetime | None = None
    max_payloads: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BackfillJobCreateRequest(DataOpsModel):
    job_name: str | None = None
    venue_name: str
    market_ids: list[str] = Field(default_factory=list)
    endpoint_types: list[str] = Field(default_factory=list)
    start_time: datetime
    end_time: datetime
    interval_seconds: int | None = Field(default=None, gt=0)
    allow_network: bool = False
    max_segments: int = Field(default=1000, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("endpoint_types")
    @classmethod
    def _require_endpoint_types(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("endpoint_types required")
        return value


class DataCoverageComputeRequest(DataOpsModel):
    scope_type: CoverageScopeType = CoverageScopeType.GLOBAL
    universe_id: str | None = None
    market_id: str | None = None
    venue_name: str | None = None
    asof_timestamp: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


class DataGapDetectRequest(DataOpsModel):
    scope_type: CoverageScopeType = CoverageScopeType.GLOBAL
    universe_id: str | None = None
    market_id: str | None = None
    venue_name: str | None = None
    asof_timestamp: datetime | None = None
    expected_cadence_seconds: int | None = Field(default=None, gt=0)


class DataOpsCycleRequest(DataOpsModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    setup_defaults: bool = True
    run_collection: bool = True
    run_backfill: bool = False
    compute_coverage: bool = True
    detect_gaps: bool = True
    plan_id: str | None = None
    universe_id: str | None = None
    venue_names: list[str] | None = None
    market_ids: list[str] | None = None
    mode: CollectionRunMode = CollectionRunMode.FIXTURE
    allow_network: bool = False
    max_payloads: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


def dataops_object_id(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}_{hash_payload(payload)[:24]}"


def hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        _json_ready(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def universe_id(name: str, version: str) -> str:
    return dataops_object_id(
        "market_universe",
        {"version": DATAOPS_VERSION, "name": name, "universe_version": version},
    )


def universe_member_id(universe_id_value: str, market_id: str, asof_timestamp: datetime) -> str:
    return dataops_object_id(
        "universe_member",
        {
            "version": DATAOPS_VERSION,
            "universe_id": universe_id_value,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp,
        },
    )


def collection_plan_id(name: str, version: str) -> str:
    return dataops_object_id(
        "collection_plan",
        {"version": DATAOPS_VERSION, "name": name, "plan_version": version},
    )


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, Decimal | datetime):
        return str(value)
    return value

