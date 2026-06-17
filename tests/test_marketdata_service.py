from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.ingestion.service import IngestionService
from prediction_desk.marketdata.enums import MarketPriceSource
from prediction_desk.marketdata.models import (
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
    compute_market_liquidity_hash,
    compute_market_price_hash,
)
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_marketdata_service_derives_snapshots_from_orderbooks(tmp_path: Path) -> None:
    _, session_factory = _repo(tmp_path, "derive.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = MarketDataService(repo).derive_market_data_for_market(market_id)

    assert result.price_snapshots_created == 2
    assert result.liquidity_snapshots_created == 2
    assert {snapshot.market_id for snapshot in result.price_snapshots} == {market_id}


def test_asof_price_and_liquidity_use_available_at_not_observed_at(tmp_path: Path) -> None:
    _, session_factory = _repo(tmp_path, "asof.db")
    market_id = "mkt_sfo_rain_2026_09_01"
    asof = datetime(2026, 6, 16, 12, 30, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        older_price = _price_snapshot(
            market_id=market_id,
            snapshot_id="price_old",
            observed_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
            captured_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
            available_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
            price=Decimal("0.50"),
        )
        future_price = _price_snapshot(
            market_id=market_id,
            snapshot_id="price_future",
            observed_at=datetime(2026, 6, 16, 11, 0, tzinfo=UTC),
            captured_at=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
            available_at=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
            price=Decimal("0.80"),
        )
        older_liquidity = _liquidity_snapshot(
            market_id=market_id,
            snapshot_id="liquidity_old",
            observed_at=older_price.observed_at,
            captured_at=older_price.captured_at,
            available_at=older_price.available_at,
            bid=Decimal("0.49"),
            ask=Decimal("0.51"),
        )
        future_liquidity = _liquidity_snapshot(
            market_id=market_id,
            snapshot_id="liquidity_future",
            observed_at=future_price.observed_at,
            captured_at=future_price.captured_at,
            available_at=future_price.available_at,
            bid=Decimal("0.79"),
            ask=Decimal("0.81"),
        )
        repo.save_market_price_snapshot(older_price)
        repo.save_market_price_snapshot(future_price)
        repo.save_market_liquidity_snapshot(older_liquidity)
        repo.save_market_liquidity_snapshot(future_liquidity)

        latest_price = repo.get_latest_price_snapshot_asof(market_id, asof)
        latest_liquidity = repo.get_latest_liquidity_snapshot_asof(market_id, asof)

    assert latest_price is not None
    assert latest_price.price_snapshot_id == "price_old"
    assert latest_liquidity is not None
    assert latest_liquidity.liquidity_snapshot_id == "liquidity_old"


def test_kalshi_fixture_ingestion_creates_price_and_liquidity_snapshots(
    tmp_path: Path,
) -> None:
    _, session_factory = _repo(tmp_path, "kalshi.db")

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = IngestionService(repo).ingest_fixture_payloads(venue_name="kalshi")
        prices = repo.list_price_snapshots("kalshi_market_kxweather_nyc_rain_20260930")
        liquidity = repo.list_liquidity_snapshots("kalshi_market_kxweather_nyc_rain_20260930")

    assert result.run.price_snapshots_created == 3
    assert result.run.liquidity_snapshots_created == 3
    assert len(prices) == 3
    assert len(liquidity) == 3


def test_polymarket_price_history_fixture_creates_price_snapshot(tmp_path: Path) -> None:
    _, session_factory = _repo(tmp_path, "polymarket.db")

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = IngestionService(repo).ingest_fixture_payloads(venue_name="polymarket")
        prices = repo.list_price_snapshots("polymarket_market_0xabc123nyctemp")

    history_prices = [
        snapshot
        for snapshot in prices
        if snapshot.source is MarketPriceSource.VENUE_PRICE_HISTORY
    ]
    assert result.run.price_snapshots_created >= 2
    assert history_prices
    assert history_prices[0].observed_at.replace(tzinfo=UTC) == datetime(
        2026, 6, 16, 11, 30, tzinfo=UTC
    )
    assert history_prices[0].available_at.replace(tzinfo=UTC) == datetime(
        2026, 6, 16, 12, 10, tzinfo=UTC
    )


def _repo(tmp_path: Path, name: str):
    database_url = f"sqlite:///{tmp_path / name}"
    init_db(database_url)
    engine = build_engine(database_url)
    return PredictionMarketRepository, build_session_factory(engine)


def _price_snapshot(
    *,
    market_id: str,
    snapshot_id: str,
    observed_at: datetime,
    captured_at: datetime,
    available_at: datetime,
    price: Decimal,
) -> MarketPriceSnapshot:
    snapshot = MarketPriceSnapshot(
        price_snapshot_id=snapshot_id,
        market_id=market_id,
        outcome_id=None,
        venue_id="sample_research_venue",
        venue_name="Sample Research Venue",
        source=MarketPriceSource.MANUAL_FIXTURE,
        observed_at=observed_at,
        captured_at=captured_at,
        available_at=available_at,
        price=price,
        bid=price,
        ask=price,
        mid=price,
        spread=Decimal("0"),
        last_trade_price=None,
        volume=None,
        open_interest=None,
        source_payload_id=None,
        orderbook_snapshot_id=None,
        external_market_id=None,
        external_outcome_id=None,
        data_hash="pending",
        metadata={},
    )
    return snapshot.model_copy(update={"data_hash": compute_market_price_hash(snapshot)})


def _liquidity_snapshot(
    *,
    market_id: str,
    snapshot_id: str,
    observed_at: datetime,
    captured_at: datetime,
    available_at: datetime,
    bid: Decimal,
    ask: Decimal,
) -> MarketLiquiditySnapshot:
    snapshot = MarketLiquiditySnapshot(
        liquidity_snapshot_id=snapshot_id,
        market_id=market_id,
        venue_id="sample_research_venue",
        venue_name="Sample Research Venue",
        observed_at=observed_at,
        captured_at=captured_at,
        available_at=available_at,
        best_bid=bid,
        best_ask=ask,
        mid_price=(bid + ask) / Decimal("2"),
        spread=ask - bid,
        spread_bps=Decimal("100"),
        bid_depth=Decimal("10"),
        ask_depth=Decimal("10"),
        total_bid_depth=Decimal("10"),
        total_ask_depth=Decimal("10"),
        book_imbalance=Decimal("0"),
        is_empty_book=False,
        is_crossed_book=False,
        source_payload_id=None,
        orderbook_snapshot_id=None,
        data_hash="pending",
        metadata={},
    )
    return snapshot.model_copy(update={"data_hash": compute_market_liquidity_hash(snapshot)})
