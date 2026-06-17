from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.integrity.models import IntegrityRunConfig
from prediction_desk.integrity.runner import IntegrityRunError, run_integrity_scan
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_integrity_runner_persists_run_and_summary(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "integrity_runner.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        result = run_integrity_scan(
            IntegrityRunConfig(
                name="runner test",
                asof_timestamp=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                market_ids=[market_id],
                max_steps=10,
            ),
            repo=repo,
        )
        stored_run = repo.get_integrity_run(result.run.integrity_run_id)
        stored_summary = repo.get_integrity_run_summary(result.run.integrity_run_id)

    assert result.summary.total_assessments == 1
    assert result.summary.total_signals >= 1
    assert stored_run is not None
    assert stored_summary is not None
    assert stored_summary.total_assessments == 1


def test_integrity_runner_rejects_too_many_steps(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "integrity_runner_guardrail.db")

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        with pytest.raises(IntegrityRunError) as exc_info:
            run_integrity_scan(
                IntegrityRunConfig(
                    start_time=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                    end_time=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                    interval_seconds=3600,
                    max_steps=1,
                ),
                repo=repo,
            )
        assert exc_info.value.code == "too_many_integrity_steps"


def _session_factory(tmp_path: Path, filename: str):
    database_url = f"sqlite:///{tmp_path / filename}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)
