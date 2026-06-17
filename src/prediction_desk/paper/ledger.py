"""Simulated ledger helpers for paper execution."""

from __future__ import annotations

from decimal import Decimal

from prediction_desk.paper.enums import PaperLedgerEntryType
from prediction_desk.paper.models import PaperFill, PaperLedgerEntry, hash_payload
from prediction_desk.pretrade.enums import TradeSide


def apply_fill_to_ledger(fill: PaperFill) -> list[PaperLedgerEntry]:
    """Creates simulated ledger entries for one fill."""

    entries: list[PaperLedgerEntry] = []
    if fill.side == TradeSide.BUY:
        entries.append(
            _entry(
                fill,
                PaperLedgerEntryType.CASH_DEBIT,
                fill.notional,
                "SIMULATED cash debit for BUY fill",
            )
        )
        entries.append(
            _entry(
                fill,
                PaperLedgerEntryType.POSITION_INCREASE,
                fill.size_units,
                "SIMULATED position increase",
                currency="UNITS",
            )
        )
    elif fill.side == TradeSide.SELL:
        entries.append(
            _entry(
                fill,
                PaperLedgerEntryType.CASH_CREDIT,
                fill.notional,
                "SIMULATED cash credit for SELL fill",
            )
        )
        entries.append(
            _entry(
                fill,
                PaperLedgerEntryType.POSITION_DECREASE,
                fill.size_units,
                "SIMULATED position decrease",
                currency="UNITS",
            )
        )
    if fill.fee_amount > Decimal("0"):
        entries.append(
            _entry(
                fill,
                PaperLedgerEntryType.FEE_DEBIT,
                fill.fee_amount,
                "SIMULATED configurable fee debit",
            )
        )
    return entries


def _entry(
    fill: PaperFill,
    entry_type: PaperLedgerEntryType,
    amount: Decimal,
    description: str,
    *,
    currency: str = "SIM_USD",
) -> PaperLedgerEntry:
    payload = {
        "paper_fill_id": fill.paper_fill_id,
        "entry_type": entry_type.value,
        "amount": amount,
        "currency": currency,
    }
    return PaperLedgerEntry(
        ledger_entry_id=f"paper_ledger_{hash_payload(payload)[:24]}",
        simulation_run_id=fill.simulation_run_id,
        paper_order_id=fill.paper_order_id,
        paper_fill_id=fill.paper_fill_id,
        market_id=fill.market_id,
        outcome_id=fill.outcome_id,
        venue_id=fill.venue_id,
        entry_type=entry_type,
        occurred_at=fill.filled_at,
        amount=amount,
        currency=currency,
        description=description,
        is_simulated=True,
        metadata={"source": "paper_ledger_v1"},
    )

