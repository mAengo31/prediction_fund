"""Simulated paper position and portfolio calculations."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.marketdata.models import MarketPriceSnapshot
from prediction_desk.paper.enums import PaperLedgerEntryType
from prediction_desk.paper.models import (
    PaperFill,
    PaperPortfolioSnapshot,
    PaperPositionSnapshot,
    compute_paper_portfolio_snapshot_id,
    compute_paper_position_snapshot_id,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import TradeSide


def get_latest_position_snapshot_asof(
    repo: PredictionMarketRepository,
    *,
    market_id: str,
    outcome_id: str | None = None,
    simulation_run_id: str | None = None,
    asof_timestamp: datetime,
) -> PaperPositionSnapshot | None:
    return repo.get_latest_paper_position_asof(
        market_id,
        outcome_id=outcome_id,
        simulation_run_id=simulation_run_id,
        asof_timestamp=asof_timestamp,
    )


def get_latest_portfolio_snapshot_asof(
    repo: PredictionMarketRepository,
    *,
    simulation_run_id: str | None = None,
    asof_timestamp: datetime,
) -> PaperPortfolioSnapshot | None:
    return repo.get_latest_paper_portfolio_asof(
        simulation_run_id=simulation_run_id,
        asof_timestamp=asof_timestamp,
    )


def update_position_from_fill(
    fill: PaperFill,
    *,
    previous_position: PaperPositionSnapshot | None,
    mark_price_snapshot: MarketPriceSnapshot | None,
) -> PaperPositionSnapshot:
    previous_units = previous_position.position_units if previous_position else Decimal("0")
    previous_cost = previous_position.cost_basis if previous_position else Decimal("0")
    previous_realized = (
        previous_position.realized_pnl_simulated if previous_position else Decimal("0")
    )
    previous_average = previous_position.average_entry_price if previous_position else None

    if fill.side == TradeSide.BUY:
        new_units = previous_units + fill.size_units
        new_cost = previous_cost + fill.notional
        average_entry = new_cost / new_units if new_units > Decimal("0") else None
        realized = previous_realized
    else:
        average = previous_average or Decimal("0")
        closed_cost = average * fill.size_units
        new_units = previous_units - fill.size_units
        new_cost = max(Decimal("0"), previous_cost - closed_cost)
        average_entry = new_cost / new_units if new_units > Decimal("0") else None
        realized = previous_realized + fill.notional - closed_cost - fill.fee_amount

    mark_price = _mark_price(mark_price_snapshot)
    if mark_price is not None and average_entry is not None and new_units > Decimal("0"):
        unrealized = (mark_price - average_entry) * new_units
    else:
        unrealized = Decimal("0")
    snapshot = PaperPositionSnapshot(
        position_snapshot_id="pending",
        simulation_run_id=fill.simulation_run_id,
        market_id=fill.market_id,
        outcome_id=fill.outcome_id,
        venue_id=fill.venue_id,
        asof_timestamp=fill.asof_timestamp,
        generated_at=fill.filled_at,
        available_at=fill.asof_timestamp,
        position_units=new_units,
        average_entry_price=average_entry,
        cost_basis=new_cost,
        realized_pnl_simulated=realized,
        unrealized_pnl_simulated=unrealized,
        mark_price=mark_price,
        mark_price_snapshot_id=(
            mark_price_snapshot.price_snapshot_id if mark_price_snapshot else None
        ),
        is_flat=new_units == Decimal("0"),
        is_simulated=True,
        metadata={
            "source": "paper_position_update_v1",
            "mark_missing": mark_price is None,
        },
    )
    return snapshot.model_copy(
        update={"position_snapshot_id": compute_paper_position_snapshot_id(snapshot)}
    )


def mark_position_to_market(
    repo: PredictionMarketRepository,
    *,
    market_id: str,
    outcome_id: str | None = None,
    simulation_run_id: str | None = None,
    asof_timestamp: datetime,
) -> PaperPositionSnapshot | None:
    previous = repo.get_latest_paper_position_asof(
        market_id,
        outcome_id=outcome_id,
        simulation_run_id=simulation_run_id,
        asof_timestamp=asof_timestamp,
    )
    if previous is None:
        return None
    price_snapshot = repo.get_latest_price_snapshot_asof(market_id, asof_timestamp)
    mark_price = _mark_price(price_snapshot)
    if mark_price is None or previous.average_entry_price is None:
        return previous.model_copy(
            update={
                "metadata": {
                    **previous.metadata,
                    "mark_missing": True,
                    "source": "paper_mark_to_market_v1",
                }
            }
        )
    unrealized = (mark_price - previous.average_entry_price) * previous.position_units
    snapshot = previous.model_copy(
        update={
            "asof_timestamp": asof_timestamp,
            "generated_at": datetime.now(tz=UTC),
            "available_at": asof_timestamp,
            "unrealized_pnl_simulated": unrealized,
            "mark_price": mark_price,
            "mark_price_snapshot_id": (
                price_snapshot.price_snapshot_id if price_snapshot is not None else None
            ),
            "metadata": {
                **previous.metadata,
                "source": "paper_mark_to_market_v1",
                "mark_missing": False,
            },
        }
    )
    return snapshot.model_copy(
        update={"position_snapshot_id": compute_paper_position_snapshot_id(snapshot)}
    )


def compute_portfolio_snapshot(
    repo: PredictionMarketRepository,
    *,
    simulation_run_id: str | None = None,
    asof_timestamp: datetime,
    initial_cash_simulated: Decimal = Decimal("0"),
) -> PaperPortfolioSnapshot:
    asof = _aware(asof_timestamp)
    entries = [
        entry
        for entry in repo.list_paper_ledger_entries(
            simulation_run_id=simulation_run_id,
            limit=10000,
        )
        if _aware(entry.occurred_at) <= asof
    ]
    cash = initial_cash_simulated
    total_fees = Decimal("0")
    for entry in entries:
        if entry.entry_type == PaperLedgerEntryType.CASH_CREDIT:
            cash += entry.amount
        elif entry.entry_type == PaperLedgerEntryType.CASH_DEBIT:
            cash -= entry.amount
        elif entry.entry_type == PaperLedgerEntryType.FEE_DEBIT:
            cash -= entry.amount
            total_fees += entry.amount

    positions = _latest_positions(repo, simulation_run_id, asof_timestamp)
    gross = Decimal("0")
    net = Decimal("0")
    realized = Decimal("0")
    unrealized = Decimal("0")
    open_count = 0
    closed_count = 0
    for position in positions:
        mark = position.mark_price or position.average_entry_price or Decimal("0")
        value = position.position_units * mark
        gross += abs(value)
        net += value
        realized += position.realized_pnl_simulated
        unrealized += position.unrealized_pnl_simulated
        if position.is_flat:
            closed_count += 1
        else:
            open_count += 1

    snapshot = PaperPortfolioSnapshot(
        portfolio_snapshot_id="pending",
        simulation_run_id=simulation_run_id,
        asof_timestamp=asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=asof_timestamp,
        cash_balance_simulated=cash,
        gross_exposure_simulated=gross,
        net_exposure_simulated=net,
        realized_pnl_simulated=realized,
        unrealized_pnl_simulated=unrealized,
        total_fees_simulated=total_fees,
        total_equity_simulated=cash + net,
        open_positions_count=open_count,
        closed_positions_count=closed_count,
        is_simulated=True,
        metadata={
            "source": "paper_portfolio_v1",
            "initial_cash_simulated": str(initial_cash_simulated),
        },
    )
    return snapshot.model_copy(
        update={"portfolio_snapshot_id": compute_paper_portfolio_snapshot_id(snapshot)}
    )


def _latest_positions(
    repo: PredictionMarketRepository,
    simulation_run_id: str | None,
    asof_timestamp: datetime,
) -> list[PaperPositionSnapshot]:
    latest: dict[tuple[str, str | None, str | None], PaperPositionSnapshot] = {}
    for snapshot in repo.list_paper_position_snapshots(
        simulation_run_id=simulation_run_id,
        limit=10000,
    ):
        if _aware(snapshot.available_at) > _aware(asof_timestamp):
            continue
        key = (snapshot.market_id, snapshot.outcome_id, snapshot.venue_id)
        existing = latest.get(key)
        if existing is None or (
            snapshot.available_at,
            snapshot.generated_at,
            snapshot.position_snapshot_id,
        ) > (
            existing.available_at,
            existing.generated_at,
            existing.position_snapshot_id,
        ):
            latest[key] = snapshot
    return list(latest.values())


def _mark_price(snapshot: MarketPriceSnapshot | None) -> Decimal | None:
    if snapshot is None:
        return None
    return (
        snapshot.price
        or snapshot.mid
        or snapshot.last_trade_price
        or snapshot.bid
        or snapshot.ask
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
