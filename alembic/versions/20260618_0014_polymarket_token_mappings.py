"""Add venue outcome token mappings for public CLOB reads.

Revision ID: 20260618_0014
Revises: 20260617_0013
Create Date: 2026-06-18 00:14:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260618_0014"
down_revision = "20260617_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venue_outcome_token_mappings",
        sa.Column("mapping_id", sa.String(128), primary_key=True),
        sa.Column("venue_id", sa.String(128), nullable=False),
        sa.Column("venue_name", sa.String(256), nullable=False),
        sa.Column("canonical_market_id", sa.String(128), nullable=False),
        sa.Column("canonical_outcome_id", sa.String(128)),
        sa.Column("outcome_label", sa.String(256), nullable=False),
        sa.Column("external_market_id", sa.String(512)),
        sa.Column("condition_id", sa.String(512)),
        sa.Column("question_id", sa.String(512)),
        sa.Column("gamma_market_id", sa.String(512)),
        sa.Column("gamma_event_id", sa.String(512)),
        sa.Column("market_address", sa.String(512)),
        sa.Column("token_id", sa.String(512)),
        sa.Column("asset_id", sa.String(512)),
        sa.Column("token_side", sa.String(32), nullable=False),
        sa.Column("enable_orderbook", sa.Boolean()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["canonical_market_id"], ["markets.market_id"]),
        sa.ForeignKeyConstraint(["canonical_outcome_id"], ["outcomes.outcome_id"]),
    )
    for column in (
        "venue_id",
        "venue_name",
        "canonical_market_id",
        "external_market_id",
        "condition_id",
        "gamma_market_id",
        "token_id",
        "asset_id",
        "token_side",
        "last_seen_at",
        "status",
    ):
        op.create_index(
            f"ix_venue_outcome_token_mappings_{column}",
            "venue_outcome_token_mappings",
            [column],
        )


def downgrade() -> None:
    op.drop_table("venue_outcome_token_mappings")
