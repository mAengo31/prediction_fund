from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.integrity.service import IntegrityService
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_integrity_service_persists_feature_signals_and_assessment(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "integrity_service.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        MarketDataService(repo).compute_market_data_quality(market_id, asof)
        analysis = IntegrityService(repo).analyze_market_integrity_details(market_id, asof)
        signals = repo.list_integrity_signals(market_id=market_id)
        assessments = repo.list_integrity_assessments(market_id=market_id)

    assert analysis.feature_snapshot.market_id == market_id
    assert analysis.assessment.integrity_assessment_id
    assert signals
    assert assessments


def test_integrity_service_avoids_duplicates_unless_force(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "integrity_duplicates.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        service = IntegrityService(repo)
        first = service.analyze_market_integrity_details(market_id, asof)
        second = service.analyze_market_integrity_details(market_id, asof)
        forced = service.analyze_market_integrity_details(market_id, asof, force=True)
        assessments = repo.list_integrity_assessments(market_id=market_id)

    assert first.assessment.integrity_assessment_id == second.assessment.integrity_assessment_id
    assert forced.assessment.integrity_assessment_id == first.assessment.integrity_assessment_id
    assert len(assessments) == 1


def test_future_integrity_assessment_is_not_returned_by_asof_lookup(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "integrity_asof.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        service = IntegrityService(repo)
        current = service.analyze_market_integrity(market_id, asof)
        future = current.model_copy(
            update={
                "integrity_assessment_id": "integrity_assessment_future",
                "asof_timestamp": asof + timedelta(hours=1),
                "available_at": asof + timedelta(hours=1),
                "input_hash": "future_input_hash",
                "output_hash": "future_output_hash",
            }
        )
        repo.save_integrity_assessment(future)
        latest = repo.get_latest_integrity_assessment_asof(market_id, asof)

    assert latest is not None
    assert latest.integrity_assessment_id == current.integrity_assessment_id


def _session_factory(tmp_path: Path, filename: str):
    database_url = f"sqlite:///{tmp_path / filename}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)
