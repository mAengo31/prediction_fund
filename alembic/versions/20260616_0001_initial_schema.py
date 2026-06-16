"""Initial prediction-desk schema.

Revision ID: 20260616_0001
Revises:
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venues",
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("jurisdiction", sa.String(length=128), nullable=True),
        sa.Column("venue_type", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("venue_id"),
    )

    op.create_table(
        "events",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.venue_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_events_venue_id", "events", ["venue_id"])

    op.create_table(
        "markets",
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("venue_id", sa.String(length=128), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("market_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("settlement_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.venue_id"]),
        sa.PrimaryKeyConstraint("market_id"),
    )
    op.create_index("ix_markets_event_id", "markets", ["event_id"])
    op.create_index("ix_markets_venue_id", "markets", ["venue_id"])

    op.create_table(
        "outcomes",
        sa.Column("outcome_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("payout", sa.Numeric(20, 10), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("outcome_id"),
    )
    op.create_index("ix_outcomes_market_id", "outcomes", ["market_id"])

    op.create_table(
        "market_rule_snapshots",
        sa.Column("rule_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_rule_text", sa.Text(), nullable=False),
        sa.Column("normalized_rule_text", sa.Text(), nullable=True),
        sa.Column("resolution_source", sa.String(length=512), nullable=True),
        sa.Column("settlement_authority", sa.String(length=512), nullable=True),
        sa.Column("time_zone", sa.String(length=128), nullable=True),
        sa.Column("rule_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("rule_snapshot_id"),
    )
    op.create_index(
        "ix_market_rule_snapshots_captured_at", "market_rule_snapshots", ["captured_at"]
    )
    op.create_index("ix_market_rule_snapshots_market_id", "market_rule_snapshots", ["market_id"])
    op.create_index("ix_market_rule_snapshots_rule_hash", "market_rule_snapshots", ["rule_hash"])

    op.create_table(
        "orderbook_snapshots",
        sa.Column("snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bids", sa.JSON(), nullable=False),
        sa.Column("asks", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("snapshot_id"),
    )
    op.create_index("ix_orderbook_snapshots_captured_at", "orderbook_snapshots", ["captured_at"])
    op.create_index("ix_orderbook_snapshots_market_id", "orderbook_snapshots", ["market_id"])

    op.create_table(
        "trade_prints",
        sa.Column("trade_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(20, 10), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 10), nullable=False),
        sa.Column("side", sa.String(length=32), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("trade_id"),
    )
    op.create_index("ix_trade_prints_executed_at", "trade_prints", ["executed_at"])
    op.create_index("ix_trade_prints_market_id", "trade_prints", ["market_id"])

    op.create_table(
        "resolution_events",
        sa.Column("resolution_event_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome_id", sa.String(length=128), nullable=True),
        sa.Column("result_label", sa.String(length=256), nullable=True),
        sa.Column("resolution_source_url", sa.String(length=1024), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["outcome_id"], ["outcomes.outcome_id"]),
        sa.PrimaryKeyConstraint("resolution_event_id"),
    )
    op.create_index("ix_resolution_events_market_id", "resolution_events", ["market_id"])
    op.create_index("ix_resolution_events_resolved_at", "resolution_events", ["resolved_at"])

    op.create_table(
        "trust_verdicts",
        sa.Column("verdict_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_integrity_score", sa.Integer(), nullable=False),
        sa.Column("resolution_risk_score", sa.Integer(), nullable=False),
        sa.Column("liquidity_risk_score", sa.Integer(), nullable=False),
        sa.Column("cross_venue_consistency_score", sa.Integer(), nullable=False),
        sa.Column("information_freshness_score", sa.Integer(), nullable=False),
        sa.Column("manipulation_risk_score", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("model_versions", sa.JSON(), nullable=False),
        sa.Column("data_versions", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("verdict_id"),
    )
    op.create_index("ix_trust_verdicts_asof_timestamp", "trust_verdicts", ["asof_timestamp"])
    op.create_index("ix_trust_verdicts_market_id", "trust_verdicts", ["market_id"])


def downgrade() -> None:
    op.drop_index("ix_trust_verdicts_market_id", table_name="trust_verdicts")
    op.drop_index("ix_trust_verdicts_asof_timestamp", table_name="trust_verdicts")
    op.drop_table("trust_verdicts")

    op.drop_index("ix_resolution_events_resolved_at", table_name="resolution_events")
    op.drop_index("ix_resolution_events_market_id", table_name="resolution_events")
    op.drop_table("resolution_events")

    op.drop_index("ix_trade_prints_market_id", table_name="trade_prints")
    op.drop_index("ix_trade_prints_executed_at", table_name="trade_prints")
    op.drop_table("trade_prints")

    op.drop_index("ix_orderbook_snapshots_market_id", table_name="orderbook_snapshots")
    op.drop_index("ix_orderbook_snapshots_captured_at", table_name="orderbook_snapshots")
    op.drop_table("orderbook_snapshots")

    op.drop_index("ix_market_rule_snapshots_rule_hash", table_name="market_rule_snapshots")
    op.drop_index("ix_market_rule_snapshots_market_id", table_name="market_rule_snapshots")
    op.drop_index("ix_market_rule_snapshots_captured_at", table_name="market_rule_snapshots")
    op.drop_table("market_rule_snapshots")

    op.drop_index("ix_outcomes_market_id", table_name="outcomes")
    op.drop_table("outcomes")

    op.drop_index("ix_markets_venue_id", table_name="markets")
    op.drop_index("ix_markets_event_id", table_name="markets")
    op.drop_table("markets")

    op.drop_index("ix_events_venue_id", table_name="events")
    op.drop_table("events")

    op.drop_table("venues")
