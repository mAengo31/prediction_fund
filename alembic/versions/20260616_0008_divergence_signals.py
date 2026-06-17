"""Add cross-venue divergence signals.

Revision ID: 20260616_0008
Revises: 20260616_0007
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0008"
down_revision = "20260616_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cross_venue_divergence_snapshots",
        sa.Column("divergence_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("equivalence_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("outcome_mapping_id", sa.String(length=128), nullable=True),
        sa.Column("left_market_id", sa.String(length=128), nullable=False),
        sa.Column("right_market_id", sa.String(length=128), nullable=False),
        sa.Column("left_venue_id", sa.String(length=128), nullable=True),
        sa.Column("right_venue_id", sa.String(length=128), nullable=True),
        sa.Column("left_outcome_id", sa.String(length=128), nullable=True),
        sa.Column("right_outcome_id", sa.String(length=128), nullable=True),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equivalence_status", sa.String(length=64), nullable=False),
        sa.Column("comparison_permission", sa.String(length=64), nullable=False),
        sa.Column("equivalence_score", sa.Integer(), nullable=True),
        sa.Column("equivalence_confidence_score", sa.Integer(), nullable=True),
        sa.Column("outcome_relation", sa.String(length=64), nullable=True),
        sa.Column("left_price_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("right_price_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("left_liquidity_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("right_liquidity_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("left_quality_report_id", sa.String(length=128), nullable=True),
        sa.Column("right_quality_report_id", sa.String(length=128), nullable=True),
        sa.Column("left_integrity_assessment_id", sa.String(length=128), nullable=True),
        sa.Column("right_integrity_assessment_id", sa.String(length=128), nullable=True),
        sa.Column("left_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_price_raw", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_price_aligned", sa.Numeric(30, 10), nullable=True),
        sa.Column("left_mid", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_mid_raw", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_mid_aligned", sa.Numeric(30, 10), nullable=True),
        sa.Column("left_bid", sa.Numeric(30, 10), nullable=True),
        sa.Column("left_ask", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_bid_raw", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_ask_raw", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_bid_aligned", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_ask_aligned", sa.Numeric(30, 10), nullable=True),
        sa.Column("signed_mid_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("absolute_mid_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("signed_price_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("absolute_price_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("gap_bps", sa.Numeric(30, 10), nullable=True),
        sa.Column("combined_spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread_adjusted_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("left_spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("left_total_depth", sa.Numeric(30, 10), nullable=True),
        sa.Column("right_total_depth", sa.Numeric(30, 10), nullable=True),
        sa.Column("min_total_depth", sa.Numeric(30, 10), nullable=True),
        sa.Column("left_quality_score", sa.Integer(), nullable=True),
        sa.Column("right_quality_score", sa.Integer(), nullable=True),
        sa.Column("left_integrity_risk_score", sa.Integer(), nullable=True),
        sa.Column("right_integrity_risk_score", sa.Integer(), nullable=True),
        sa.Column("stale_side", sa.String(length=32), nullable=True),
        sa.Column("weaker_side", sa.String(length=32), nullable=True),
        sa.Column("comparable", sa.Boolean(), nullable=False),
        sa.Column("comparable_with_haircut", sa.Boolean(), nullable=False),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False),
        sa.Column("do_not_compare", sa.Boolean(), nullable=False),
        sa.Column("missing_price_data", sa.Boolean(), nullable=False),
        sa.Column("missing_liquidity_data", sa.Boolean(), nullable=False),
        sa.Column("stale_data", sa.Boolean(), nullable=False),
        sa.Column("low_quality_data", sa.Boolean(), nullable=False),
        sa.Column("high_integrity_risk", sa.Boolean(), nullable=False),
        sa.Column("wide_spread", sa.Boolean(), nullable=False),
        sa.Column("one_sided_or_empty_book", sa.Boolean(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["equivalence_assessment_id"],
            ["market_equivalence_assessments.equivalence_assessment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["outcome_mapping_id"],
            ["outcome_equivalence_mappings.outcome_mapping_id"],
        ),
        sa.ForeignKeyConstraint(["left_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["right_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["left_outcome_id"], ["outcomes.outcome_id"]),
        sa.ForeignKeyConstraint(["right_outcome_id"], ["outcomes.outcome_id"]),
        sa.ForeignKeyConstraint(
            ["left_price_snapshot_id"],
            ["market_price_snapshots.price_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_price_snapshot_id"],
            ["market_price_snapshots.price_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["left_liquidity_snapshot_id"],
            ["market_liquidity_snapshots.liquidity_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_liquidity_snapshot_id"],
            ["market_liquidity_snapshots.liquidity_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["left_quality_report_id"],
            ["market_data_quality_reports.quality_report_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_quality_report_id"],
            ["market_data_quality_reports.quality_report_id"],
        ),
        sa.ForeignKeyConstraint(
            ["left_integrity_assessment_id"],
            ["integrity_assessments.integrity_assessment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_integrity_assessment_id"],
            ["integrity_assessments.integrity_assessment_id"],
        ),
        sa.PrimaryKeyConstraint("divergence_snapshot_id"),
    )
    _indexes(
        "cross_venue_divergence_snapshots",
        (
            "asof_timestamp",
            "available_at",
            "comparison_permission",
            "equivalence_assessment_id",
            "equivalence_status",
            "input_hash",
            "left_market_id",
            "left_venue_id",
            "outcome_relation",
            "output_hash",
            "right_market_id",
            "right_venue_id",
        ),
    )

    op.create_table(
        "cross_venue_divergence_signals",
        sa.Column("divergence_signal_id", sa.String(length=128), nullable=False),
        sa.Column("divergence_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("equivalence_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("left_market_id", sa.String(length=128), nullable=False),
        sa.Column("right_market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
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
            ["divergence_snapshot_id"],
            ["cross_venue_divergence_snapshots.divergence_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["equivalence_assessment_id"],
            ["market_equivalence_assessments.equivalence_assessment_id"],
        ),
        sa.ForeignKeyConstraint(["left_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["right_market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("divergence_signal_id"),
    )
    _indexes(
        "cross_venue_divergence_signals",
        (
            "action_hint",
            "asof_timestamp",
            "available_at",
            "category",
            "divergence_snapshot_id",
            "equivalence_assessment_id",
            "input_hash",
            "left_market_id",
            "output_hash",
            "reason_code",
            "right_market_id",
            "severity",
            "signal_name",
        ),
    )

    op.create_table(
        "cross_venue_divergence_assessments",
        sa.Column("divergence_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("divergence_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("equivalence_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("outcome_mapping_id", sa.String(length=128), nullable=True),
        sa.Column("left_market_id", sa.String(length=128), nullable=False),
        sa.Column("right_market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_ids", sa.JSON(), nullable=False),
        sa.Column("overall_divergence_score", sa.Integer(), nullable=False),
        sa.Column("price_divergence_score", sa.Integer(), nullable=False),
        sa.Column("spread_adjusted_score", sa.Integer(), nullable=False),
        sa.Column("persistence_score", sa.Integer(), nullable=False),
        sa.Column("stale_side_score", sa.Integer(), nullable=False),
        sa.Column("low_liquidity_score", sa.Integer(), nullable=False),
        sa.Column("low_data_quality_score", sa.Integer(), nullable=False),
        sa.Column("integrity_context_score", sa.Integer(), nullable=False),
        sa.Column("equivalence_context_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=64), nullable=False),
        sa.Column("action_hint", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("absolute_mid_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("spread_adjusted_gap", sa.Numeric(30, 10), nullable=True),
        sa.Column("gap_bps", sa.Numeric(30, 10), nullable=True),
        sa.Column("comparison_permission", sa.String(length=64), nullable=False),
        sa.Column("equivalence_score", sa.Integer(), nullable=True),
        sa.Column("equivalence_confidence_score", sa.Integer(), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["divergence_snapshot_id"],
            ["cross_venue_divergence_snapshots.divergence_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["equivalence_assessment_id"],
            ["market_equivalence_assessments.equivalence_assessment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["outcome_mapping_id"],
            ["outcome_equivalence_mappings.outcome_mapping_id"],
        ),
        sa.ForeignKeyConstraint(["left_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["right_market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("divergence_assessment_id"),
    )
    _indexes(
        "cross_venue_divergence_assessments",
        (
            "action_hint",
            "asof_timestamp",
            "available_at",
            "comparison_permission",
            "divergence_snapshot_id",
            "equivalence_assessment_id",
            "input_hash",
            "left_market_id",
            "output_hash",
            "overall_divergence_score",
            "right_market_id",
            "severity",
            "status",
        ),
    )

    op.create_table(
        "cross_venue_divergence_runs",
        sa.Column("divergence_run_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equivalence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("max_pairs", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("snapshots_created", sa.Integer(), nullable=False),
        sa.Column("signals_created", sa.Integer(), nullable=False),
        sa.Column("assessments_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("divergence_run_id"),
    )
    _indexes("cross_venue_divergence_runs", ("created_at", "status"))

    op.create_table(
        "cross_venue_divergence_run_summaries",
        sa.Column("summary_id", sa.String(length=128), nullable=False),
        sa.Column("divergence_run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_snapshots", sa.Integer(), nullable=False),
        sa.Column("total_signals", sa.Integer(), nullable=False),
        sa.Column("total_assessments", sa.Integer(), nullable=False),
        sa.Column("status_counts", sa.JSON(), nullable=False),
        sa.Column("severity_counts", sa.JSON(), nullable=False),
        sa.Column("action_hint_counts", sa.JSON(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("watch_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("material_divergence_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("needs_review_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("do_not_compare_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("markets_compared", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["divergence_run_id"],
            ["cross_venue_divergence_runs.divergence_run_id"],
        ),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    _indexes("cross_venue_divergence_run_summaries", ("created_at", "divergence_run_id"))


def downgrade() -> None:
    for table, columns in (
        ("cross_venue_divergence_run_summaries", ("created_at", "divergence_run_id")),
        ("cross_venue_divergence_runs", ("created_at", "status")),
        (
            "cross_venue_divergence_assessments",
            (
                "action_hint",
                "asof_timestamp",
                "available_at",
                "comparison_permission",
                "divergence_snapshot_id",
                "equivalence_assessment_id",
                "input_hash",
                "left_market_id",
                "output_hash",
                "overall_divergence_score",
                "right_market_id",
                "severity",
                "status",
            ),
        ),
        (
            "cross_venue_divergence_signals",
            (
                "action_hint",
                "asof_timestamp",
                "available_at",
                "category",
                "divergence_snapshot_id",
                "equivalence_assessment_id",
                "input_hash",
                "left_market_id",
                "output_hash",
                "reason_code",
                "right_market_id",
                "severity",
                "signal_name",
            ),
        ),
        (
            "cross_venue_divergence_snapshots",
            (
                "asof_timestamp",
                "available_at",
                "comparison_permission",
                "equivalence_assessment_id",
                "equivalence_status",
                "input_hash",
                "left_market_id",
                "left_venue_id",
                "outcome_relation",
                "output_hash",
                "right_market_id",
                "right_venue_id",
            ),
        ),
    ):
        for column in columns:
            op.drop_index(f"ix_{table}_{column}", table_name=table)
    for table in (
        "cross_venue_divergence_run_summaries",
        "cross_venue_divergence_runs",
        "cross_venue_divergence_assessments",
        "cross_venue_divergence_signals",
        "cross_venue_divergence_snapshots",
    ):
        op.drop_table(table)


def _indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])

