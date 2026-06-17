from __future__ import annotations

from pathlib import Path

import pytest

from prediction_desk.ingestion.scheduler import run_ingestion_once
from prediction_desk.ingestion.service import IngestionServiceError
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_run_once_scheduler_fixture_mode_creates_cursors_and_quality(tmp_path: Path) -> None:
    _, session_factory = _repo(tmp_path)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = run_ingestion_once(venue_name="kalshi", repo=repo)
        cursors = repo.list_ingestion_cursors(venue_name="Kalshi")
        reports = repo.list_quality_reports("kalshi_market_kxweather_nyc_rain_20260930")

    assert result.ingestion.run.status.value == "COMPLETED"
    assert result.price_snapshots_created == 3
    assert result.liquidity_snapshots_created == 3
    assert result.quality_reports_created >= 1
    assert cursors
    assert reports


def test_run_once_scheduler_manual_fetch_requires_network_opt_in(tmp_path: Path) -> None:
    _, session_factory = _repo(tmp_path)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        with pytest.raises(IngestionServiceError, match="public_network_disabled"):
            run_ingestion_once(
                venue_name="kalshi",
                mode="manual_public_fetch",
                allow_network=False,
                repo=repo,
            )


def _repo(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'scheduler.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    return PredictionMarketRepository, build_session_factory(engine)
