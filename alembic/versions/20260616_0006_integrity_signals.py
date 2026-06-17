"""Add fast-lane integrity signals.

Revision ID: 20260616_0006
Revises: 20260616_0005
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0006"
down_revision = "20260616_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_feature_snapshots",
        sa.Column("feature_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latest_price_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("previous_price_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("latest_liquidity_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("previous_liquidity_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("latest_quality_report_id", sa.String(length=256), nullable=True),
        sa.Column("latest_rule_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("latest_rule_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("latest_rule_diff_id", sa.String(length=128), nullable=True),
        sa.Column("price", sa.Numeric(30, 10), nullable=True),
        sa.Column("bid", sa.Numeric(30, 10), nullable=True),
        sa.Column("ask", sa.Numeric(30, 10), nullable=True),
        sa.Column("mid", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread_bps", sa.Numeric(30, 10), nullable=True),
        sa.Column("total_bid_depth", sa.Numeric(30, 10), nullable=True),
        sa.Column("total_ask_depth", sa.Numeric(30, 10), nullable=True),
        sa.Column("total_depth", sa.Numeric(30, 10), nullable=True),
        sa.Column("book_imbalance", sa.Numeric(30, 10), nullable=True),
        sa.Column("is_empty_book", sa.Boolean(), nullable=False),
        sa.Column("is_crossed_book", sa.Boolean(), nullable=False),
        sa.Column("has_missing_bid_or_ask", sa.Boolean(), nullable=False),
        sa.Column("market_data_quality_score", sa.Integer(), nullable=True),
        sa.Column("market_data_quality_reason_codes", sa.JSON(), nullable=False),
        sa.Column("freshness_seconds", sa.Integer(), nullable=True),
        sa.Column("price_change_abs", sa.Numeric(30, 10), nullable=True),
        sa.Column("price_change_pct", sa.Numeric(30, 10), nullable=True),
        sa.Column("mid_change_abs", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread_change_abs", sa.Numeric(30, 10), nullable=True),
        sa.Column("depth_change_pct", sa.Numeric(30, 10), nullable=True),
        sa.Column("rule_changed_recently", sa.Boolean(), nullable=False),
        sa.Column("rule_change_age_seconds", sa.Integer(), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["latest_rule_diff_id"], ["rule_snapshot_diffs.diff_id"]),
        sa.ForeignKeyConstraint(
            ["latest_quality_report_id"],
            ["market_data_quality_reports.quality_report_id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_liquidity_snapshot_id"],
            ["market_liquidity_snapshots.liquidity_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["previous_liquidity_snapshot_id"],
            ["market_liquidity_snapshots.liquidity_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_price_snapshot_id"],
            ["market_price_snapshots.price_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["previous_price_snapshot_id"],
            ["market_price_snapshots.price_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["latest_rule_snapshot_id"],
            ["market_rule_snapshots.rule_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("feature_snapshot_id"),
    )
    for column in ("asof_timestamp", "available_at", "input_hash", "market_id"):
        op.create_index(
            f"ix_market_feature_snapshots_{column}",
            "market_feature_snapshots",
            [column],
        )

    op.create_table(
        "integrity_signals",
        sa.Column("integrity_signal_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("signal_name", sa.String(length=128), nullable=False),
        sa.Column("signal_version", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("action_hint", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["feature_snapshot_id"],
            ["market_feature_snapshots.feature_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("integrity_signal_id"),
    )
    for column in (
        "action_hint",
        "asof_timestamp",
        "available_at",
        "category",
        "feature_snapshot_id",
        "input_hash",
        "market_id",
        "output_hash",
        "reason_code",
        "severity",
        "signal_name",
    ):
        op.create_index(f"ix_integrity_signals_{column}", "integrity_signals", [column])

    op.create_table(
        "integrity_assessments",
        sa.Column("integrity_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("signal_ids", sa.JSON(), nullable=False),
        sa.Column("overall_risk_score", sa.Integer(), nullable=False),
        sa.Column("price_anomaly_score", sa.Integer(), nullable=False),
        sa.Column("liquidity_anomaly_score", sa.Integer(), nullable=False),
        sa.Column("freshness_risk_score", sa.Integer(), nullable=False),
        sa.Column("orderbook_structure_score", sa.Integer(), nullable=False),
        sa.Column("rule_change_risk_score", sa.Integer(), nullable=False),
        sa.Column("rule_price_coupling_score", sa.Integer(), nullable=False),
        sa.Column("data_quality_risk_score", sa.Integer(), nullable=False),
        sa.Column("manipulation_proxy_score", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("action_hint", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["feature_snapshot_id"],
            ["market_feature_snapshots.feature_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("integrity_assessment_id"),
    )
    for column in (
        "action_hint",
        "asof_timestamp",
        "available_at",
        "feature_snapshot_id",
        "input_hash",
        "market_id",
        "output_hash",
        "severity",
    ):
        op.create_index(
            f"ix_integrity_assessments_{column}",
            "integrity_assessments",
            [column],
        )

    op.create_table(
        "integrity_runs",
        sa.Column("integrity_run_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_seconds", sa.Integer(), nullable=True),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("assessments_created", sa.Integer(), nullable=False),
        sa.Column("signals_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("integrity_run_id"),
    )
    for column in ("created_at", "status"):
        op.create_index(f"ix_integrity_runs_{column}", "integrity_runs", [column])

    op.create_table(
        "integrity_run_summaries",
        sa.Column("summary_id", sa.String(length=128), nullable=False),
        sa.Column("integrity_run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_assessments", sa.Integer(), nullable=False),
        sa.Column("total_signals", sa.Integer(), nullable=False),
        sa.Column("severity_counts", sa.JSON(), nullable=False),
        sa.Column("category_counts", sa.JSON(), nullable=False),
        sa.Column("action_hint_counts", sa.JSON(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("no_trade_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("manual_review_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("passive_only_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("allow_smaller_size_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("markets_scanned", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["integrity_run_id"], ["integrity_runs.integrity_run_id"]),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    op.create_index(
        "ix_integrity_run_summaries_created_at",
        "integrity_run_summaries",
        ["created_at"],
    )
    op.create_index(
        "ix_integrity_run_summaries_integrity_run_id",
        "integrity_run_summaries",
        ["integrity_run_id"],
    )


def downgrade() -> None:
    for column in ("integrity_run_id", "created_at"):
        op.drop_index(
            f"ix_integrity_run_summaries_{column}",
            table_name="integrity_run_summaries",
        )
    op.drop_table("integrity_run_summaries")
    for column in ("status", "created_at"):
        op.drop_index(f"ix_integrity_runs_{column}", table_name="integrity_runs")
    op.drop_table("integrity_runs")
    for column in (
        "severity",
        "output_hash",
        "market_id",
        "input_hash",
        "feature_snapshot_id",
        "available_at",
        "asof_timestamp",
        "action_hint",
    ):
        op.drop_index(f"ix_integrity_assessments_{column}", table_name="integrity_assessments")
    op.drop_table("integrity_assessments")
    for column in (
        "signal_name",
        "severity",
        "reason_code",
        "output_hash",
        "market_id",
        "input_hash",
        "feature_snapshot_id",
        "category",
        "available_at",
        "asof_timestamp",
        "action_hint",
    ):
        op.drop_index(f"ix_integrity_signals_{column}", table_name="integrity_signals")
    op.drop_table("integrity_signals")
    for column in ("market_id", "input_hash", "available_at", "asof_timestamp"):
        op.drop_index(
            f"ix_market_feature_snapshots_{column}",
            table_name="market_feature_snapshots",
        )
    op.drop_table("market_feature_snapshots")
