from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from prediction_desk.paper.enums import PaperOrderStatus
from prediction_desk.paper.fills import simulate_order_fill
from prediction_desk.paper.models import (
    PaperSimulateIntentRequest,
    compute_trade_intent_from_request,
)
from prediction_desk.paper.service import PaperExecutionService
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import RestrictionScopeType, RestrictionType
from prediction_desk.pretrade.models import MarketRestrictionRuleCreate
from prediction_desk.pretrade.service import PreTradeService
from tests.paper_helpers import ASOF, MARKET_ID, accepted_order, loaded_repo


def test_service_persists_order_fill_ledger_position_and_portfolio(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "service_fill.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        request = PaperSimulateIntentRequest(
            market_id=MARKET_ID,
            strategy_context="RESEARCH",
            side="BUY",
            intent_type="AGGRESSIVE_LIMIT",
            requested_price=Decimal("0.52"),
            requested_size_units=Decimal("1"),
            asof_timestamp=ASOF,
        )
        intent = compute_trade_intent_from_request(request, ASOF)
        result = PaperExecutionService(repo).simulate_trade_intent(intent)
        orders = repo.list_paper_orders(market_id=MARKET_ID)
        fills = repo.list_paper_fills(market_id=MARKET_ID)
        entries = repo.list_paper_ledger_entries()

    assert result.order.status == PaperOrderStatus.FILLED
    assert orders
    assert fills
    assert entries
    assert result.position_snapshot is not None
    assert result.portfolio_snapshot is not None


def test_service_rejects_pretrade_no_trade_and_creates_no_fill(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "service_reject.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        PreTradeService(repo).save_market_restriction_rule(
            MarketRestrictionRuleCreate(
                restriction_type=RestrictionType.NO_TRADE,
                scope_type=RestrictionScopeType.MARKET,
                market_id=MARKET_ID,
                reason_code="PAPER_TEST_BLOCK",
            )
        )
        request = PaperSimulateIntentRequest(
            market_id=MARKET_ID,
            strategy_context="RESEARCH",
            side="BUY",
            intent_type="AGGRESSIVE_LIMIT",
            requested_price=Decimal("0.52"),
            requested_size_units=Decimal("1"),
            asof_timestamp=ASOF,
        )
        result = PaperExecutionService(repo).simulate_trade_intent(
            compute_trade_intent_from_request(request, ASOF)
        )

    assert result.order.status == PaperOrderStatus.REJECTED
    assert "PRETRADE_NO_TRADE" in result.order.rejection_reason_codes
    assert not result.fills


def test_pretrade_allow_smaller_size_reduces_accepted_size(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "service_smaller.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        request = PaperSimulateIntentRequest(
            market_id=MARKET_ID,
            strategy_context="RESEARCH",
            side="BUY",
            intent_type="AGGRESSIVE_LIMIT",
            requested_price=Decimal("0.52"),
            requested_size_units=Decimal("2"),
            asof_timestamp=ASOF,
        )
        result = PaperExecutionService(repo).simulate_trade_intent(
            compute_trade_intent_from_request(request, ASOF)
        )

    assert result.pretrade.decision.final_allowed_size_units == Decimal("1")
    assert result.order.accepted_size_units == Decimal("1")


def test_no_market_data_produces_no_fill_reason(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "service_no_data.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        order = accepted_order(asof_timestamp=ASOF.replace(year=2025))
        result = simulate_order_fill(
            order,
            PaperExecutionService(repo).create_default_paper_execution_policy_if_missing(),
            order.asof_timestamp,
            repo=repo,
        )

    assert result.order.status == PaperOrderStatus.RESTING_UNFILLED
    assert result.reason_codes == ["MISSING_MARKET_DATA"]
