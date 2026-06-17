from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import StrategyContext, TradeIntentType
from prediction_desk.pretrade.models import PreTradeRunConfig
from prediction_desk.pretrade.runner import run_pretrade_checks


def test_runner_creates_run_and_summary(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'pretrade_runner.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = run_pretrade_checks(
            PreTradeRunConfig(
                name="pretrade test",
                asof_timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                market_ids=["mkt_cpi_yoy_at_least_3pct_2026_09"],
                max_checks=10,
                default_requested_size_units=Decimal("1"),
                strategy_context=StrategyContext.RESEARCH,
                intent_type=TradeIntentType.RESEARCH_ONLY,
            ),
            repo=repo,
        )
        stored = repo.get_pretrade_run(result.run.pretrade_run_id)
        summary = repo.get_pretrade_run_summary(result.run.pretrade_run_id)

    assert stored is not None
    assert summary is not None
    assert result.summary.total_decisions == 1
    assert result.run.decisions_created == 1
