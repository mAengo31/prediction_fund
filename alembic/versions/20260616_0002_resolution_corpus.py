"""Add resolution corpus schema.

Revision ID: 20260616_0002
Revises: 20260616_0001
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0002"
down_revision = "20260616_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resolution_sources",
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_name", sa.String(length=512), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=True),
        sa.Column("jurisdiction", sa.String(length=128), nullable=True),
        sa.Column("reliability_rank", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("source_id"),
    )
    op.create_index(
        "ix_resolution_sources_canonical_name",
        "resolution_sources",
        ["canonical_name"],
    )

    op.create_table(
        "resolution_predicates",
        sa.Column("predicate_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("rule_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predicate_type", sa.String(length=64), nullable=False),
        sa.Column("parse_status", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("threshold_value", sa.Numeric(30, 10), nullable=True),
        sa.Column("threshold_unit", sa.String(length=128), nullable=True),
        sa.Column("comparator", sa.String(length=64), nullable=True),
        sa.Column("time_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_zone", sa.String(length=128), nullable=True),
        sa.Column("resolution_source_id", sa.String(length=128), nullable=True),
        sa.Column("settlement_authority", sa.String(length=512), nullable=True),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("evidence_spans", sa.JSON(), nullable=False),
        sa.Column("normalized_predicate_text", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["resolution_source_id"], ["resolution_sources.source_id"]),
        sa.ForeignKeyConstraint(["rule_snapshot_id"], ["market_rule_snapshots.rule_snapshot_id"]),
        sa.PrimaryKeyConstraint("predicate_id"),
    )
    op.create_index(
        "ix_resolution_predicates_captured_at",
        "resolution_predicates",
        ["captured_at"],
    )
    op.create_index("ix_resolution_predicates_market_id", "resolution_predicates", ["market_id"])
    op.create_index(
        "ix_resolution_predicates_rule_snapshot_id",
        "resolution_predicates",
        ["rule_snapshot_id"],
    )

    op.create_table(
        "ambiguity_assessments",
        sa.Column("assessment_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("rule_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("source_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("temporal_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("definition_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("measurement_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("actor_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("threshold_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("dispute_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("exceptional_case_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("venue_adjudication_ambiguity_score", sa.Integer(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("evidence_spans", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["rule_snapshot_id"], ["market_rule_snapshots.rule_snapshot_id"]),
        sa.PrimaryKeyConstraint("assessment_id"),
    )
    op.create_index(
        "ix_ambiguity_assessments_captured_at",
        "ambiguity_assessments",
        ["captured_at"],
    )
    op.create_index("ix_ambiguity_assessments_market_id", "ambiguity_assessments", ["market_id"])
    op.create_index(
        "ix_ambiguity_assessments_rule_snapshot_id",
        "ambiguity_assessments",
        ["rule_snapshot_id"],
    )

    op.create_table(
        "rule_snapshot_diffs",
        sa.Column("diff_id", sa.String(length=128), nullable=False),
        sa.Column("market_id", sa.String(length=128), nullable=False),
        sa.Column("from_rule_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("to_rule_snapshot_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_text_changed", sa.Boolean(), nullable=False),
        sa.Column("normalized_text_changed", sa.Boolean(), nullable=False),
        sa.Column("resolution_source_changed", sa.Boolean(), nullable=False),
        sa.Column("settlement_authority_changed", sa.Boolean(), nullable=False),
        sa.Column("time_zone_changed", sa.Boolean(), nullable=False),
        sa.Column("old_rule_hash", sa.String(length=64), nullable=False),
        sa.Column("new_rule_hash", sa.String(length=64), nullable=False),
        sa.Column("changed_terms", sa.JSON(), nullable=False),
        sa.Column("added_text_fragments", sa.JSON(), nullable=False),
        sa.Column("removed_text_fragments", sa.JSON(), nullable=False),
        sa.Column("semantic_change_flags", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["from_rule_snapshot_id"],
            ["market_rule_snapshots.rule_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(["market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(
            ["to_rule_snapshot_id"],
            ["market_rule_snapshots.rule_snapshot_id"],
        ),
        sa.PrimaryKeyConstraint("diff_id"),
    )
    op.create_index("ix_rule_snapshot_diffs_created_at", "rule_snapshot_diffs", ["created_at"])
    op.create_index(
        "ix_rule_snapshot_diffs_from_rule_snapshot_id",
        "rule_snapshot_diffs",
        ["from_rule_snapshot_id"],
    )
    op.create_index("ix_rule_snapshot_diffs_market_id", "rule_snapshot_diffs", ["market_id"])
    op.create_index(
        "ix_rule_snapshot_diffs_to_rule_snapshot_id",
        "rule_snapshot_diffs",
        ["to_rule_snapshot_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rule_snapshot_diffs_to_rule_snapshot_id", table_name="rule_snapshot_diffs")
    op.drop_index("ix_rule_snapshot_diffs_market_id", table_name="rule_snapshot_diffs")
    op.drop_index("ix_rule_snapshot_diffs_from_rule_snapshot_id", table_name="rule_snapshot_diffs")
    op.drop_index("ix_rule_snapshot_diffs_created_at", table_name="rule_snapshot_diffs")
    op.drop_table("rule_snapshot_diffs")

    op.drop_index(
        "ix_ambiguity_assessments_rule_snapshot_id",
        table_name="ambiguity_assessments",
    )
    op.drop_index("ix_ambiguity_assessments_market_id", table_name="ambiguity_assessments")
    op.drop_index("ix_ambiguity_assessments_captured_at", table_name="ambiguity_assessments")
    op.drop_table("ambiguity_assessments")

    op.drop_index(
        "ix_resolution_predicates_rule_snapshot_id",
        table_name="resolution_predicates",
    )
    op.drop_index("ix_resolution_predicates_market_id", table_name="resolution_predicates")
    op.drop_index("ix_resolution_predicates_captured_at", table_name="resolution_predicates")
    op.drop_table("resolution_predicates")

    op.drop_index("ix_resolution_sources_canonical_name", table_name="resolution_sources")
    op.drop_table("resolution_sources")
