from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.dataops.coverage import compute_global_coverage, compute_market_coverage
from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def _factory(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'dataops_coverage.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)


def test_coverage_report_detects_missing_price_liquidity_and_quality(tmp_path) -> None:
    factory = _factory(tmp_path)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        report = compute_global_coverage(ASOF, repo=repo)

    assert report.total_markets >= 1
    assert report.missing_price_markets >= 1
    assert report.missing_liquidity_markets >= 1
    assert "MISSING_PRICE_SNAPSHOTS" in report.reason_codes


def test_market_coverage_for_unknown_market_is_empty(tmp_path) -> None:
    factory = _factory(tmp_path)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        report = compute_market_coverage("missing_market", ASOF, repo=repo)

    assert report.total_markets == 0
    assert report.reason_codes == ["NO_MARKETS_IN_SCOPE"]
