"""Default simulated paper-execution policy construction."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.paper.enums import FillModel
from prediction_desk.paper.models import (
    DEFAULT_PAPER_POLICY_ID,
    DEFAULT_PAPER_POLICY_NAME,
    DEFAULT_PAPER_POLICY_VERSION,
    PaperExecutionPolicy,
)


def build_default_paper_execution_policy(
    *,
    created_at: datetime | None = None,
) -> PaperExecutionPolicy:
    return PaperExecutionPolicy(
        paper_policy_id=DEFAULT_PAPER_POLICY_ID,
        policy_name=DEFAULT_PAPER_POLICY_NAME,
        policy_version=DEFAULT_PAPER_POLICY_VERSION,
        created_at=created_at or datetime.now(tz=UTC),
        is_active=True,
        allow_simulated_shorts=False,
        allow_partial_fills=True,
        default_fee_bps=Decimal("0"),
        max_slippage_bps=None,
        require_pretrade_allow=True,
        allow_pretrade_allow_smaller_size=True,
        allow_pretrade_passive_only_for_passive_orders=True,
        reject_manual_review=True,
        reject_no_trade=True,
        fill_model=FillModel.IMMEDIATE_TOP_OF_BOOK,
        metadata={"description": "Deterministic conservative paper execution policy v1."},
    )

