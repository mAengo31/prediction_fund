"""Add desk decision workbench schema.

Revision ID: 20260618_0015
Revises: 20260618_0014
Create Date: 2026-06-18 00:15:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260618_0015"
down_revision = "20260618_0014"
branch_labels = None
depends_on = None


def _idxs(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "desk_watchlists",
        sa.Column("watchlist_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("desk_watchlists", ("name", "created_at", "is_active"))

    op.create_table(
        "market_review_queue_items",
        sa.Column("queue_item_id", sa.String(128), primary_key=True),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("queue_name", sa.String(128), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False),
        sa.Column("priority_bucket", sa.String(64), nullable=False),
        sa.Column("review_status", sa.String(64), nullable=False),
        sa.Column("primary_reason_code", sa.String(128), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("evidence_ref_ids", sa.JSON(), nullable=False),
        sa.Column("latest_quality_report_id", sa.String(128)),
        sa.Column("latest_integrity_assessment_id", sa.String(128)),
        sa.Column("latest_equivalence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("latest_divergence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("latest_pretrade_decision_id", sa.String(128)),
        sa.Column("latest_research_signal_ids", sa.JSON(), nullable=False),
        sa.Column("latest_paper_order_ids", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "market_review_queue_items",
        (
            "market_id",
            "asof_timestamp",
            "generated_at",
            "available_at",
            "queue_name",
            "priority_score",
            "priority_bucket",
            "review_status",
            "primary_reason_code",
        ),
    )

    op.create_table(
        "market_decision_cards",
        sa.Column("decision_card_id", sa.String(128), primary_key=True),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("venue_name", sa.String(256)),
        sa.Column("market_status", sa.String(64)),
        sa.Column("category", sa.String(128)),
        sa.Column("latest_price", sa.Numeric(30, 10)),
        sa.Column("bid", sa.Numeric(30, 10)),
        sa.Column("ask", sa.Numeric(30, 10)),
        sa.Column("spread", sa.Numeric(30, 10)),
        sa.Column("liquidity_summary", sa.JSON(), nullable=False),
        sa.Column("data_quality_summary", sa.JSON(), nullable=False),
        sa.Column("rule_summary", sa.JSON(), nullable=False),
        sa.Column("integrity_summary", sa.JSON(), nullable=False),
        sa.Column("equivalence_summary", sa.JSON(), nullable=False),
        sa.Column("divergence_summary", sa.JSON(), nullable=False),
        sa.Column("pretrade_summary", sa.JSON(), nullable=False),
        sa.Column("paper_summary", sa.JSON(), nullable=False),
        sa.Column("research_summary", sa.JSON(), nullable=False),
        sa.Column("scenario_summary", sa.JSON(), nullable=False),
        sa.Column("data_gap_summary", sa.JSON(), nullable=False),
        sa.Column("review_priority_score", sa.Integer(), nullable=False),
        sa.Column("review_reason_codes", sa.JSON(), nullable=False),
        sa.Column("recommended_next_review_action", sa.String(64), nullable=False),
        sa.Column("source_ref_ids", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "market_decision_cards",
        (
            "market_id",
            "asof_timestamp",
            "generated_at",
            "available_at",
            "venue_name",
            "market_status",
            "category",
            "review_priority_score",
            "recommended_next_review_action",
            "input_hash",
            "output_hash",
        ),
    )

    op.create_table(
        "cross_venue_comparison_cards",
        sa.Column("comparison_card_id", sa.String(128), primary_key=True),
        sa.Column("equivalence_assessment_id", sa.String(128), nullable=False),
        sa.Column("divergence_assessment_id", sa.String(128)),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_market_id", sa.String(128), nullable=False),
        sa.Column("right_market_id", sa.String(128), nullable=False),
        sa.Column("equivalence_status", sa.String(64), nullable=False),
        sa.Column("comparison_permission", sa.String(64), nullable=False),
        sa.Column("equivalence_score", sa.Integer()),
        sa.Column("divergence_status", sa.String(64)),
        sa.Column("divergence_score", sa.Integer()),
        sa.Column("aligned_price_summary", sa.JSON(), nullable=False),
        sa.Column("liquidity_comparison", sa.JSON(), nullable=False),
        sa.Column("data_quality_comparison", sa.JSON(), nullable=False),
        sa.Column("rule_comparison", sa.JSON(), nullable=False),
        sa.Column("integrity_comparison", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("recommended_next_review_action", sa.String(64), nullable=False),
        sa.Column("source_ref_ids", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "cross_venue_comparison_cards",
        (
            "equivalence_assessment_id",
            "divergence_assessment_id",
            "asof_timestamp",
            "left_market_id",
            "right_market_id",
            "equivalence_status",
            "comparison_permission",
            "divergence_status",
            "recommended_next_review_action",
        ),
    )

    op.create_table(
        "desk_review_notes",
        sa.Column("note_id", sa.String(128), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_id", sa.String(128)),
        sa.Column("queue_item_id", sa.String(128)),
        sa.Column("decision_card_id", sa.String(128)),
        sa.Column("comparison_card_id", sa.String(128)),
        sa.Column("author", sa.String(256)),
        sa.Column("note_type", sa.String(64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "desk_review_notes",
        (
            "created_at",
            "market_id",
            "queue_item_id",
            "decision_card_id",
            "comparison_card_id",
            "author",
            "note_type",
        ),
    )

    op.create_table(
        "workbench_runs",
        sa.Column("workbench_run_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("queues_built", sa.Integer(), nullable=False),
        sa.Column("cards_built", sa.Integer(), nullable=False),
        sa.Column("comparison_cards_built", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("workbench_runs", ("created_at", "status", "asof_timestamp"))

    op.create_table(
        "workbench_run_summaries",
        sa.Column("summary_id", sa.String(128), primary_key=True),
        sa.Column("workbench_run_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_queue_items", sa.Integer(), nullable=False),
        sa.Column("total_decision_cards", sa.Integer(), nullable=False),
        sa.Column("total_comparison_cards", sa.Integer(), nullable=False),
        sa.Column("priority_counts", sa.JSON(), nullable=False),
        sa.Column("review_action_counts", sa.JSON(), nullable=False),
        sa.Column("top_reason_codes", sa.JSON(), nullable=False),
        sa.Column("markets_reviewed", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs("workbench_run_summaries", ("workbench_run_id", "created_at"))


def downgrade() -> None:
    op.drop_table("workbench_run_summaries")
    op.drop_table("workbench_runs")
    op.drop_table("desk_review_notes")
    op.drop_table("cross_venue_comparison_cards")
    op.drop_table("market_decision_cards")
    op.drop_table("market_review_queue_items")
    op.drop_table("desk_watchlists")

