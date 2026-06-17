from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from prediction_desk.paper.models import PaperSimulationRunConfig
from prediction_desk.paper.runner import run_paper_simulation
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import TradeIntentType
from tests.paper_helpers import ASOF, MARKET_ID, loaded_repo


def test_paper_run_creates_run_and_summary(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "runner.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = run_paper_simulation(
            PaperSimulationRunConfig(
                name="paper test",
                start_time=ASOF,
                end_time=ASOF + timedelta(hours=1),
                interval_seconds=3600,
                market_ids=[MARKET_ID],
                max_orders=10,
                initial_cash_simulated=Decimal("1000"),
                default_intent_type=TradeIntentType.RESEARCH_ONLY,
            ),
            repo=repo,
        )

    assert result.summary.total_orders == 2
    assert result.run.orders_created == 2
    assert result.summary.final_total_equity_simulated == Decimal("1000.0000000000")

