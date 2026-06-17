from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.ingestion.scheduler import run_ingestion_once
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository

ASOF = datetime(2026, 6, 16, 12, 45, tzinfo=UTC)
KALSHI_RAIN = "kalshi_market_kxweather_nyc_rain_20260930"
POLYMARKET_RAIN = "polymarket_market_0xrainnycsep2026"
POLYMARKET_TEMP = "polymarket_market_0xabc123nyctemp"


def ingest_fixture_venues(database_url: str) -> None:
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        run_ingestion_once(venue_name="kalshi", repo=repo)
        run_ingestion_once(venue_name="polymarket", repo=repo)
