"""Add point-in-time replay harness schema.

Revision ID: 20260616_0003
Revises: 20260616_0002
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0003"
down_revision = "20260616_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "replay_runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("policy_name", sa.String(length=128), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_replay_runs_created_at", "replay_runs", ["created_at"])
    op.create_index("ix_replay_runs_status", "replay_runs", ["status"])

    op.create_table(
        "replay_steps",
        sa.Column("step_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_status", sa.String(length=64), nullable=True),
        sa.Column("rule_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("rule_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("orderbook_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("resolution_predicate_id", sa.String(length=128), nullable=True),
        sa.Column("ambiguity_assessment_id", sa.String(length=128), nullable=True),
        sa.Column("trust_verdict_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("allowed_size_multiplier", sa.Numeric(12, 6), nullable=False),
        sa.Column("price_integrity_score", sa.Integer(), nullable=True),
        sa.Column("resolution_risk_score", sa.Integer(), nullable=True),
        sa.Column("liquidity_risk_score", sa.Integer(), nullable=True),
        sa.Column("cross_venue_consistency_score", sa.Integer(), nullable=True),
        sa.Column("information_freshness_score", sa.Integer(), nullable=True),
        sa.Column("manipulation_risk_score", sa.Integer(), nullable=True),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("error_code", sa.String(length=128), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ambiguity_assessment_id"],
            ["ambiguity_assessments.assessment_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["orderbook_snapshot_id"], ["orderbook_snapshots.snapshot_id"]),
        sa.ForeignKeyConstraint(
            ["resolution_predicate_id"],
            ["resolution_predicates.predicate_id"],
        ),
        sa.ForeignKeyConstraint(["rule_snapshot_id"], ["market_rule_snapshots.rule_snapshot_id"]),
        sa.ForeignKeyConstraint(["run_id"], ["replay_runs.run_id"]),
        sa.ForeignKeyConstraint(["trust_verdict_id"], ["trust_verdicts.verdict_id"]),
        sa.PrimaryKeyConstraint("step_id"),
    )
    op.create_index("ix_replay_steps_asof_timestamp", "replay_steps", ["asof_timestamp"])
    op.create_index("ix_replay_steps_input_hash", "replay_steps", ["input_hash"])
    op.create_index("ix_replay_steps_market_id", "replay_steps", ["market_id"])
    op.create_index("ix_replay_steps_output_hash", "replay_steps", ["output_hash"])
    op.create_index("ix_replay_steps_run_id", "replay_steps", ["run_id"])

    op.create_table(
        "replay_run_summaries",
        sa.Column("summary_id", sa.String(length=128), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("errored_steps", sa.Integer(), nullable=False),
        sa.Column("action_counts", sa.JSON(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("no_trade_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("manual_review_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("passive_only_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("allow_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("allowed_exposure_units", sa.Numeric(20, 6), nullable=False),
        sa.Column("blocked_exposure_units", sa.Numeric(20, 6), nullable=False),
        sa.Column("markets_replayed", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["replay_runs.run_id"]),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    op.create_index(
        "ix_replay_run_summaries_created_at",
        "replay_run_summaries",
        ["created_at"],
    )
    op.create_index("ix_replay_run_summaries_run_id", "replay_run_summaries", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_replay_run_summaries_run_id", table_name="replay_run_summaries")
    op.drop_index("ix_replay_run_summaries_created_at", table_name="replay_run_summaries")
    op.drop_table("replay_run_summaries")

    op.drop_index("ix_replay_steps_run_id", table_name="replay_steps")
    op.drop_index("ix_replay_steps_output_hash", table_name="replay_steps")
    op.drop_index("ix_replay_steps_market_id", table_name="replay_steps")
    op.drop_index("ix_replay_steps_input_hash", table_name="replay_steps")
    op.drop_index("ix_replay_steps_asof_timestamp", table_name="replay_steps")
    op.drop_table("replay_steps")

    op.drop_index("ix_replay_runs_status", table_name="replay_runs")
    op.drop_index("ix_replay_runs_created_at", table_name="replay_runs")
    op.drop_table("replay_runs")
