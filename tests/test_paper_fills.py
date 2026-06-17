from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.models import OrderBookSnapshot, PriceLevel
from prediction_desk.paper.enums import PaperOrderStatus
from prediction_desk.paper.fills import simulate_order_fill
from prediction_desk.paper.policies import build_default_paper_execution_policy
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import TradeIntentType, TradeSide
from tests.paper_helpers import ASOF, MARKET_ID, accepted_order, loaded_repo, long_position


def test_buy_top_of_book_fills_at_best_ask_when_allowed(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "buy_top.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = simulate_order_fill(
            accepted_order(limit_price=Decimal("0.52")),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert result.order.status == PaperOrderStatus.FILLED
    assert result.fills[0].price == Decimal("0.51")


def test_buy_limit_below_ask_does_not_fill(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "buy_below.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = simulate_order_fill(
            accepted_order(limit_price=Decimal("0.50")),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert result.order.status == PaperOrderStatus.RESTING_UNFILLED
    assert not result.fills


def test_buy_larger_than_top_depth_partially_fills(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "partial.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = simulate_order_fill(
            accepted_order(limit_price=Decimal("0.52"), size=Decimal("100")),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert result.order.status == PaperOrderStatus.PARTIALLY_FILLED
    assert result.order.filled_size_units == Decimal("90")


def test_sell_without_long_rejects_when_shorts_disabled(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "sell_no_long.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = simulate_order_fill(
            accepted_order(side=TradeSide.SELL, limit_price=Decimal("0.48")),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert result.order.status == PaperOrderStatus.REJECTED
    assert "SIMULATED_SHORTS_DISABLED" in result.order.rejection_reason_codes


def test_sell_reduces_existing_long_position(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "sell_long.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        repo.save_paper_position_snapshot(long_position(units=Decimal("2")))
        result = simulate_order_fill(
            accepted_order(side=TradeSide.SELL, limit_price=Decimal("0.48")),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert result.order.status == PaperOrderStatus.FILLED
    assert result.position_snapshot is not None
    assert result.position_snapshot.position_units == Decimal("1")


def test_passive_and_research_intents_do_not_fill(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "passive.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        passive = simulate_order_fill(
            accepted_order(intent_type=TradeIntentType.PASSIVE_LIMIT),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )
        research = simulate_order_fill(
            accepted_order(intent_type=TradeIntentType.RESEARCH_ONLY),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert passive.order.status == PaperOrderStatus.RESTING_UNFILLED
    assert research.order.status == PaperOrderStatus.RESTING_UNFILLED


def test_future_orderbook_is_not_used_for_fill_at_t(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "future_book.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        repo.save_orderbook_snapshot(
            OrderBookSnapshot(
                snapshot_id="ob_future_paper",
                market_id=MARKET_ID,
                captured_at=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                bids=[PriceLevel(price=Decimal("0.90"), quantity=Decimal("10"))],
                asks=[PriceLevel(price=Decimal("0.91"), quantity=Decimal("10"))],
                metadata={},
            )
        )
        result = simulate_order_fill(
            accepted_order(limit_price=Decimal("0.52")),
            build_default_paper_execution_policy(created_at=ASOF),
            ASOF,
            repo=repo,
        )

    assert result.fills[0].source_orderbook_snapshot_id != "ob_future_paper"
    assert result.fills[0].price == Decimal("0.51")

