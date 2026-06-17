from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from prediction_desk.dataops.backfill import create_backfill_job, run_backfill_job
from prediction_desk.dataops.enums import BackfillSegmentStatus
from prediction_desk.ingestion.service import IngestionService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository

START = datetime(2026, 6, 16, 11, 0, tzinfo=UTC)
END = datetime(2026, 6, 16, 12, 10, tzinfo=UTC)
POLYMARKET_TEMP = "polymarket_market_0xabc123nyctemp"


def _factory(tmp_path: Path, name: str):
    database_url = f"sqlite:///{tmp_path / name}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)


def test_backfill_job_plans_deterministic_segments(tmp_path: Path) -> None:
    factory = _factory(tmp_path, "dataops_backfill_plan.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        job = create_backfill_job(
            venue_name="polymarket",
            market_ids=[POLYMARKET_TEMP],
            endpoint_types=["PRICE_HISTORY"],
            start_time=START,
            end_time=END,
            interval_seconds=3600,
            repo=repo,
        )
        first = repo.list_backfill_segments(backfill_job_id=job.backfill_job_id)
        second = repo.list_backfill_segments(backfill_job_id=job.backfill_job_id)

    assert [segment.backfill_segment_id for segment in first] == [
        segment.backfill_segment_id for segment in second
    ]
    assert len(first) == 2


def test_unsupported_historical_endpoint_creates_skipped_segment(tmp_path: Path) -> None:
    factory = _factory(tmp_path, "dataops_backfill_unsupported.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        job = create_backfill_job(
            venue_name="kalshi",
            market_ids=["kalshi_market_kxweather_nyc_rain_20260930"],
            endpoint_types=["ORDERBOOK"],
            start_time=START,
            end_time=END,
            repo=repo,
        )
        result = run_backfill_job(job.backfill_job_id, repo=repo)

    assert result.segments[0].status == BackfillSegmentStatus.SKIPPED_UNSUPPORTED
    assert result.segments[0].supported is False


def test_fixture_price_history_backfill_preserves_available_at_semantics(
    tmp_path: Path,
) -> None:
    fixture_dir = tmp_path / "polymarket_fixture"
    fixture_dir.mkdir()
    shutil.copy(
        Path("sample_data/venue_payloads/polymarket/market_detail_weather.json"),
        fixture_dir / "market_detail_weather.json",
    )
    factory = _factory(tmp_path, "dataops_backfill_price_history.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        IngestionService(repo).ingest_fixture_payloads(
            venue_name="polymarket",
            fixture_dir=fixture_dir,
            analyze_rules=False,
            recompute_verdicts=False,
        )
        job = create_backfill_job(
            venue_name="polymarket",
            market_ids=[POLYMARKET_TEMP],
            endpoint_types=["PRICE_HISTORY"],
            start_time=START,
            end_time=END,
            repo=repo,
        )
        result = run_backfill_job(job.backfill_job_id, repo=repo)
        before_available = repo.get_latest_price_snapshot_asof(
            POLYMARKET_TEMP,
            datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        )
        at_available = repo.get_latest_price_snapshot_asof(POLYMARKET_TEMP, END)

    assert result.segments[0].snapshots_created == 1
    assert before_available is None
    assert at_available is not None
    assert at_available.observed_at < at_available.available_at
