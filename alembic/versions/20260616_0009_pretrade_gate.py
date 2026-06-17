"""Add pre-trade gate schema.

Revision ID: 20260616_0009
Revises: 20260616_0008
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0009"
down_revision = "20260616_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trade_intents",
        sa.Column("trade_intent_id", sa.String(128), nullable=False),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("outcome_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("strategy_context", sa.String(64), nullable=False),
        sa.Column("side", sa.String(32), nullable=False),
        sa.Column("intent_type", sa.String(64), nullable=False),
        sa.Column("requested_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("requested_notional_usd", sa.Numeric(30, 10), nullable=True),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["outcome_id"], ["outcomes.outcome_id"]),
        sa.PrimaryKeyConstraint("trade_intent_id"),
    )
    _indexes(
        "trade_intents",
        ("asof_timestamp", "intent_type", "market_id", "strategy_context", "venue_id"),
    )

    op.create_table(
        "pretrade_policies",
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("policy_name", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("max_order_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("max_market_exposure_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("max_event_exposure_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("max_venue_exposure_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("max_strategy_exposure_units", sa.Numeric(30, 10), nullable=True),
        sa.Column("allow_unknown_exposure", sa.Boolean(), nullable=False),
        sa.Column("require_active_market", sa.Boolean(), nullable=False),
        sa.Column("require_rule_snapshot", sa.Boolean(), nullable=False),
        sa.Column("require_trust_verdict", sa.Boolean(), nullable=False),
        sa.Column("require_market_data_quality", sa.Boolean(), nullable=False),
        sa.Column("min_market_data_quality_score", sa.Integer(), nullable=False),
        sa.Column("max_resolution_risk_score", sa.Integer(), nullable=False),
        sa.Column("max_integrity_risk_score", sa.Integer(), nullable=False),
        sa.Column("max_divergence_score_without_review", sa.Integer(), nullable=False),
        sa.Column("max_staleness_seconds", sa.Integer(), nullable=False),
        sa.Column("max_spread", sa.Numeric(30, 10), nullable=True),
        sa.Column("max_spread_bps", sa.Numeric(30, 10), nullable=True),
        sa.Column("allow_manual_review_markets", sa.Boolean(), nullable=False),
        sa.Column("allow_comparable_with_haircut", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("policy_id"),
    )
    _indexes("pretrade_policies", ("created_at", "is_active", "policy_name"))

    op.create_table(
        "market_restriction_rules",
        sa.Column("restriction_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("restriction_type", sa.String(64), nullable=False),
        sa.Column("scope_type", sa.String(64), nullable=False),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("venue_name", sa.String(256), nullable=True),
        sa.Column("market_id", sa.String(128), nullable=True),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("title_pattern", sa.String(512), nullable=True),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("restriction_id"),
    )
    _indexes(
        "market_restriction_rules",
        (
            "category",
            "created_at",
            "event_id",
            "is_active",
            "market_id",
            "reason_code",
            "restriction_type",
            "scope_type",
            "venue_id",
            "venue_name",
        ),
    )

    op.create_table(
        "exposure_snapshots",
        sa.Column("exposure_snapshot_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("market_id", sa.String(128), nullable=True),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("strategy_context", sa.String(64), nullable=True),
        sa.Column("market_exposure_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("event_exposure_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("venue_exposure_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("strategy_exposure_units", sa.Numeric(30, 10), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["event_id"], ["events.event_id"]),
        sa.PrimaryKeyConstraint("exposure_snapshot_id"),
    )
    _indexes(
        "exposure_snapshots",
        (
            "asof_timestamp",
            "created_at",
            "event_id",
            "market_id",
            "source",
            "strategy_context",
            "venue_id",
        ),
    )

    op.create_table(
        "pretrade_input_snapshots",
        sa.Column("input_snapshot_id", sa.String(128), nullable=False),
        sa.Column("trade_intent_id", sa.String(128), nullable=False),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_status", sa.String(64), nullable=True),
        sa.Column("event_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("latest_rule_snapshot_id", sa.String(128), nullable=True),
        sa.Column("latest_rule_snapshot_hash", sa.String(64), nullable=True),
        sa.Column("latest_trust_verdict_id", sa.String(128), nullable=True),
        sa.Column("latest_quality_report_id", sa.String(128), nullable=True),
        sa.Column("latest_integrity_assessment_id", sa.String(128), nullable=True),
        sa.Column("latest_equivalence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("latest_divergence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("latest_price_snapshot_id", sa.String(128), nullable=True),
        sa.Column("latest_liquidity_snapshot_id", sa.String(128), nullable=True),
        sa.Column("exposure_snapshot_id", sa.String(128), nullable=True),
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("restriction_ids", sa.JSON(), nullable=False),
        sa.Column("resolution_risk_score", sa.Integer(), nullable=True),
        sa.Column("market_data_quality_score", sa.Integer(), nullable=True),
        sa.Column("integrity_risk_score", sa.Integer(), nullable=True),
        sa.Column("max_divergence_score", sa.Integer(), nullable=True),
        sa.Column("comparable_market_count", sa.Integer(), nullable=False),
        sa.Column("manual_review_equivalence_count", sa.Integer(), nullable=False),
        sa.Column("do_not_compare_equivalence_count", sa.Integer(), nullable=False),
        sa.Column("divergence_watch_count", sa.Integer(), nullable=False),
        sa.Column("material_divergence_count", sa.Integer(), nullable=False),
        sa.Column("divergence_needs_review_count", sa.Integer(), nullable=False),
        sa.Column("divergence_do_not_compare_count", sa.Integer(), nullable=False),
        sa.Column("current_market_exposure_units", sa.Numeric(30, 10), nullable=True),
        sa.Column("current_event_exposure_units", sa.Numeric(30, 10), nullable=True),
        sa.Column("current_venue_exposure_units", sa.Numeric(30, 10), nullable=True),
        sa.Column("current_strategy_exposure_units", sa.Numeric(30, 10), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["trade_intent_id"], ["trade_intents.trade_intent_id"]),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("input_snapshot_id"),
    )
    _indexes(
        "pretrade_input_snapshots",
        (
            "asof_timestamp",
            "available_at",
            "input_hash",
            "market_id",
            "policy_id",
            "trade_intent_id",
        ),
    )

    op.create_table(
        "pretrade_decisions",
        sa.Column("pretrade_decision_id", sa.String(128), nullable=False),
        sa.Column("trade_intent_id", sa.String(128), nullable=False),
        sa.Column("input_snapshot_id", sa.String(128), nullable=False),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_id", sa.String(128), nullable=False),
        sa.Column("policy_name", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("allowed_size_multiplier", sa.Numeric(30, 10), nullable=False),
        sa.Column("requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("max_allowed_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_allowed_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("passive_only", sa.Boolean(), nullable=False),
        sa.Column("manual_review_required", sa.Boolean(), nullable=False),
        sa.Column("hard_blocked", sa.Boolean(), nullable=False),
        sa.Column("composite_risk_score", sa.Integer(), nullable=False),
        sa.Column("resolution_risk_score", sa.Integer(), nullable=True),
        sa.Column("market_data_quality_score", sa.Integer(), nullable=True),
        sa.Column("integrity_risk_score", sa.Integer(), nullable=True),
        sa.Column("max_divergence_score", sa.Integer(), nullable=True),
        sa.Column("exposure_risk_score", sa.Integer(), nullable=True),
        sa.Column("hard_blockers", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["trade_intent_id"], ["trade_intents.trade_intent_id"]),
        sa.ForeignKeyConstraint(
            ["input_snapshot_id"],
            ["pretrade_input_snapshots.input_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("pretrade_decision_id"),
    )
    _indexes(
        "pretrade_decisions",
        (
            "action",
            "asof_timestamp",
            "available_at",
            "hard_blocked",
            "input_hash",
            "market_id",
            "output_hash",
            "policy_id",
        ),
    )

    op.create_table(
        "pretrade_runs",
        sa.Column("pretrade_run_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_id", sa.String(128), nullable=True),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("max_checks", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("decisions_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("pretrade_run_id"),
    )
    _indexes("pretrade_runs", ("created_at", "status"))

    op.create_table(
        "pretrade_run_summaries",
        sa.Column("summary_id", sa.String(128), nullable=False),
        sa.Column("pretrade_run_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_decisions", sa.Integer(), nullable=False),
        sa.Column("action_counts", sa.JSON(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("no_trade_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("manual_review_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("passive_only_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("allow_smaller_size_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("allow_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("hard_block_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("total_requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_final_allowed_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["pretrade_run_id"], ["pretrade_runs.pretrade_run_id"]),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    _indexes("pretrade_run_summaries", ("created_at", "pretrade_run_id"))


def downgrade() -> None:
    for table in (
        "pretrade_run_summaries",
        "pretrade_runs",
        "pretrade_decisions",
        "pretrade_input_snapshots",
        "exposure_snapshots",
        "market_restriction_rules",
        "pretrade_policies",
        "trade_intents",
    ):
        op.drop_table(table)


def _indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])
