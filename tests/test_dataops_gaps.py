from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.dataops.enums import CoverageScopeType, DataGapType
from prediction_desk.dataops.gaps import detect_data_gaps
from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_gap_detection_creates_missing_data_gaps(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_gaps.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        gaps = detect_data_gaps(CoverageScopeType.GLOBAL, ASOF, repo=repo)

    gap_types = {gap.gap_type for gap in gaps}
    assert DataGapType.MISSING_PRICE_SNAPSHOT in gap_types
    assert DataGapType.MISSING_LIQUIDITY_SNAPSHOT in gap_types


def test_gap_detection_creates_stale_market_data_gap(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_stale_gaps.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market("mkt_sfo_rain_2026_09_01")
        gaps = detect_data_gaps(
            CoverageScopeType.MARKET,
            datetime(2026, 6, 16, 14, 0, tzinfo=UTC),
            market_id="mkt_sfo_rain_2026_09_01",
            expected_cadence_seconds=60,
            repo=repo,
        )

    assert any(gap.gap_type == DataGapType.STALE_MARKET_DATA for gap in gaps)
