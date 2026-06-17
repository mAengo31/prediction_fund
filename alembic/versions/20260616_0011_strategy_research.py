"""Add strategy research harness schema.

Revision ID: 20260616_0011
Revises: 20260616_0010
Create Date: 2026-06-16 00:11:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0011"
down_revision = "20260616_0010"
branch_labels = None
depends_on = None


def _idx(table: str, column: str, name: str | None = None) -> None:
    op.create_index(name or f"ix_{table}_{column}", table, [column])


def _idxs(table: str, columns: list[str]) -> None:
    for column in columns:
        _idx(table, column)


def upgrade() -> None:
    op.create_table(
        "research_strategy_definitions",
        sa.Column("strategy_id", sa.String(length=128), primary_key=True),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("family", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("requires_pretrade", sa.Boolean(), nullable=False),
        sa.Column("allows_paper_simulation", sa.Boolean(), nullable=False),
        sa.Column("default_requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("default_intent_type", sa.String(length=64), nullable=False),
        sa.Column("default_strategy_context", sa.String(length=64), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "research_strategy_definitions",
        ["strategy_name", "created_at", "is_active", "family"],
    )

    op.create_table(
        "research_feature_snapshots",
        sa.Column("research_feature_snapshot_id", sa.String(length=128), primary_key=True),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_source", sa.String(length=64), nullable=False),
        sa.Column("feature_family", sa.String(length=64), nullable=False),
        sa.Column("source_ref_ids", sa.JSON(), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "research_feature_snapshots",
        [
            "market_id",
            "asof_timestamp",
            "available_at",
            "feature_source",
            "input_hash",
            "output_hash",
        ],
    )

    op.create_table(
        "research_signals",
        sa.Column("research_signal_id", sa.String(length=128), primary_key=True),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("signal_strength_score", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("action_bias", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("source_feature_ids", sa.JSON(), nullable=False),
        sa.Column("source_ref_ids", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "research_signals",
        [
            "strategy_id",
            "strategy_name",
            "market_id",
            "asof_timestamp",
            "available_at",
            "signal_type",
            "input_hash",
            "output_hash",
        ],
    )

    op.create_table(
        "research_intent_proposals",
        sa.Column("proposal_id", sa.String(length=128), primary_key=True),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("strategy_name", sa.String(length=128), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("research_signal_id", sa.String(length=128)),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("outcome_id", sa.String(length=128)),
        sa.Column("venue_id", sa.String(length=128)),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("side", sa.String(length=32), nullable=False),
        sa.Column("intent_type", sa.String(length=64), nullable=False),
        sa.Column("strategy_context", sa.String(length=64), nullable=False),
        sa.Column("requested_price", sa.Numeric(30, 10)),
        sa.Column("requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("requested_notional_usd", sa.Numeric(30, 10)),
        sa.Column("pretrade_required", sa.Boolean(), nullable=False),
        sa.Column("paper_simulation_allowed", sa.Boolean(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("source_signal_ids", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "research_intent_proposals",
        [
            "strategy_id",
            "strategy_name",
            "research_signal_id",
            "market_id",
            "venue_id",
            "asof_timestamp",
            "available_at",
            "input_hash",
            "output_hash",
        ],
    )

    op.create_table(
        "research_decision_traces",
        sa.Column("trace_id", sa.String(length=128), primary_key=True),
        sa.Column("research_run_id", sa.String(length=128)),
        sa.Column("strategy_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("research_signal_id", sa.String(length=128)),
        sa.Column("proposal_id", sa.String(length=128)),
        sa.Column("trade_intent_id", sa.String(length=128)),
        sa.Column("pretrade_decision_id", sa.String(length=128)),
        sa.Column("paper_order_id", sa.String(length=128)),
        sa.Column("paper_fill_ids", sa.JSON(), nullable=False),
        sa.Column("paper_position_snapshot_id", sa.String(length=128)),
        sa.Column("paper_portfolio_snapshot_id", sa.String(length=128)),
        sa.Column("pretrade_action", sa.String(length=64)),
        sa.Column("paper_order_status", sa.String(length=64)),
        sa.Column("filled_size_units_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("avg_fill_price_simulated", sa.Numeric(30, 10)),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "research_decision_traces",
        [
            "research_run_id",
            "strategy_id",
            "market_id",
            "asof_timestamp",
            "available_at",
            "research_signal_id",
            "proposal_id",
            "pretrade_decision_id",
            "paper_order_id",
            "pretrade_action",
            "paper_order_status",
            "input_hash",
            "output_hash",
        ],
    )

    op.create_table(
        "research_runs",
        sa.Column("research_run_id", sa.String(length=128), primary_key=True),
        sa.Column("name", sa.String(length=512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("strategy_ids", sa.JSON(), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("max_steps", sa.Integer(), nullable=False),
        sa.Column("max_proposals", sa.Integer(), nullable=False),
        sa.Column("enable_paper_simulation", sa.Boolean(), nullable=False),
        sa.Column("paper_policy_id", sa.String(length=128)),
        sa.Column("initial_cash_simulated", sa.Numeric(30, 10)),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("signals_created", sa.Integer(), nullable=False),
        sa.Column("proposals_created", sa.Integer(), nullable=False),
        sa.Column("pretrade_checks_created", sa.Integer(), nullable=False),
        sa.Column("paper_orders_created", sa.Integer(), nullable=False),
        sa.Column("paper_fills_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
    )
    op.create_index("ix_research_runs_created_at", "research_runs", ["created_at"])
    op.create_index("ix_research_runs_status", "research_runs", ["status"])

    op.create_table(
        "research_run_summaries",
        sa.Column("summary_id", sa.String(length=128), primary_key=True),
        sa.Column("research_run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("total_signals", sa.Integer(), nullable=False),
        sa.Column("total_proposals", sa.Integer(), nullable=False),
        sa.Column("total_pretrade_checks", sa.Integer(), nullable=False),
        sa.Column("total_paper_orders", sa.Integer(), nullable=False),
        sa.Column("total_paper_fills", sa.Integer(), nullable=False),
        sa.Column("strategy_counts", sa.JSON(), nullable=False),
        sa.Column("signal_type_counts", sa.JSON(), nullable=False),
        sa.Column("pretrade_action_counts", sa.JSON(), nullable=False),
        sa.Column("paper_order_status_counts", sa.JSON(), nullable=False),
        sa.Column("reason_code_counts", sa.JSON(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("total_requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_pretrade_allowed_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_filled_size_units_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_portfolio_equity_simulated", sa.Numeric(30, 10)),
        sa.Column("final_realized_pnl_simulated", sa.Numeric(30, 10)),
        sa.Column("final_unrealized_pnl_simulated", sa.Numeric(30, 10)),
        sa.Column("proposal_to_pretrade_pass_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("paper_fill_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("research_run_summaries", ["research_run_id", "created_at"])

    op.create_table(
        "research_attribution_reports",
        sa.Column("attribution_report_id", sa.String(length=128), primary_key=True),
        sa.Column("research_run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("by_strategy", sa.JSON(), nullable=False),
        sa.Column("by_market", sa.JSON(), nullable=False),
        sa.Column("by_venue", sa.JSON(), nullable=False),
        sa.Column("by_reason_code", sa.JSON(), nullable=False),
        sa.Column("by_signal_type", sa.JSON(), nullable=False),
        sa.Column("by_pretrade_action", sa.JSON(), nullable=False),
        sa.Column("by_paper_order_status", sa.JSON(), nullable=False),
        sa.Column("simulated_pnl_by_strategy", sa.JSON(), nullable=False),
        sa.Column("simulated_pnl_by_market", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("research_attribution_reports", ["research_run_id", "created_at"])


def downgrade() -> None:
    op.drop_table("research_attribution_reports")
    op.drop_table("research_run_summaries")
    op.drop_table("research_runs")
    op.drop_table("research_decision_traces")
    op.drop_table("research_intent_proposals")
    op.drop_table("research_signals")
    op.drop_table("research_feature_snapshots")
    op.drop_table("research_strategy_definitions")
