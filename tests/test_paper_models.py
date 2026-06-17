from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from prediction_desk.paper.enums import LiquiditySource
from prediction_desk.paper.models import PaperFill
from prediction_desk.paper.policies import build_default_paper_execution_policy
from prediction_desk.pretrade.enums import TradeSide


def test_default_paper_policy_creation_is_deterministic() -> None:
    now = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    first = build_default_paper_execution_policy(created_at=now)
    second = build_default_paper_execution_policy(created_at=now)

    assert first.paper_policy_id == second.paper_policy_id
    assert first.policy_name == "default_paper_execution_policy"
    assert not first.allow_simulated_shorts


def test_paper_fill_must_be_simulated() -> None:
    with pytest.raises(ValueError):
        PaperFill(
            paper_fill_id="fill",
            paper_order_id="order",
            market_id="market",
            side=TradeSide.BUY,
            filled_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
            asof_timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
            price=Decimal("0.5"),
            size_units=Decimal("1"),
            notional=Decimal("0.5"),
            fee_amount=Decimal("0"),
            fee_bps=Decimal("0"),
            liquidity_source=LiquiditySource.TOP_OF_BOOK,
            fill_reason="test",
            is_simulated=False,
        )

