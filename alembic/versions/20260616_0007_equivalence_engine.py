"""Add cross-venue equivalence engine.

Revision ID: 20260616_0007
Revises: 20260616_0006
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260616_0007"
down_revision = "20260616_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "equivalence_candidates",
        sa.Column("candidate_id", sa.String(length=128), nullable=False),
        sa.Column("left_market_id", sa.String(length=128), nullable=False),
        sa.Column("right_market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("candidate_score", sa.Integer(), nullable=False),
        sa.Column("candidate_reasons", sa.JSON(), nullable=False),
        sa.Column("left_venue_id", sa.String(length=128), nullable=True),
        sa.Column("right_venue_id", sa.String(length=128), nullable=True),
        sa.Column("title_similarity_score", sa.Integer(), nullable=False),
        sa.Column("category_match", sa.Boolean(), nullable=False),
        sa.Column("shared_tokens", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["left_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["right_market_id"], ["markets.market_id"]),
        sa.PrimaryKeyConstraint("candidate_id"),
    )
    for column in (
        "asof_timestamp",
        "candidate_score",
        "input_hash",
        "left_market_id",
        "left_venue_id",
        "right_market_id",
        "right_venue_id",
    ):
        op.create_index(f"ix_equivalence_candidates_{column}", "equivalence_candidates", [column])

    op.create_table(
        "market_equivalence_assessments",
        sa.Column("equivalence_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("left_market_id", sa.String(length=128), nullable=False),
        sa.Column("right_market_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_rule_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("right_rule_snapshot_id", sa.String(length=128), nullable=True),
        sa.Column("left_rule_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("right_rule_snapshot_hash", sa.String(length=64), nullable=True),
        sa.Column("left_resolution_predicate_id", sa.String(length=128), nullable=True),
        sa.Column("right_resolution_predicate_id", sa.String(length=128), nullable=True),
        sa.Column("left_ambiguity_assessment_id", sa.String(length=128), nullable=True),
        sa.Column("right_ambiguity_assessment_id", sa.String(length=128), nullable=True),
        sa.Column("left_venue_id", sa.String(length=128), nullable=True),
        sa.Column("right_venue_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("comparison_permission", sa.String(length=64), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("title_similarity_score", sa.Integer(), nullable=False),
        sa.Column("event_identity_score", sa.Integer(), nullable=False),
        sa.Column("outcome_structure_score", sa.Integer(), nullable=False),
        sa.Column("outcome_mapping_score", sa.Integer(), nullable=False),
        sa.Column("predicate_similarity_score", sa.Integer(), nullable=False),
        sa.Column("resolution_source_score", sa.Integer(), nullable=False),
        sa.Column("settlement_authority_score", sa.Integer(), nullable=False),
        sa.Column("temporal_alignment_score", sa.Integer(), nullable=False),
        sa.Column("threshold_alignment_score", sa.Integer(), nullable=False),
        sa.Column("timezone_alignment_score", sa.Integer(), nullable=False),
        sa.Column("ambiguity_compatibility_score", sa.Integer(), nullable=False),
        sa.Column("venue_rule_compatibility_score", sa.Integer(), nullable=False),
        sa.Column("same_venue", sa.Boolean(), nullable=False),
        sa.Column("same_event_likely", sa.Boolean(), nullable=False),
        sa.Column("same_outcome_universe_likely", sa.Boolean(), nullable=False),
        sa.Column("inverse_outcome_likely", sa.Boolean(), nullable=False),
        sa.Column("resolution_source_mismatch", sa.Boolean(), nullable=False),
        sa.Column("settlement_authority_mismatch", sa.Boolean(), nullable=False),
        sa.Column("deadline_mismatch", sa.Boolean(), nullable=False),
        sa.Column("timezone_mismatch", sa.Boolean(), nullable=False),
        sa.Column("threshold_mismatch", sa.Boolean(), nullable=False),
        sa.Column("high_ambiguity", sa.Boolean(), nullable=False),
        sa.Column("insufficient_rule_data", sa.Boolean(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["left_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["right_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(
            ["left_rule_snapshot_id"],
            ["market_rule_snapshots.rule_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_rule_snapshot_id"],
            ["market_rule_snapshots.rule_snapshot_id"],
        ),
        sa.ForeignKeyConstraint(
            ["left_resolution_predicate_id"],
            ["resolution_predicates.predicate_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_resolution_predicate_id"],
            ["resolution_predicates.predicate_id"],
        ),
        sa.ForeignKeyConstraint(
            ["left_ambiguity_assessment_id"],
            ["ambiguity_assessments.assessment_id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_ambiguity_assessment_id"],
            ["ambiguity_assessments.assessment_id"],
        ),
        sa.PrimaryKeyConstraint("equivalence_assessment_id"),
    )
    for column in (
        "asof_timestamp",
        "available_at",
        "comparison_permission",
        "input_hash",
        "left_market_id",
        "left_venue_id",
        "output_hash",
        "overall_score",
        "right_market_id",
        "right_venue_id",
        "status",
    ):
        op.create_index(
            f"ix_market_equivalence_assessments_{column}",
            "market_equivalence_assessments",
            [column],
        )

    op.create_table(
        "outcome_equivalence_mappings",
        sa.Column("outcome_mapping_id", sa.String(length=128), nullable=False),
        sa.Column("equivalence_assessment_id", sa.String(length=128), nullable=False),
        sa.Column("left_market_id", sa.String(length=128), nullable=False),
        sa.Column("right_market_id", sa.String(length=128), nullable=False),
        sa.Column("left_outcome_id", sa.String(length=128), nullable=True),
        sa.Column("right_outcome_id", sa.String(length=128), nullable=True),
        sa.Column("left_label", sa.String(length=256), nullable=True),
        sa.Column("right_label", sa.String(length=256), nullable=True),
        sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["equivalence_assessment_id"],
            ["market_equivalence_assessments.equivalence_assessment_id"],
        ),
        sa.ForeignKeyConstraint(["left_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["right_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["left_outcome_id"], ["outcomes.outcome_id"]),
        sa.ForeignKeyConstraint(["right_outcome_id"], ["outcomes.outcome_id"]),
        sa.PrimaryKeyConstraint("outcome_mapping_id"),
    )
    for column in ("equivalence_assessment_id", "left_market_id", "relation", "right_market_id"):
        op.create_index(
            f"ix_outcome_equivalence_mappings_{column}",
            "outcome_equivalence_mappings",
            [column],
        )

    op.create_table(
        "equivalence_classes",
        sa.Column("equivalence_class_id", sa.String(length=128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("representative_title", sa.String(length=512), nullable=True),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("assessment_ids", sa.JSON(), nullable=False),
        sa.Column("min_pair_score", sa.Integer(), nullable=False),
        sa.Column("average_pair_score", sa.Numeric(12, 6), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("comparison_permission", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("equivalence_class_id"),
    )
    for column in ("asof_timestamp", "comparison_permission", "status"):
        op.create_index(f"ix_equivalence_classes_{column}", "equivalence_classes", [column])

    op.create_table(
        "equivalence_runs",
        sa.Column("equivalence_run_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("venue_names", sa.JSON(), nullable=False),
        sa.Column("max_pairs", sa.Integer(), nullable=False),
        sa.Column("min_candidate_score", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("candidates_created", sa.Integer(), nullable=False),
        sa.Column("assessments_created", sa.Integer(), nullable=False),
        sa.Column("classes_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("equivalence_run_id"),
    )
    for column in ("created_at", "status"):
        op.create_index(f"ix_equivalence_runs_{column}", "equivalence_runs", [column])

    op.create_table(
        "equivalence_run_summaries",
        sa.Column("summary_id", sa.String(length=128), nullable=False),
        sa.Column("equivalence_run_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_candidates", sa.Integer(), nullable=False),
        sa.Column("total_assessments", sa.Integer(), nullable=False),
        sa.Column("total_classes", sa.Integer(), nullable=False),
        sa.Column("status_counts", sa.JSON(), nullable=False),
        sa.Column("permission_counts", sa.JSON(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("comparable_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("manual_review_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("do_not_compare_rate", sa.Numeric(12, 6), nullable=False),
        sa.Column("markets_compared", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["equivalence_run_id"], ["equivalence_runs.equivalence_run_id"]),
        sa.PrimaryKeyConstraint("summary_id"),
    )
    for column in ("created_at", "equivalence_run_id"):
        op.create_index(
            f"ix_equivalence_run_summaries_{column}",
            "equivalence_run_summaries",
            [column],
        )


def downgrade() -> None:
    for table, columns in (
        ("equivalence_run_summaries", ("created_at", "equivalence_run_id")),
        ("equivalence_runs", ("created_at", "status")),
        ("equivalence_classes", ("asof_timestamp", "comparison_permission", "status")),
        (
            "outcome_equivalence_mappings",
            ("equivalence_assessment_id", "left_market_id", "relation", "right_market_id"),
        ),
        (
            "market_equivalence_assessments",
            (
                "asof_timestamp",
                "available_at",
                "comparison_permission",
                "input_hash",
                "left_market_id",
                "left_venue_id",
                "output_hash",
                "overall_score",
                "right_market_id",
                "right_venue_id",
                "status",
            ),
        ),
        (
            "equivalence_candidates",
            (
                "asof_timestamp",
                "candidate_score",
                "input_hash",
                "left_market_id",
                "left_venue_id",
                "right_market_id",
                "right_venue_id",
            ),
        ),
    ):
        for column in columns:
            op.drop_index(f"ix_{table}_{column}", table_name=table)
    op.drop_table("equivalence_run_summaries")
    op.drop_table("equivalence_runs")
    op.drop_table("equivalence_classes")
    op.drop_table("outcome_equivalence_mappings")
    op.drop_table("market_equivalence_assessments")
    op.drop_table("equivalence_candidates")
