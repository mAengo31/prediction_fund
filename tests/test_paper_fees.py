from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.paper.fees import compute_simulated_fee, get_fee_bps_for_venue
from prediction_desk.paper.policies import build_default_paper_execution_policy


def test_fee_calculation_decimal_only() -> None:
    assert compute_simulated_fee(Decimal("100"), Decimal("12.5")) == Decimal("0.1250000000")


def test_default_fee_is_zero_unless_configured() -> None:
    policy = build_default_paper_execution_policy(
        created_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    )

    assert get_fee_bps_for_venue(policy) == Decimal("0")

