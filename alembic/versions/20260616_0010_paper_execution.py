"""Add paper execution simulation schema.

Revision ID: 20260616_0010
Revises: 20260616_0009
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0010"
down_revision = "20260616_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_execution_policies",
        sa.Column("paper_policy_id", sa.String(128), nullable=False),
        sa.Column("policy_name", sa.String(128), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("allow_simulated_shorts", sa.Boolean(), nullable=False),
        sa.Column("allow_partial_fills", sa.Boolean(), nullable=False),
        sa.Column("default_fee_bps", sa.Numeric(30, 10), nullable=False),
        sa.Column("max_slippage_bps", sa.Numeric(30, 10), nullable=True),
        sa.Column("require_pretrade_allow", sa.Boolean(), nullable=False),
        sa.Column("allow_pretrade_allow_smaller_size", sa.Boolean(), nullable=False),
        sa.Column("allow_pretrade_passive_only_for_passive_orders", sa.Boolean(), nullable=False),
        sa.Column("reject_manual_review", sa.Boolean(), nullable=False),
        sa.Column("reject_no_trade", sa.Boolean(), nullable=False),
        sa.Column("fill_model", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("paper_policy_id"),
    )
    _indexes("paper_execution_policies", ("created_at", "is_active", "policy_name"))

    op.create_table(
        "paper_orders",
        sa.Column("paper_order_id", sa.String(128), nullable=False),
        sa.Column("trade_intent_id", sa.String(128), nullable=False),
        sa.Column("pretrade_decision_id", sa.String(128), nullable=True),
        sa.Column("paper_policy_id", sa.String(128), nullable=False),
        sa.Column("simulation_run_id", sa.String(128), nullable=True),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("outcome_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("side", sa.String(32), nullable=False),
        sa.Column("intent_type", sa.String(64), nullable=False),
        sa.Column("requested_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("limit_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("requested_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("accepted_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("filled_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("remaining_size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("rejection_reason_codes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["outcome_id"], ["outcomes.outcome_id"]),
        sa.ForeignKeyConstraint(["paper_policy_id"], ["paper_execution_policies.paper_policy_id"]),
        sa.ForeignKeyConstraint(
            ["pretrade_decision_id"],
            ["pretrade_decisions.pretrade_decision_id"],
        ),
        sa.ForeignKeyConstraint(["trade_intent_id"], ["trade_intents.trade_intent_id"]),
        sa.PrimaryKeyConstraint("paper_order_id"),
    )
    _indexes(
        "paper_orders",
        (
            "asof_timestamp",
            "available_at",
            "created_at",
            "intent_type",
            "market_id",
            "paper_policy_id",
            "pretrade_decision_id",
            "simulation_run_id",
            "status",
            "trade_intent_id",
            "venue_id",
        ),
    )

    op.create_table(
        "paper_fills",
        sa.Column("paper_fill_id", sa.String(128), nullable=False),
        sa.Column("paper_order_id", sa.String(128), nullable=False),
        sa.Column("simulation_run_id", sa.String(128), nullable=True),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("outcome_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("side", sa.String(32), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(30, 10), nullable=False),
        sa.Column("size_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("notional", sa.Numeric(30, 10), nullable=False),
        sa.Column("fee_amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("fee_bps", sa.Numeric(30, 10), nullable=False),
        sa.Column("liquidity_source", sa.String(64), nullable=False),
        sa.Column("source_orderbook_snapshot_id", sa.String(128), nullable=True),
        sa.Column("source_price_snapshot_id", sa.String(128), nullable=True),
        sa.Column("source_liquidity_snapshot_id", sa.String(128), nullable=True),
        sa.Column("fill_reason", sa.String(256), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["paper_order_id"], ["paper_orders.paper_order_id"]),
        sa.PrimaryKeyConstraint("paper_fill_id"),
    )
    _indexes(
        "paper_fills",
        ("asof_timestamp", "market_id", "paper_order_id", "simulation_run_id", "venue_id"),
    )

    op.create_table(
        "paper_ledger_entries",
        sa.Column("ledger_entry_id", sa.String(128), nullable=False),
        sa.Column("simulation_run_id", sa.String(128), nullable=True),
        sa.Column("paper_order_id", sa.String(128), nullable=True),
        sa.Column("paper_fill_id", sa.String(128), nullable=True),
        sa.Column("market_id", sa.String(128), nullable=True),
        sa.Column("outcome_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("entry_type", sa.String(64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount", sa.Numeric(30, 10), nullable=False),
        sa.Column("currency", sa.String(32), nullable=False),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("ledger_entry_id"),
    )
    _indexes(
        "paper_ledger_entries",
        (
            "entry_type",
            "market_id",
            "occurred_at",
            "paper_fill_id",
            "paper_order_id",
            "simulation_run_id",
            "venue_id",
        ),
    )

    op.create_table(
        "paper_position_snapshots",
        sa.Column("position_snapshot_id", sa.String(128), nullable=False),
        sa.Column("simulation_run_id", sa.String(128), nullable=True),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("outcome_id", sa.String(128), nullable=True),
        sa.Column("venue_id", sa.String(128), nullable=True),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("position_units", sa.Numeric(30, 10), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("cost_basis", sa.Numeric(30, 10), nullable=False),
        sa.Column("realized_pnl_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("unrealized_pnl_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("mark_price", sa.Numeric(30, 10), nullable=True),
        sa.Column("mark_price_snapshot_id", sa.String(128), nullable=True),
        sa.Column("is_flat", sa.Boolean(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("position_snapshot_id"),
    )
    _indexes(
        "paper_position_snapshots",
        (
            "asof_timestamp",
            "available_at",
            "is_flat",
            "market_id",
            "simulation_run_id",
            "venue_id",
        ),
    )

    op.create_table(
        "paper_portfolio_snapshots",
        sa.Column("portfolio_snapshot_id", sa.String(128), nullable=False),
        sa.Column("simulation_run_id", sa.String(128), nullable=True),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash_balance_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("gross_exposure_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("net_exposure_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("realized_pnl_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("unrealized_pnl_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_fees_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("total_equity_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("open_positions_count", sa.Integer(), nullable=False),
        sa.Column("closed_positions_count", sa.Integer(), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("portfolio_snapshot_id"),
    )
    _indexes("paper_portfolio_snapshots", ("asof_timestamp", "available_at", "simulation_run_id"))

    op.create_table(
        "paper_simulation_runs",
        sa.Column("simulation_run_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("paper_policy_id", sa.String(128), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("max_orders", sa.Integer(), nullable=False),
        sa.Column("initial_cash_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("orders_created", sa.Integer(), nullable=False),
        sa.Column("fills_created", sa.Integer(), nullable=False),
        sa.Column("rejected_orders", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("simulation_run_id"),
    )
    _indexes("paper_simulation_runs", ("created_at", "paper_policy_id", "status"))

    op.create_table(
        "paper_simulation_run_summaries",
        sa.Column("summary_id", sa.String(128), nullable=False),
        sa.Column("simulation_run_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_orders", sa.Integer(), nullable=False),
        sa.Column("filled_orders", sa.Integer(), nullable=False),
        sa.Column("partially_filled_orders", sa.Integer(), nullable=False),
        sa.Column("rejected_orders", sa.Integer(), nullable=False),
        sa.Column("total_fills", sa.Integer(), nullable=False),
        sa.Column("total_fees_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_cash_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_gross_exposure_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_net_exposure_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_realized_pnl_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_unrealized_pnl_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("final_total_equity_simulated", sa.Numeric(30, 10), nullable=False),
        sa.Column("fill_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("rejection_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["simulation_run_id"], ["paper_simulation_runs.simulation_run_id"]),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    _indexes("paper_simulation_run_summaries", ("created_at", "simulation_run_id"))


def downgrade() -> None:
    for table in (
        "paper_simulation_run_summaries",
        "paper_simulation_runs",
        "paper_portfolio_snapshots",
        "paper_position_snapshots",
        "paper_ledger_entries",
        "paper_fills",
        "paper_orders",
        "paper_execution_policies",
    ):
        op.drop_table(table)


def _indexes(table_name: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table_name}_{column}", table_name, [column])
