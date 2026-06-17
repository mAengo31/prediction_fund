from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.paper.enums import LiquiditySource, PaperLedgerEntryType
from prediction_desk.paper.ledger import apply_fill_to_ledger
from prediction_desk.paper.models import PaperFill
from prediction_desk.pretrade.enums import TradeSide


def test_apply_buy_fill_to_ledger_creates_cash_fee_and_position_entries() -> None:
    fill = PaperFill(
        paper_fill_id="fill",
        paper_order_id="order",
        market_id="market",
        side=TradeSide.BUY,
        filled_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        asof_timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        price=Decimal("0.50"),
        size_units=Decimal("2"),
        notional=Decimal("1.00"),
        fee_amount=Decimal("0.01"),
        fee_bps=Decimal("100"),
        liquidity_source=LiquiditySource.TOP_OF_BOOK,
        fill_reason="test",
        is_simulated=True,
    )

    entries = apply_fill_to_ledger(fill)

    assert {entry.entry_type for entry in entries} == {
        PaperLedgerEntryType.CASH_DEBIT,
        PaperLedgerEntryType.FEE_DEBIT,
        PaperLedgerEntryType.POSITION_INCREASE,
    }

