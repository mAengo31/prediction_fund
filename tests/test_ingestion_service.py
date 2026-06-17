from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import func, select

from prediction_desk.ingestion.service import IngestionService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.orm import MarketRuleSnapshotRecord
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_ingestion_service_archives_payloads_and_creates_mapping(tmp_path: Path) -> None:
    repo, session_factory = _repo(tmp_path)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = IngestionService(repo).ingest_fixture_payloads(venue_name="kalshi")

    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        mapping = repo.get_mapping_by_external_market_id(
            "Kalshi", "KXWEATHER-NYC-RAIN-20260930"
        )
        payloads = repo.list_raw_venue_payloads(venue_name="Kalshi")

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 5
    assert result.run.markets_created == 1
    assert result.run.rule_snapshots_created == 1
    assert result.run.orderbook_snapshots_created == 3
    assert result.run.price_snapshots_created == 3
    assert result.run.liquidity_snapshots_created == 3
    assert mapping is not None
    assert mapping.canonical_market_id == "kalshi_market_kxweather_nyc_rain_20260930"
    assert len(payloads) == 5
    assert repo is not None


def test_ingestion_service_is_idempotent_for_unchanged_rule_snapshots(tmp_path: Path) -> None:
    _, session_factory = _repo(tmp_path)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        first = IngestionService(repo).ingest_fixture_payloads(venue_name="kalshi")
        second = IngestionService(repo).ingest_fixture_payloads(venue_name="kalshi")

    with session_factory() as session:
        count = session.scalar(
            select(func.count())
            .select_from(MarketRuleSnapshotRecord)
            .where(
                MarketRuleSnapshotRecord.market_id
                == "kalshi_market_kxweather_nyc_rain_20260930"
            )
        )

    assert first.run.rule_snapshots_created == 1
    assert second.run.rule_snapshots_created == 0
    assert count == 1


def test_ingestion_service_records_errors_and_continues(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    source_dir = Path("sample_data/venue_payloads/kalshi")
    valid = json.loads((source_dir / "market_detail_weather.json").read_text())
    bad = json.loads((source_dir / "orderbook_weather.json").read_text())
    bad["external_id"] = None
    bad["response_payload"] = {"orderbook": {}}
    (fixture_dir / "market_detail_weather.json").write_text(json.dumps(valid))
    (fixture_dir / "bad_orderbook.json").write_text(json.dumps(bad))
    _, session_factory = _repo(tmp_path)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = IngestionService(repo).ingest_fixture_payloads(
            venue_name="kalshi",
            fixture_dir=fixture_dir,
        )

    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        errors = repo.list_ingestion_errors(result.run.ingestion_run_id)
        market = repo.get_market("kalshi_market_kxweather_nyc_rain_20260930")

    assert result.run.status.value == "PARTIAL"
    assert result.run.errors_count == 1
    assert len(errors) == 1
    assert errors[0].error_code == "payload_ingestion_failed"
    assert market is not None


def _repo(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'ingestion.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    return PredictionMarketRepository, session_factory
