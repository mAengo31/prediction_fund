"""Pydantic models for deterministic simulated paper execution."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from prediction_desk.paper.enums import (
    FillModel,
    LiquiditySource,
    PaperLedgerEntryType,
    PaperOrderStatus,
    PaperSimulationRunStatus,
)
from prediction_desk.pretrade.enums import StrategyContext, TradeIntentType, TradeSide
from prediction_desk.pretrade.models import PreTradeCheckResponse, TradeIntent

PAPER_POLICY_VERSION = "paper_execution_policy_v1"
PAPER_ORDER_VERSION = "paper_order_v1"
PAPER_FILL_VERSION = "paper_fill_v1"
PAPER_POSITION_VERSION = "paper_position_snapshot_v1"
PAPER_PORTFOLIO_VERSION = "paper_portfolio_snapshot_v1"
PAPER_RUNNER_VERSION = "paper_simulation_runner_v1"
DEFAULT_PAPER_POLICY_ID = "paper_policy_default_paper_execution_policy_v1"
DEFAULT_PAPER_POLICY_NAME = "default_paper_execution_policy"
DEFAULT_PAPER_POLICY_VERSION = "v1"


class PaperModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaperExecutionPolicy(PaperModel):
    paper_policy_id: str
    policy_name: str
    policy_version: str
    created_at: datetime
    is_active: bool = True
    allow_simulated_shorts: bool = False
    allow_partial_fills: bool = True
    default_fee_bps: Decimal = Decimal("0")
    max_slippage_bps: Decimal | None = None
    require_pretrade_allow: bool = True
    allow_pretrade_allow_smaller_size: bool = True
    allow_pretrade_passive_only_for_passive_orders: bool = True
    reject_manual_review: bool = True
    reject_no_trade: bool = True
    fill_model: FillModel = FillModel.IMMEDIATE_TOP_OF_BOOK
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperOrder(PaperModel):
    paper_order_id: str
    trade_intent_id: str
    pretrade_decision_id: str | None = None
    paper_policy_id: str
    simulation_run_id: str | None = None
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    side: TradeSide
    intent_type: str
    requested_price: Decimal | None = None
    limit_price: Decimal | None = None
    requested_size_units: Decimal = Field(gt=Decimal("0"))
    accepted_size_units: Decimal = Field(ge=Decimal("0"))
    filled_size_units: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    remaining_size_units: Decimal = Field(ge=Decimal("0"))
    status: PaperOrderStatus
    rejection_reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime
    asof_timestamp: datetime
    available_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperFill(PaperModel):
    paper_fill_id: str
    paper_order_id: str
    simulation_run_id: str | None = None
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    side: TradeSide
    filled_at: datetime
    asof_timestamp: datetime
    price: Decimal = Field(ge=Decimal("0"))
    size_units: Decimal = Field(gt=Decimal("0"))
    notional: Decimal = Field(ge=Decimal("0"))
    fee_amount: Decimal = Field(ge=Decimal("0"))
    fee_bps: Decimal = Field(ge=Decimal("0"))
    liquidity_source: LiquiditySource
    source_orderbook_snapshot_id: str | None = None
    source_price_snapshot_id: str | None = None
    source_liquidity_snapshot_id: str | None = None
    fill_reason: str
    is_simulated: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("is_simulated")
    @classmethod
    def _must_be_simulated(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("paper fills must be simulated")
        return value


class PaperLedgerEntry(PaperModel):
    ledger_entry_id: str
    simulation_run_id: str | None = None
    paper_order_id: str | None = None
    paper_fill_id: str | None = None
    market_id: str | None = None
    outcome_id: str | None = None
    venue_id: str | None = None
    entry_type: PaperLedgerEntryType
    occurred_at: datetime
    amount: Decimal
    currency: str
    description: str
    is_simulated: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("is_simulated")
    @classmethod
    def _must_be_simulated(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("paper ledger entries must be simulated")
        return value


class PaperPositionSnapshot(PaperModel):
    position_snapshot_id: str
    simulation_run_id: str | None = None
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    position_units: Decimal
    average_entry_price: Decimal | None = None
    cost_basis: Decimal
    realized_pnl_simulated: Decimal
    unrealized_pnl_simulated: Decimal
    mark_price: Decimal | None = None
    mark_price_snapshot_id: str | None = None
    is_flat: bool
    is_simulated: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("is_simulated")
    @classmethod
    def _must_be_simulated(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("paper positions must be simulated")
        return value


class PaperPortfolioSnapshot(PaperModel):
    portfolio_snapshot_id: str
    simulation_run_id: str | None = None
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    cash_balance_simulated: Decimal
    gross_exposure_simulated: Decimal
    net_exposure_simulated: Decimal
    realized_pnl_simulated: Decimal
    unrealized_pnl_simulated: Decimal
    total_fees_simulated: Decimal
    total_equity_simulated: Decimal
    open_positions_count: int
    closed_positions_count: int
    is_simulated: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("is_simulated")
    @classmethod
    def _must_be_simulated(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("paper portfolios must be simulated")
        return value


class PaperSimulationRun(PaperModel):
    simulation_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: PaperSimulationRunStatus
    paper_policy_id: str
    start_time: datetime
    end_time: datetime
    interval_seconds: int
    market_ids: list[str] = Field(default_factory=list)
    max_orders: int
    initial_cash_simulated: Decimal
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    orders_created: int = 0
    fills_created: int = 0
    rejected_orders: int = 0
    errors_count: int = 0


class PaperSimulationRunSummary(PaperModel):
    summary_id: str
    simulation_run_id: str
    created_at: datetime
    total_orders: int
    filled_orders: int
    partially_filled_orders: int
    rejected_orders: int
    total_fills: int
    total_fees_simulated: Decimal
    final_cash_simulated: Decimal
    final_gross_exposure_simulated: Decimal
    final_net_exposure_simulated: Decimal
    final_realized_pnl_simulated: Decimal
    final_unrealized_pnl_simulated: Decimal
    final_total_equity_simulated: Decimal
    fill_rate: Decimal
    rejection_rate: Decimal
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperSimulationResult(PaperModel):
    pretrade: PreTradeCheckResponse
    order: PaperOrder
    fills: list[PaperFill] = Field(default_factory=list)
    ledger_entries: list[PaperLedgerEntry] = Field(default_factory=list)
    position_snapshot: PaperPositionSnapshot | None = None
    portfolio_snapshot: PaperPortfolioSnapshot | None = None


class PaperFillResult(PaperModel):
    order: PaperOrder
    fills: list[PaperFill] = Field(default_factory=list)
    ledger_entries: list[PaperLedgerEntry] = Field(default_factory=list)
    position_snapshot: PaperPositionSnapshot | None = None
    portfolio_snapshot: PaperPortfolioSnapshot | None = None
    reason_codes: list[str] = Field(default_factory=list)


class PaperSimulateIntentRequest(PaperModel):
    market_id: str
    outcome_id: str | None = None
    venue_id: str | None = None
    strategy_context: StrategyContext = StrategyContext.RESEARCH
    side: TradeSide = TradeSide.BUY
    intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY
    requested_price: Decimal | None = None
    requested_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    requested_notional_usd: Decimal | None = Field(default=None, ge=Decimal("0"))
    asof_timestamp: datetime | None = None
    paper_policy_id: str | None = None
    force_recompute_pretrade: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperSimulationRunConfig(PaperModel):
    name: str | None = None
    start_time: datetime
    end_time: datetime
    interval_seconds: int = Field(gt=0)
    market_ids: list[str] | None = None
    max_orders: int = Field(default=10000, gt=0)
    initial_cash_simulated: Decimal = Decimal("1000")
    paper_policy_id: str | None = None
    trade_plan: list[dict[str, Any]] | None = None
    default_order_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    default_intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY
    default_strategy_context: StrategyContext = StrategyContext.RESEARCH
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperSimulationRunRequest(PaperModel):
    name: str | None = None
    start_time: datetime
    end_time: datetime
    interval_seconds: int = Field(default=3600, gt=0)
    market_ids: list[str] | None = None
    max_orders: int = Field(default=10000, gt=0)
    initial_cash_simulated: Decimal = Decimal("1000")
    paper_policy_id: str | None = None
    trade_plan: list[dict[str, Any]] | None = None
    default_order_size_units: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    default_intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY
    default_strategy_context: StrategyContext = StrategyContext.RESEARCH
    metadata: dict[str, Any] = Field(default_factory=dict)


class PaperSimulationRunResult(PaperModel):
    run: PaperSimulationRun
    orders: list[PaperOrder] = Field(default_factory=list)
    fills: list[PaperFill] = Field(default_factory=list)
    summary: PaperSimulationRunSummary


def compute_paper_policy_id(policy_name: str, policy_version: str) -> str:
    return f"paper_policy_{hash_payload({'name': policy_name, 'version': policy_version})[:24]}"


def compute_paper_order_id(order: PaperOrder) -> str:
    return f"paper_order_{hash_payload(_paper_order_hash_payload(order))[:24]}"


def compute_paper_fill_id(fill: PaperFill) -> str:
    return f"paper_fill_{hash_payload(_paper_fill_hash_payload(fill))[:24]}"


def compute_paper_position_snapshot_id(snapshot: PaperPositionSnapshot) -> str:
    return f"paper_position_{hash_payload(_paper_position_hash_payload(snapshot))[:24]}"


def compute_paper_portfolio_snapshot_id(snapshot: PaperPortfolioSnapshot) -> str:
    return f"paper_portfolio_{hash_payload(_paper_portfolio_hash_payload(snapshot))[:24]}"


def compute_trade_intent_from_request(
    request: PaperSimulateIntentRequest,
    asof_timestamp: datetime,
) -> TradeIntent:
    from prediction_desk.pretrade.models import compute_trade_intent_id

    intent = TradeIntent(
        trade_intent_id="pending",
        market_id=request.market_id,
        outcome_id=request.outcome_id,
        venue_id=request.venue_id,
        strategy_context=request.strategy_context,
        side=request.side,
        intent_type=request.intent_type,
        requested_price=request.requested_price,
        requested_size_units=request.requested_size_units,
        requested_notional_usd=request.requested_notional_usd,
        asof_timestamp=asof_timestamp,
        metadata={"source": "paper_simulation_request_v1", **request.metadata},
    )
    return intent.model_copy(update={"trade_intent_id": compute_trade_intent_id(intent)})


def hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            _json_safe(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _paper_order_hash_payload(order: PaperOrder) -> dict[str, Any]:
    return {
        "version": PAPER_ORDER_VERSION,
        "trade_intent_id": order.trade_intent_id,
        "pretrade_decision_id": order.pretrade_decision_id,
        "paper_policy_id": order.paper_policy_id,
        "simulation_run_id": order.simulation_run_id,
        "market_id": order.market_id,
        "outcome_id": order.outcome_id,
        "venue_id": order.venue_id,
        "side": order.side.value,
        "intent_type": order.intent_type,
        "requested_price": order.requested_price,
        "limit_price": order.limit_price,
        "requested_size_units": order.requested_size_units,
        "accepted_size_units": order.accepted_size_units,
        "created_at": order.created_at,
        "asof_timestamp": order.asof_timestamp,
    }


def _paper_fill_hash_payload(fill: PaperFill) -> dict[str, Any]:
    return {
        "version": PAPER_FILL_VERSION,
        "paper_order_id": fill.paper_order_id,
        "simulation_run_id": fill.simulation_run_id,
        "market_id": fill.market_id,
        "outcome_id": fill.outcome_id,
        "side": fill.side.value,
        "asof_timestamp": fill.asof_timestamp,
        "price": fill.price,
        "size_units": fill.size_units,
        "source_orderbook_snapshot_id": fill.source_orderbook_snapshot_id,
        "liquidity_source": fill.liquidity_source.value,
        "fill_reason": fill.fill_reason,
        "metadata": fill.metadata,
    }


def _paper_position_hash_payload(snapshot: PaperPositionSnapshot) -> dict[str, Any]:
    return {
        "version": PAPER_POSITION_VERSION,
        "simulation_run_id": snapshot.simulation_run_id,
        "market_id": snapshot.market_id,
        "outcome_id": snapshot.outcome_id,
        "venue_id": snapshot.venue_id,
        "asof_timestamp": snapshot.asof_timestamp,
        "position_units": snapshot.position_units,
        "average_entry_price": snapshot.average_entry_price,
        "cost_basis": snapshot.cost_basis,
        "realized_pnl_simulated": snapshot.realized_pnl_simulated,
        "unrealized_pnl_simulated": snapshot.unrealized_pnl_simulated,
        "mark_price": snapshot.mark_price,
        "mark_price_snapshot_id": snapshot.mark_price_snapshot_id,
    }


def _paper_portfolio_hash_payload(snapshot: PaperPortfolioSnapshot) -> dict[str, Any]:
    return {
        "version": PAPER_PORTFOLIO_VERSION,
        "simulation_run_id": snapshot.simulation_run_id,
        "asof_timestamp": snapshot.asof_timestamp,
        "cash_balance_simulated": snapshot.cash_balance_simulated,
        "gross_exposure_simulated": snapshot.gross_exposure_simulated,
        "net_exposure_simulated": snapshot.net_exposure_simulated,
        "realized_pnl_simulated": snapshot.realized_pnl_simulated,
        "unrealized_pnl_simulated": snapshot.unrealized_pnl_simulated,
        "total_fees_simulated": snapshot.total_fees_simulated,
        "total_equity_simulated": snapshot.total_equity_simulated,
        "open_positions_count": snapshot.open_positions_count,
        "closed_positions_count": snapshot.closed_positions_count,
    }

