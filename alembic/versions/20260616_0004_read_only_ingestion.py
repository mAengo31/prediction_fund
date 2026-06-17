"""Add read-only venue ingestion schema.

Revision ID: 20260616_0004
Revises: 20260616_0003
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0004"
down_revision = "20260616_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_venue_payloads",
        sa.Column("payload_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("venue_name", sa.String(length=256), nullable=False),
        sa.Column("endpoint_type", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("request_params", sa.JSON(), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("response_hash", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=128), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("payload_id"),
    )
    op.create_index("ix_raw_venue_payloads_captured_at", "raw_venue_payloads", ["captured_at"])
    op.create_index("ix_raw_venue_payloads_endpoint_type", "raw_venue_payloads", ["endpoint_type"])
    op.create_index("ix_raw_venue_payloads_external_id", "raw_venue_payloads", ["external_id"])
    op.create_index("ix_raw_venue_payloads_response_hash", "raw_venue_payloads", ["response_hash"])
    op.create_index("ix_raw_venue_payloads_venue_id", "raw_venue_payloads", ["venue_id"])
    op.create_index("ix_raw_venue_payloads_venue_name", "raw_venue_payloads", ["venue_name"])

    op.create_table(
        "venue_market_mappings",
        sa.Column("mapping_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("venue_name", sa.String(length=256), nullable=False),
        sa.Column("external_event_id", sa.String(length=512), nullable=True),
        sa.Column("external_market_id", sa.String(length=512), nullable=False),
        sa.Column("external_symbol", sa.String(length=512), nullable=True),
        sa.Column("canonical_event_id", sa.String(length=128), nullable=True),
        sa.Column("canonical_market_id", sa.String(length=128), nullable=True),
        sa.Column("external_url", sa.String(length=2048), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["canonical_market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("mapping_id"),
    )
    op.create_index(
        "ix_venue_market_mappings_canonical_event_id",
        "venue_market_mappings",
        ["canonical_event_id"],
    )
    op.create_index(
        "ix_venue_market_mappings_canonical_market_id",
        "venue_market_mappings",
        ["canonical_market_id"],
    )
    op.create_index(
        "ix_venue_market_mappings_external_market_id",
        "venue_market_mappings",
        ["external_market_id"],
    )
    op.create_index(
        "ix_venue_market_mappings_last_seen_at",
        "venue_market_mappings",
        ["last_seen_at"],
    )
    op.create_index("ix_venue_market_mappings_status", "venue_market_mappings", ["status"])
    op.create_index("ix_venue_market_mappings_venue_id", "venue_market_mappings", ["venue_id"])
    op.create_index(
        "ix_venue_market_mappings_venue_name",
        "venue_market_mappings",
        ["venue_name"],
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("ingestion_run_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("venue_name", sa.String(length=256), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("endpoint_types", sa.JSON(), nullable=False),
        sa.Column("markets_seen", sa.Integer(), nullable=False),
        sa.Column("markets_created", sa.Integer(), nullable=False),
        sa.Column("markets_updated", sa.Integer(), nullable=False),
        sa.Column("rule_snapshots_created", sa.Integer(), nullable=False),
        sa.Column("orderbook_snapshots_created", sa.Integer(), nullable=False),
        sa.Column("payloads_archived", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("ingestion_run_id"),
    )
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])
    op.create_index("ix_ingestion_runs_status", "ingestion_runs", ["status"])
    op.create_index("ix_ingestion_runs_venue_id", "ingestion_runs", ["venue_id"])
    op.create_index("ix_ingestion_runs_venue_name", "ingestion_runs", ["venue_name"])

    op.create_table(
        "ingestion_errors",
        sa.Column("error_id", sa.String(length=128), nullable=False),
        sa.Column("ingestion_run_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("external_id", sa.String(length=512), nullable=True),
        sa.Column("endpoint_type", sa.String(length=64), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("payload_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["ingestion_runs.ingestion_run_id"]),
        sa.ForeignKeyConstraint(["payload_id"], ["raw_venue_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("error_id"),
    )
    op.create_index("ix_ingestion_errors_error_code", "ingestion_errors", ["error_code"])
    op.create_index("ix_ingestion_errors_external_id", "ingestion_errors", ["external_id"])
    op.create_index(
        "ix_ingestion_errors_ingestion_run_id",
        "ingestion_errors",
        ["ingestion_run_id"],
    )
    op.create_index("ix_ingestion_errors_occurred_at", "ingestion_errors", ["occurred_at"])
    op.create_index("ix_ingestion_errors_venue_id", "ingestion_errors", ["venue_id"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_errors_venue_id", table_name="ingestion_errors")
    op.drop_index("ix_ingestion_errors_occurred_at", table_name="ingestion_errors")
    op.drop_index("ix_ingestion_errors_ingestion_run_id", table_name="ingestion_errors")
    op.drop_index("ix_ingestion_errors_external_id", table_name="ingestion_errors")
    op.drop_index("ix_ingestion_errors_error_code", table_name="ingestion_errors")
    op.drop_table("ingestion_errors")

    op.drop_index("ix_ingestion_runs_venue_name", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_venue_id", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_status", table_name="ingestion_runs")
    op.drop_index("ix_ingestion_runs_started_at", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")

    op.drop_index("ix_venue_market_mappings_venue_name", table_name="venue_market_mappings")
    op.drop_index("ix_venue_market_mappings_venue_id", table_name="venue_market_mappings")
    op.drop_index("ix_venue_market_mappings_status", table_name="venue_market_mappings")
    op.drop_index("ix_venue_market_mappings_last_seen_at", table_name="venue_market_mappings")
    op.drop_index(
        "ix_venue_market_mappings_external_market_id",
        table_name="venue_market_mappings",
    )
    op.drop_index(
        "ix_venue_market_mappings_canonical_market_id",
        table_name="venue_market_mappings",
    )
    op.drop_index(
        "ix_venue_market_mappings_canonical_event_id",
        table_name="venue_market_mappings",
    )
    op.drop_table("venue_market_mappings")

    op.drop_index("ix_raw_venue_payloads_venue_name", table_name="raw_venue_payloads")
    op.drop_index("ix_raw_venue_payloads_venue_id", table_name="raw_venue_payloads")
    op.drop_index("ix_raw_venue_payloads_response_hash", table_name="raw_venue_payloads")
    op.drop_index("ix_raw_venue_payloads_external_id", table_name="raw_venue_payloads")
    op.drop_index("ix_raw_venue_payloads_endpoint_type", table_name="raw_venue_payloads")
    op.drop_index("ix_raw_venue_payloads_captured_at", table_name="raw_venue_payloads")
    op.drop_table("raw_venue_payloads")
