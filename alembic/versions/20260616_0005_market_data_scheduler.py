"""Add canonical market data and ingestion cursors.

Revision ID: 20260616_0005
Revises: 20260616_0004
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0005"
down_revision = "20260616_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ingestion_runs",
        sa.Column("price_snapshots_created", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("liquidity_snapshots_created", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "ingestion_runs",
        sa.Column("quality_reports_created", sa.Integer(), server_default="0", nullable=False),
    )

    op.create_table(
        "market_price_snapshots",
        sa.Column("price_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("outcome_id", sa.String(length=128), nullable=True),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("venue_name", sa.String(length=256), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(30, 10), nullable=True),
        sa.Column("bid", sa.Numeric(30, 10), nullable=True),
        sa.Column("ask", sa.Numeric(30, 10), nullable=True),
        sa.Column("mid", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("last_trade_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("volume", sa.Numeric(30, 10), nullable=True),
        sa.Column("open_interest", sa.Numeric(30, 10), nullable=True),
        sa.Column("source_payload_id", sa.String(length=128), nullable=True),
        sa.Column("orderbook_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("external_market_id", sa.String(length=512), nullable=True),
        sa.Column("external_outcome_id", sa.String(length=512), nullable=True),
        sa.Column("data_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["orderbook_snapshot_id"], ["orderbook_snapshots.snapshot_id"]),
        sa.ForeignKeyConstraint(["outcome_id"], ["outcomes.outcome_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["raw_venue_payloads.payload_id"]),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.venue_id"]),
        sa.PrimaryKeyConstraint("price_snapshot_id"),
    )
    for column in (
        "available_at",
        "captured_at",
        "data_hash",
        "external_market_id",
        "market_id",
        "observed_at",
        "source",
        "venue_id",
        "venue_name",
    ):
        op.create_index(f"ix_market_price_snapshots_{column}", "market_price_snapshots", [column])

    op.create_table(
        "market_liquidity_snapshots",
        sa.Column("liquidity_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("venue_name", sa.String(length=256), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("best_bid", sa.Numeric(30, 10), nullable=True),
        sa.Column("best_ask", sa.Numeric(30, 10), nullable=True),
        sa.Column("mid_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread_bps", sa.Numeric(30, 10), nullable=True),
        sa.Column("bid_depth", sa.Numeric(30, 10), nullable=False),
        sa.Column("ask_depth", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_bid_depth", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_ask_depth", sa.Numeric(30, 10), nullable=False),
        sa.Column("book_imbalance", sa.Numeric(30, 10), nullable=True),
        sa.Column("is_empty_book", sa.Boolean(), nullable=False),
        sa.Column("is_crossed_book", sa.Boolean(), nullable=False),
        sa.Column("source_payload_id", sa.String(length=128), nullable=True),
        sa.Column("orderbook_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("data_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["orderbook_snapshot_id"], ["orderbook_snapshots.snapshot_id"]),
        sa.ForeignKeyConstraint(["source_payload_id"], ["raw_venue_payloads.payload_id"]),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.venue_id"]),
        sa.PrimaryKeyConstraint("liquidity_snapshot_id"),
    )
    for column in (
        "available_at",
        "captured_at",
        "data_hash",
        "market_id",
        "observed_at",
        "venue_id",
        "venue_name",
    ):
        op.create_index(
            f"ix_market_liquidity_snapshots_{column}",
            "market_liquidity_snapshots",
            [column],
        )

    op.create_table(
        "market_data_quality_reports",
        sa.Column("quality_report_id", sa.String(length=256), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_price_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("latest_liquidity_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("latest_orderbook_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("latest_rule_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("freshness_seconds", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("has_recent_price", sa.Boolean(), nullable=False),
        sa.Column("has_recent_orderbook", sa.Boolean(), nullable=False),
        sa.Column("has_rule_snapshot", sa.Boolean(), nullable=False),
        sa.Column("has_venue_mapping", sa.Boolean(), nullable=False),
        sa.Column("stale_market_data", sa.Boolean(), nullable=False),
        sa.Column("crossed_book", sa.Boolean(), nullable=False),
        sa.Column("empty_book", sa.Boolean(), nullable=False),
        sa.Column("wide_spread", sa.Boolean(), nullable=False),
        sa.Column("out_of_bounds_price", sa.Boolean(), nullable=False),
        sa.Column("missing_bid_or_ask", sa.Boolean(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["latest_liquidity_snapshot_id"],
            ["market_liquidity_snapshots.liquidity_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_orderbook_snapshot_id"],
            ["orderbook_snapshots.snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_price_snapshot_id"],
            ["market_price_snapshots.price_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_rule_snapshot_id"],
            ["market_rule_snapshots.rule_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("quality_report_id"),
    )
    op.create_index(
        "ix_market_data_quality_reports_asof_timestamp",
        "market_data_quality_reports",
        ["asof_timestamp"],
    )
    op.create_index(
        "ix_market_data_quality_reports_market_id",
        "market_data_quality_reports",
        ["market_id"],
    )
    op.create_index(
        "ix_market_data_quality_reports_severity",
        "market_data_quality_reports",
        ["severity"],
    )

    op.create_table(
        "ingestion_cursors",
        sa.Column("cursor_id", sa.String(length=256), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("venue_name", sa.String(length=256), nullable=False),
        sa.Column("endpoint_type", sa.String(length=64), nullable=False),
        sa.Column("external_market_id", sa.String(length=512), nullable=True),
        sa.Column("canonical_market_id", sa.String(length=128), nullable=True),
        sa.Column("cursor_value", sa.Text(), nullable=True),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("cursor_id"),
    )
    for column in (
        "canonical_market_id",
        "endpoint_type",
        "external_market_id",
        "status",
        "venue_id",
        "venue_name",
    ):
        op.create_index(f"ix_ingestion_cursors_{column}", "ingestion_cursors", [column])


def downgrade() -> None:
    for column in (
        "venue_name",
        "venue_id",
        "status",
        "external_market_id",
        "endpoint_type",
        "canonical_market_id",
    ):
        op.drop_index(f"ix_ingestion_cursors_{column}", table_name="ingestion_cursors")
    op.drop_table("ingestion_cursors")

    op.drop_index(
        "ix_market_data_quality_reports_severity",
        table_name="market_data_quality_reports",
    )
    op.drop_index(
        "ix_market_data_quality_reports_market_id",
        table_name="market_data_quality_reports",
    )
    op.drop_index(
        "ix_market_data_quality_reports_asof_timestamp",
        table_name="market_data_quality_reports",
    )
    op.drop_table("market_data_quality_reports")

    for column in (
        "venue_name",
        "venue_id",
        "observed_at",
        "market_id",
        "data_hash",
        "captured_at",
        "available_at",
    ):
        op.drop_index(
            f"ix_market_liquidity_snapshots_{column}",
            table_name="market_liquidity_snapshots",
        )
    op.drop_table("market_liquidity_snapshots")

    for column in (
        "venue_name",
        "venue_id",
        "source",
        "observed_at",
        "market_id",
        "external_market_id",
        "data_hash",
        "captured_at",
        "available_at",
    ):
        op.drop_index(f"ix_market_price_snapshots_{column}", table_name="market_price_snapshots")
    op.drop_table("market_price_snapshots")

    op.drop_column("ingestion_runs", "quality_reports_created")
    op.drop_column("ingestion_runs", "liquidity_snapshots_created")
    op.drop_column("ingestion_runs", "price_snapshots_created")
