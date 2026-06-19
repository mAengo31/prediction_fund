"""Add vendor dataset evaluation schema.

Revision ID: 20260619_0016
Revises: 20260618_0015
Create Date: 2026-06-19 00:16:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260619_0016"
down_revision = "20260618_0015"
branch_labels = None
depends_on = None


def _idxs(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "vendor_dataset_sources",
        sa.Column("vendor_source_id", sa.String(128), primary_key=True),
        sa.Column("vendor_name", sa.String(256), nullable=False),
        sa.Column("dataset_name", sa.String(256), nullable=False),
        sa.Column("dataset_version", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contact_url", sa.String(1024)),
        sa.Column("license_status", sa.String(64), nullable=False),
        sa.Column("supported_file_types", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("vendor_dataset_sources", ("vendor_name", "dataset_name", "created_at", "license_status"))

    op.create_table(
        "vendor_sample_files",
        sa.Column("sample_file_id", sa.String(128), primary_key=True),
        sa.Column(
            "vendor_source_id",
            sa.String(128),
            sa.ForeignKey("vendor_dataset_sources.vendor_source_id"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(512), nullable=False),
        sa.Column("file_type", sa.String(64), nullable=False),
        sa.Column("local_path", sa.String(2048), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer()),
        sa.Column("schema_summary", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "vendor_sample_files",
        ("vendor_source_id", "file_name", "file_type", "imported_at", "file_hash"),
    )

    op.create_table(
        "vendor_schema_inspections",
        sa.Column("schema_inspection_id", sa.String(128), primary_key=True),
        sa.Column(
            "sample_file_id",
            sa.String(128),
            sa.ForeignKey("vendor_sample_files.sample_file_id"),
            nullable=False,
        ),
        sa.Column("inspected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_columns", sa.JSON(), nullable=False),
        sa.Column("detected_types", sa.JSON(), nullable=False),
        sa.Column("timestamp_columns", sa.JSON(), nullable=False),
        sa.Column("market_identifier_columns", sa.JSON(), nullable=False),
        sa.Column("token_identifier_columns", sa.JSON(), nullable=False),
        sa.Column("price_columns", sa.JSON(), nullable=False),
        sa.Column("size_columns", sa.JSON(), nullable=False),
        sa.Column("orderbook_columns", sa.JSON(), nullable=False),
        sa.Column("trade_columns", sa.JSON(), nullable=False),
        sa.Column("resolution_columns", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("vendor_schema_inspections", ("sample_file_id", "inspected_at"))

    op.create_table(
        "vendor_data_validation_reports",
        sa.Column("validation_report_id", sa.String(128), primary_key=True),
        sa.Column(
            "sample_file_id",
            sa.String(128),
            sa.ForeignKey("vendor_sample_files.sample_file_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validation_status", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("missing_required_columns", sa.JSON(), nullable=False),
        sa.Column("token_mapping_issues", sa.JSON(), nullable=False),
        sa.Column("timestamp_issues", sa.JSON(), nullable=False),
        sa.Column("price_issues", sa.JSON(), nullable=False),
        sa.Column("duplicate_issues", sa.JSON(), nullable=False),
        sa.Column("point_in_time_issues", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("vendor_data_validation_reports", ("sample_file_id", "created_at", "validation_status"))

    op.create_table(
        "vendor_import_dry_runs",
        sa.Column("dry_run_id", sa.String(128), primary_key=True),
        sa.Column(
            "sample_file_id",
            sa.String(128),
            sa.ForeignKey("vendor_sample_files.sample_file_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("rows_examined", sa.Integer(), nullable=False),
        sa.Column("canonical_markets_detected", sa.Integer(), nullable=False),
        sa.Column("canonical_orderbooks_detected", sa.Integer(), nullable=False),
        sa.Column("canonical_price_snapshots_detected", sa.Integer(), nullable=False),
        sa.Column("canonical_trade_prints_detected", sa.Integer(), nullable=False),
        sa.Column("canonical_resolution_events_detected", sa.Integer(), nullable=False),
        sa.Column("would_create_counts", sa.JSON(), nullable=False),
        sa.Column("would_skip_counts", sa.JSON(), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("vendor_import_dry_runs", ("sample_file_id", "created_at", "status"))

    op.create_table(
        "vendor_evaluation_reports",
        sa.Column("evaluation_report_id", sa.String(128), primary_key=True),
        sa.Column(
            "vendor_source_id",
            sa.String(128),
            sa.ForeignKey("vendor_dataset_sources.vendor_source_id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sample_file_ids", sa.JSON(), nullable=False),
        sa.Column("overall_status", sa.String(64), nullable=False),
        sa.Column("coverage_score", sa.Integer(), nullable=False),
        sa.Column("token_mapping_score", sa.Integer(), nullable=False),
        sa.Column("timestamp_quality_score", sa.Integer(), nullable=False),
        sa.Column("orderbook_quality_score", sa.Integer(), nullable=False),
        sa.Column("price_history_quality_score", sa.Integer(), nullable=False),
        sa.Column("replay_safety_score", sa.Integer(), nullable=False),
        sa.Column("license_readiness_score", sa.Integer(), nullable=False),
        sa.Column("strengths", sa.JSON(), nullable=False),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("questions_for_vendor", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("vendor_evaluation_reports", ("vendor_source_id", "created_at", "overall_status"))


def downgrade() -> None:
    for table in (
        "vendor_evaluation_reports",
        "vendor_import_dry_runs",
        "vendor_data_validation_reports",
        "vendor_schema_inspections",
        "vendor_sample_files",
        "vendor_dataset_sources",
    ):
        op.drop_table(table)
