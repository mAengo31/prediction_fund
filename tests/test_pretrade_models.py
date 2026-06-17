from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from prediction_desk.pretrade.enums import StrategyContext, TradeIntentType, TradeSide
from prediction_desk.pretrade.models import TradeIntent, compute_trade_intent_id


def test_trade_intent_validates_positive_size() -> None:
    with pytest.raises(ValidationError):
        TradeIntent(
            trade_intent_id="pending",
            market_id="mkt_test",
            strategy_context=StrategyContext.RESEARCH,
            side=TradeSide.BUY,
            intent_type=TradeIntentType.RESEARCH_ONLY,
            requested_size_units=Decimal("0"),
            asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
        )


def test_trade_intent_rejects_out_of_bounds_price() -> None:
    with pytest.raises(ValidationError):
        TradeIntent(
            trade_intent_id="pending",
            market_id="mkt_test",
            strategy_context=StrategyContext.RESEARCH,
            side=TradeSide.BUY,
            intent_type=TradeIntentType.RESEARCH_ONLY,
            requested_price=Decimal("1.01"),
            requested_size_units=Decimal("1"),
            asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
        )


def test_trade_intent_hash_is_deterministic() -> None:
    intent = TradeIntent(
        trade_intent_id="pending",
        market_id="mkt_test",
        strategy_context=StrategyContext.RESEARCH,
        side=TradeSide.BUY,
        intent_type=TradeIntentType.RESEARCH_ONLY,
        requested_size_units=Decimal("1"),
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
    )

    assert compute_trade_intent_id(intent) == compute_trade_intent_id(intent)
