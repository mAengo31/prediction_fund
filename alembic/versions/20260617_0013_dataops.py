"""Add read-only dataops orchestration schema.

Revision ID: 20260617_0013
Revises: 20260617_0012
Create Date: 2026-06-17 00:13:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260617_0013"
down_revision = "20260617_0012"
branch_labels = None
depends_on = None


def _idxs(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "market_universe_definitions",
        sa.Column("universe_id", sa.String(128), primary_key=True),
        sa.Column("universe_name", sa.String(128), nullable=False),
        sa.Column("universe_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("venue_names", sa.JSON(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("market_statuses", sa.JSON(), nullable=False),
        sa.Column("market_types", sa.JSON(), nullable=False),
        sa.Column("include_market_ids", sa.JSON(), nullable=False),
        sa.Column("exclude_market_ids", sa.JSON(), nullable=False),
        sa.Column("title_include_patterns", sa.JSON(), nullable=False),
        sa.Column("title_exclude_patterns", sa.JSON(), nullable=False),
        sa.Column("min_market_data_quality_score", sa.Integer()),
        sa.Column("min_liquidity_depth", sa.Numeric(30, 10)),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("market_universe_definitions", ("universe_name", "created_at", "is_active"))

    op.create_table(
        "market_universe_members",
        sa.Column("universe_member_id", sa.String(128), primary_key=True),
        sa.Column("universe_id", sa.String(128), nullable=False),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("venue_id", sa.String(128)),
        sa.Column("venue_name", sa.String(256)),
        sa.Column("event_id", sa.String(128)),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inclusion_reason_codes", sa.JSON(), nullable=False),
        sa.Column("exclusion_reason_codes", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["universe_id"], ["market_universe_definitions.universe_id"]),
    )
    _idxs(
        "market_universe_members",
        (
            "universe_id",
            "market_id",
            "venue_id",
            "venue_name",
            "event_id",
            "added_at",
            "asof_timestamp",
        ),
    )

    op.create_table(
        "collection_plans",
        sa.Column("collection_plan_id", sa.String(128), primary_key=True),
        sa.Column("plan_name", sa.String(128), nullable=False),
        sa.Column("plan_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("universe_id", sa.String(128)),
        sa.Column("venue_names", sa.JSON(), nullable=False),
        sa.Column("endpoint_types", sa.JSON(), nullable=False),
        sa.Column("cadence_seconds", sa.Integer(), nullable=False),
        sa.Column("lookback_seconds", sa.Integer()),
        sa.Column("max_markets_per_run", sa.Integer(), nullable=False),
        sa.Column("max_payloads_per_run", sa.Integer(), nullable=False),
        sa.Column("allow_network_default", sa.Boolean(), nullable=False),
        sa.Column("derive_market_data", sa.Boolean(), nullable=False),
        sa.Column("compute_quality", sa.Boolean(), nullable=False),
        sa.Column("analyze_rules", sa.Boolean(), nullable=False),
        sa.Column("recompute_verdicts", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("collection_plans", ("plan_name", "created_at", "is_active", "universe_id"))

    op.create_table(
        "collection_runs",
        sa.Column("collection_run_id", sa.String(128), primary_key=True),
        sa.Column("collection_plan_id", sa.String(128)),
        sa.Column("universe_id", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("mode", sa.String(64), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("allow_network", sa.Boolean(), nullable=False),
        sa.Column("venue_names", sa.JSON(), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("endpoint_types", sa.JSON(), nullable=False),
        sa.Column("payloads_archived", sa.Integer(), nullable=False),
        sa.Column("markets_processed", sa.Integer(), nullable=False),
        sa.Column("price_snapshots_created", sa.Integer(), nullable=False),
        sa.Column("liquidity_snapshots_created", sa.Integer(), nullable=False),
        sa.Column("quality_reports_created", sa.Integer(), nullable=False),
        sa.Column("ingestion_runs_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "collection_runs",
        ("collection_plan_id", "universe_id", "created_at", "status", "mode", "asof_timestamp"),
    )

    op.create_table(
        "backfill_jobs",
        sa.Column("backfill_job_id", sa.String(128), primary_key=True),
        sa.Column("job_name", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("venue_name", sa.String(256), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("endpoint_types", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_seconds", sa.Integer()),
        sa.Column("allow_network", sa.Boolean(), nullable=False),
        sa.Column("max_segments", sa.Integer(), nullable=False),
        sa.Column("segments_created", sa.Integer(), nullable=False),
        sa.Column("segments_completed", sa.Integer(), nullable=False),
        sa.Column("segments_failed", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("backfill_jobs", ("created_at", "status", "venue_name"))

    op.create_table(
        "backfill_segments",
        sa.Column("backfill_segment_id", sa.String(128), primary_key=True),
        sa.Column("backfill_job_id", sa.String(128), nullable=False),
        sa.Column("venue_name", sa.String(256), nullable=False),
        sa.Column("market_id", sa.String(128)),
        sa.Column("endpoint_type", sa.String(64), nullable=False),
        sa.Column("segment_start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("segment_end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("supported", sa.Boolean(), nullable=False),
        sa.Column("unsupported_reason", sa.String(256)),
        sa.Column("payloads_archived", sa.Integer(), nullable=False),
        sa.Column("snapshots_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["backfill_job_id"], ["backfill_jobs.backfill_job_id"]),
    )
    _idxs(
        "backfill_segments",
        (
            "backfill_job_id",
            "venue_name",
            "market_id",
            "endpoint_type",
            "segment_start_time",
            "segment_end_time",
            "status",
            "supported",
        ),
    )

    op.create_table(
        "data_coverage_reports",
        sa.Column("coverage_report_id", sa.String(128), primary_key=True),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope_type", sa.String(64), nullable=False),
        sa.Column("universe_id", sa.String(128)),
        sa.Column("market_id", sa.String(128)),
        sa.Column("venue_name", sa.String(256)),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("total_markets", sa.Integer(), nullable=False),
        sa.Column("markets_with_rules", sa.Integer(), nullable=False),
        sa.Column("markets_with_orderbooks", sa.Integer(), nullable=False),
        sa.Column("markets_with_price_snapshots", sa.Integer(), nullable=False),
        sa.Column("markets_with_liquidity_snapshots", sa.Integer(), nullable=False),
        sa.Column("markets_with_quality_reports", sa.Integer(), nullable=False),
        sa.Column("stale_markets", sa.Integer(), nullable=False),
        sa.Column("missing_rule_markets", sa.Integer(), nullable=False),
        sa.Column("missing_price_markets", sa.Integer(), nullable=False),
        sa.Column("missing_liquidity_markets", sa.Integer(), nullable=False),
        sa.Column("average_quality_score", sa.Numeric(30, 10)),
        sa.Column("coverage_score", sa.Integer(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "data_coverage_reports",
        ("asof_timestamp", "created_at", "scope_type", "universe_id", "market_id", "venue_name"),
    )

    op.create_table(
        "data_gaps",
        sa.Column("data_gap_id", sa.String(128), primary_key=True),
        sa.Column("coverage_report_id", sa.String(128)),
        sa.Column("market_id", sa.String(128)),
        sa.Column("venue_name", sa.String(256)),
        sa.Column("gap_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True)),
        sa.Column("end_time", sa.DateTime(timezone=True)),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_cadence_seconds", sa.Integer()),
        sa.Column("observed_count", sa.Integer(), nullable=False),
        sa.Column("expected_count", sa.Integer()),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "data_gaps",
        (
            "coverage_report_id",
            "market_id",
            "venue_name",
            "gap_type",
            "severity",
            "detected_at",
            "reason_code",
        ),
    )

    op.create_table(
        "data_retention_policies",
        sa.Column("retention_policy_id", sa.String(128), primary_key=True),
        sa.Column("policy_name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("raw_payload_retention_days", sa.Integer()),
        sa.Column("orderbook_snapshot_retention_days", sa.Integer()),
        sa.Column("price_snapshot_retention_days", sa.Integer()),
        sa.Column("liquidity_snapshot_retention_days", sa.Integer()),
        sa.Column("quality_report_retention_days", sa.Integer()),
        sa.Column("archive_before_delete", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("data_retention_policies", ("policy_name", "created_at", "is_active"))


def downgrade() -> None:
    op.drop_table("data_retention_policies")
    op.drop_table("data_gaps")
    op.drop_table("data_coverage_reports")
    op.drop_table("backfill_segments")
    op.drop_table("backfill_jobs")
    op.drop_table("collection_runs")
    op.drop_table("collection_plans")
    op.drop_table("market_universe_members")
    op.drop_table("market_universe_definitions")
