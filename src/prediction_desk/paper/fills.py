"""Deterministic simulated fill models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from prediction_desk.domain.models import OrderBookSnapshot, PriceLevel
from prediction_desk.paper.enums import FillModel, LiquiditySource, PaperOrderStatus
from prediction_desk.paper.fees import compute_simulated_fee, get_fee_bps_for_venue
from prediction_desk.paper.ledger import apply_fill_to_ledger
from prediction_desk.paper.models import (
    PaperExecutionPolicy,
    PaperFill,
    PaperFillResult,
    PaperOrder,
    compute_paper_fill_id,
)
from prediction_desk.paper.portfolio import update_position_from_fill
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import TradeIntentType, TradeSide


def simulate_order_fill(
    order: PaperOrder,
    policy: PaperExecutionPolicy,
    asof_timestamp: datetime,
    *,
    repo: PredictionMarketRepository,
) -> PaperFillResult:
    """Simulates fills using only market data available at or before T."""

    if order.status == PaperOrderStatus.REJECTED:
        return PaperFillResult(order=order, reason_codes=list(order.rejection_reason_codes))
    if order.accepted_size_units <= Decimal("0"):
        updated = order.model_copy(
            update={
                "status": PaperOrderStatus.REJECTED,
                "rejection_reason_codes": ["NO_ACCEPTED_SIZE"],
            }
        )
        return PaperFillResult(order=updated, reason_codes=["NO_ACCEPTED_SIZE"])
    if order.intent_type == TradeIntentType.RESEARCH_ONLY.value:
        return _no_fill(order, "RESEARCH_ONLY_NO_FILL")
    if policy.fill_model == FillModel.RESEARCH_NO_FILL:
        return _no_fill(order, "RESEARCH_NO_FILL")
    if (
        policy.fill_model == FillModel.PASSIVE_NO_FILL_V1
        or order.intent_type == TradeIntentType.PASSIVE_LIMIT.value
    ):
        return _no_fill(order, "PASSIVE_ORDER_RESTING_UNFILLED")

    orderbook = repo.get_latest_orderbook_snapshot_asof(order.market_id, asof_timestamp)
    price_snapshot = repo.get_latest_price_snapshot_asof(order.market_id, asof_timestamp)
    liquidity_snapshot = repo.get_latest_liquidity_snapshot_asof(order.market_id, asof_timestamp)
    if orderbook is None:
        return _no_fill(order, "MISSING_MARKET_DATA")

    previous_position = repo.get_latest_paper_position_asof(
        order.market_id,
        outcome_id=order.outcome_id,
        simulation_run_id=order.simulation_run_id,
        asof_timestamp=asof_timestamp,
    )
    if order.side == TradeSide.SELL and not policy.allow_simulated_shorts:
        available_units = (
            previous_position.position_units if previous_position is not None else Decimal("0")
        )
        if available_units <= Decimal("0"):
            updated = order.model_copy(
                update={
                    "status": PaperOrderStatus.REJECTED,
                    "rejection_reason_codes": ["SIMULATED_SHORTS_DISABLED"],
                }
            )
            return PaperFillResult(
                order=updated,
                reason_codes=["SIMULATED_SHORTS_DISABLED"],
            )

    levels = _candidate_levels(order, orderbook, policy.fill_model)
    if not levels:
        return _no_fill(order, "LIMIT_NOT_CROSSING_BOOK")

    fill_limit = order.accepted_size_units
    if order.side == TradeSide.SELL and not policy.allow_simulated_shorts:
        available = previous_position.position_units if previous_position else Decimal("0")
        fill_limit = min(fill_limit, available)
    remaining = fill_limit
    fills: list[PaperFill] = []
    ledger_entries = []
    current_position = previous_position
    for index, level in enumerate(levels):
        if remaining <= Decimal("0"):
            break
        size = min(remaining, level.quantity)
        if size <= Decimal("0"):
            continue
        notional = level.price * size
        fee_bps = get_fee_bps_for_venue(policy, venue_id=order.venue_id)
        fill = PaperFill(
            paper_fill_id="pending",
            paper_order_id=order.paper_order_id,
            simulation_run_id=order.simulation_run_id,
            market_id=order.market_id,
            outcome_id=order.outcome_id,
            venue_id=order.venue_id,
            side=order.side,
            filled_at=asof_timestamp,
            asof_timestamp=asof_timestamp,
            price=level.price,
            size_units=size,
            notional=notional,
            fee_amount=compute_simulated_fee(notional, fee_bps),
            fee_bps=fee_bps,
            liquidity_source=(
                LiquiditySource.TOP_OF_BOOK
                if policy.fill_model == FillModel.IMMEDIATE_TOP_OF_BOOK
                else LiquiditySource.WALKED_BOOK
            ),
            source_orderbook_snapshot_id=orderbook.snapshot_id,
            source_price_snapshot_id=price_snapshot.price_snapshot_id if price_snapshot else None,
            source_liquidity_snapshot_id=(
                liquidity_snapshot.liquidity_snapshot_id if liquidity_snapshot else None
            ),
            fill_reason=(
                "SIMULATED_TOP_OF_BOOK_FILL"
                if policy.fill_model == FillModel.IMMEDIATE_TOP_OF_BOOK
                else "SIMULATED_WALKED_BOOK_FILL"
            ),
            is_simulated=True,
            metadata={"level_index": index, "fill_model": policy.fill_model.value},
        )
        fill = fill.model_copy(update={"paper_fill_id": compute_paper_fill_id(fill)})
        fills.append(fill)
        ledger_entries.extend(apply_fill_to_ledger(fill))
        current_position = update_position_from_fill(
            fill,
            previous_position=current_position,
            mark_price_snapshot=price_snapshot,
        )
        remaining -= size

    if not fills:
        return _no_fill(order, "NO_FILLABLE_SIZE")
    filled_size = sum((fill.size_units for fill in fills), Decimal("0"))
    if filled_size < order.accepted_size_units and not policy.allow_partial_fills:
        return _no_fill(order, "PARTIAL_FILLS_DISABLED")
    status = (
        PaperOrderStatus.FILLED
        if filled_size >= order.accepted_size_units
        else PaperOrderStatus.PARTIALLY_FILLED
    )
    updated_order = order.model_copy(
        update={
            "filled_size_units": filled_size,
            "remaining_size_units": max(Decimal("0"), order.accepted_size_units - filled_size),
            "status": status,
            "metadata": {
                **order.metadata,
                "source_orderbook_snapshot_id": orderbook.snapshot_id,
                "source_price_snapshot_id": (
                    price_snapshot.price_snapshot_id if price_snapshot else None
                ),
                "source_liquidity_snapshot_id": (
                    liquidity_snapshot.liquidity_snapshot_id if liquidity_snapshot else None
                ),
            },
        }
    )
    return PaperFillResult(
        order=updated_order,
        fills=fills,
        ledger_entries=ledger_entries,
        position_snapshot=current_position,
        reason_codes=[fill.fill_reason for fill in fills],
    )


def _candidate_levels(
    order: PaperOrder,
    orderbook: OrderBookSnapshot,
    fill_model: FillModel,
) -> list[PriceLevel]:
    if order.side == TradeSide.BUY:
        levels = sorted(orderbook.asks, key=lambda level: level.price)
        return _filter_buy_levels(order, levels, fill_model)
    if order.side == TradeSide.SELL:
        levels = sorted(orderbook.bids, key=lambda level: level.price, reverse=True)
        return _filter_sell_levels(order, levels, fill_model)
    return []


def _filter_buy_levels(
    order: PaperOrder,
    levels: list[PriceLevel],
    fill_model: FillModel,
) -> list[PriceLevel]:
    filtered = [
        level
        for level in levels
        if order.limit_price is None or level.price <= order.limit_price
    ]
    if fill_model == FillModel.IMMEDIATE_TOP_OF_BOOK:
        return filtered[:1]
    return filtered


def _filter_sell_levels(
    order: PaperOrder,
    levels: list[PriceLevel],
    fill_model: FillModel,
) -> list[PriceLevel]:
    filtered = [
        level
        for level in levels
        if order.limit_price is None or level.price >= order.limit_price
    ]
    if fill_model == FillModel.IMMEDIATE_TOP_OF_BOOK:
        return filtered[:1]
    return filtered


def _no_fill(order: PaperOrder, reason_code: str) -> PaperFillResult:
    updated = order.model_copy(
        update={
            "status": PaperOrderStatus.RESTING_UNFILLED,
            "remaining_size_units": order.accepted_size_units - order.filled_size_units,
            "metadata": {**order.metadata, "no_fill_reason": reason_code},
        }
    )
    return PaperFillResult(order=updated, reason_codes=[reason_code])

