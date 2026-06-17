"""Add slow-lane scenario feature schema.

Revision ID: 20260617_0012
Revises: 20260616_0011
Create Date: 2026-06-17 00:12:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260617_0012"
down_revision = "20260616_0011"
branch_labels = None
depends_on = None


def _idxs(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "scenario_seed_bundles",
        sa.Column("seed_bundle_id", sa.String(128), primary_key=True),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seed_source", sa.String(64), nullable=False),
        sa.Column("market_title", sa.String(512)),
        sa.Column("market_description", sa.Text()),
        sa.Column("rule_snapshot_id", sa.String(128)),
        sa.Column("rule_snapshot_hash", sa.String(64)),
        sa.Column("resolution_predicate_id", sa.String(128)),
        sa.Column("ambiguity_assessment_id", sa.String(128)),
        sa.Column("market_data_quality_report_id", sa.String(128)),
        sa.Column("integrity_assessment_id", sa.String(128)),
        sa.Column("equivalence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("divergence_assessment_ids", sa.JSON(), nullable=False),
        sa.Column("trust_verdict_id", sa.String(128)),
        sa.Column("source_ref_ids", sa.JSON(), nullable=False),
        sa.Column("seed_text", sa.Text(), nullable=False),
        sa.Column("structured_context", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "scenario_seed_bundles",
        ("market_id", "asof_timestamp", "available_at", "seed_source", "input_hash", "output_hash"),
    )

    op.create_table(
        "scenario_simulation_specs",
        sa.Column("scenario_spec_id", sa.String(128), primary_key=True),
        sa.Column("seed_bundle_id", sa.String(128), nullable=False),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scenario_engine", sa.String(64), nullable=False),
        sa.Column("scenario_goal", sa.Text(), nullable=False),
        sa.Column("horizon_hours", sa.Integer()),
        sa.Column("requested_agent_count", sa.Integer()),
        sa.Column("requested_rounds", sa.Integer()),
        sa.Column("variables", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["seed_bundle_id"], ["scenario_seed_bundles.seed_bundle_id"]),
    )
    _idxs(
        "scenario_simulation_specs",
        ("seed_bundle_id", "market_id", "asof_timestamp", "created_at", "scenario_engine"),
    )

    op.create_table(
        "scenario_artifacts",
        sa.Column("scenario_artifact_id", sa.String(128), primary_key=True),
        sa.Column("scenario_spec_id", sa.String(128)),
        sa.Column("seed_bundle_id", sa.String(128)),
        sa.Column("market_id", sa.String(128)),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("artifact_type", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_path", sa.Text()),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("raw_text", sa.Text()),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(128), nullable=False),
        sa.Column("is_simulated", sa.Boolean(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
    )
    _idxs(
        "scenario_artifacts",
        (
            "scenario_spec_id",
            "seed_bundle_id",
            "market_id",
            "asof_timestamp",
            "available_at",
            "artifact_type",
            "source_type",
            "payload_hash",
        ),
    )

    op.create_table(
        "scenario_feature_snapshots",
        sa.Column("scenario_feature_snapshot_id", sa.String(128), primary_key=True),
        sa.Column("scenario_artifact_id", sa.String(128), nullable=False),
        sa.Column("seed_bundle_id", sa.String(128)),
        sa.Column("market_id", sa.String(128), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scenario_engine", sa.String(64), nullable=False),
        sa.Column("horizon_hours", sa.Integer()),
        sa.Column("scenario_confidence_score", sa.Integer()),
        sa.Column("scenario_uncertainty_score", sa.Integer()),
        sa.Column("sentiment_score", sa.Integer()),
        sa.Column("consensus_score", sa.Integer()),
        sa.Column("polarization_score", sa.Integer()),
        sa.Column("narrative_risk_score", sa.Integer()),
        sa.Column("shock_risk_score", sa.Integer()),
        sa.Column("adoption_or_support_score", sa.Integer()),
        sa.Column("opposition_score", sa.Integer()),
        sa.Column("key_scenario_labels", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("source_ref_ids", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scenario_artifact_id"],
            ["scenario_artifacts.scenario_artifact_id"],
        ),
    )
    _idxs(
        "scenario_feature_snapshots",
        (
            "scenario_artifact_id",
            "seed_bundle_id",
            "market_id",
            "asof_timestamp",
            "available_at",
            "scenario_engine",
            "input_hash",
            "output_hash",
        ),
    )

    op.create_table(
        "scenario_runs",
        sa.Column("scenario_run_id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("asof_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market_ids", sa.JSON(), nullable=False),
        sa.Column("mode", sa.String(64), nullable=False),
        sa.Column("max_items", sa.Integer(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("seed_bundles_created", sa.Integer(), nullable=False),
        sa.Column("specs_created", sa.Integer(), nullable=False),
        sa.Column("artifacts_imported", sa.Integer(), nullable=False),
        sa.Column("features_created", sa.Integer(), nullable=False),
        sa.Column("errors_count", sa.Integer(), nullable=False),
    )
    _idxs("scenario_runs", ("created_at", "status", "asof_timestamp", "mode"))

    op.create_table(
        "scenario_run_summaries",
        sa.Column("summary_id", sa.String(128), primary_key=True),
        sa.Column("scenario_run_id", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_seed_bundles", sa.Integer(), nullable=False),
        sa.Column("total_artifacts", sa.Integer(), nullable=False),
        sa.Column("total_features", sa.Integer(), nullable=False),
        sa.Column("average_scores", sa.JSON(), nullable=False),
        sa.Column("reason_code_counts", sa.JSON(), nullable=False),
        sa.Column("markets_processed", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_run_id"], ["scenario_runs.scenario_run_id"]),
    )
    _idxs("scenario_run_summaries", ("scenario_run_id", "created_at"))


def downgrade() -> None:
    op.drop_table("scenario_run_summaries")
    op.drop_table("scenario_runs")
    op.drop_table("scenario_feature_snapshots")
    op.drop_table("scenario_artifacts")
    op.drop_table("scenario_simulation_specs")
    op.drop_table("scenario_seed_bundles")
