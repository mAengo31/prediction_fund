from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.paper.models import PaperPositionSnapshot
from prediction_desk.paper.portfolio import compute_portfolio_snapshot
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.paper_helpers import ASOF, MARKET_ID, loaded_repo, long_position


def test_position_and_portfolio_asof_do_not_return_future_snapshots(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "paper_asof.db")
    future = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        old = long_position(units=Decimal("1"))
        new = old.model_copy(
            update={
                "position_snapshot_id": "paper_position_future",
                "asof_timestamp": future,
                "generated_at": future,
                "available_at": future,
                "position_units": Decimal("9"),
            }
        )
        repo.save_paper_position_snapshot(old)
        repo.save_paper_position_snapshot(new)
        portfolio = compute_portfolio_snapshot(
            repo,
            asof_timestamp=ASOF,
            initial_cash_simulated=Decimal("100"),
        )
        future_portfolio = portfolio.model_copy(
            update={
                "portfolio_snapshot_id": "paper_portfolio_future",
                "asof_timestamp": future,
                "generated_at": future,
                "available_at": future,
                "total_equity_simulated": Decimal("999"),
            }
        )
        repo.save_paper_portfolio_snapshot(portfolio)
        repo.save_paper_portfolio_snapshot(future_portfolio)

        latest_position = repo.get_latest_paper_position_asof(
            MARKET_ID,
            asof_timestamp=ASOF,
        )
        latest_portfolio = repo.get_latest_paper_portfolio_asof(asof_timestamp=ASOF)

    assert latest_position is not None
    assert latest_position.position_units == Decimal("1")
    assert latest_portfolio is not None
    assert latest_portfolio.portfolio_snapshot_id == portfolio.portfolio_snapshot_id


def test_portfolio_snapshot_cash_and_exposure_are_simulated(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "portfolio.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        position: PaperPositionSnapshot = repo.save_paper_position_snapshot(
            long_position(units=Decimal("2"))
        )
        snapshot = compute_portfolio_snapshot(
            repo,
            asof_timestamp=ASOF,
            initial_cash_simulated=Decimal("100"),
        )

    assert position.is_simulated
    assert snapshot.cash_balance_simulated == Decimal("100")
    assert snapshot.gross_exposure_simulated == Decimal("1.00")

