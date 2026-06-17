from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.integrity.features import build_market_feature_snapshot
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


def test_feature_snapshot_uses_latest_price_liquidity_quality_asof(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "features.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        quality = MarketDataService(repo).compute_market_data_quality(market_id, asof)
        feature = build_market_feature_snapshot(market_id, asof, repo=repo)

    assert feature.latest_price_snapshot_id is not None
    assert feature.previous_price_snapshot_id is not None
    assert feature.latest_liquidity_snapshot_id is not None
    assert feature.previous_liquidity_snapshot_id is not None
    assert feature.latest_quality_report_id == quality.quality_report_id
    assert feature.spread == Decimal("0.2200000000")
    assert feature.spread_change_abs is not None


def test_feature_snapshot_does_not_use_future_available_market_data(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "future_marketdata.db")
    market_id = "mkt_sfo_rain_2026_09_01"
    asof = datetime(2026, 6, 16, 12, 30, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        repo.save_market_price_snapshot(
            _price_snapshot(
                market_id=market_id,
                snapshot_id="price_old",
                observed_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                available_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                price=Decimal("0.50"),
            )
        )
        repo.save_market_price_snapshot(
            _price_snapshot(
                market_id=market_id,
                snapshot_id="price_future",
                observed_at=datetime(2026, 6, 16, 11, 0, tzinfo=UTC),
                available_at=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                price=Decimal("0.90"),
            )
        )
        repo.save_market_liquidity_snapshot(
            _liquidity_snapshot(
                market_id=market_id,
                snapshot_id="liquidity_old",
                observed_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                available_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
                bid=Decimal("0.49"),
                ask=Decimal("0.51"),
            )
        )
        repo.save_market_liquidity_snapshot(
            _liquidity_snapshot(
                market_id=market_id,
                snapshot_id="liquidity_future",
                observed_at=datetime(2026, 6, 16, 11, 0, tzinfo=UTC),
                available_at=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                bid=Decimal("0.89"),
                ask=Decimal("0.91"),
            )
        )
        feature = build_market_feature_snapshot(market_id, asof, repo=repo)

    assert feature.latest_price_snapshot_id == "price_old"
    assert feature.latest_liquidity_snapshot_id == "liquidity_old"
    assert feature.price == Decimal("0.5000000000")


def test_feature_snapshot_does_not_use_future_rule_snapshot_or_diff(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "future_rules.db")
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        feature = build_market_feature_snapshot(
            "mkt_rate_cut_rule_change_2026",
            asof,
            repo=repo,
        )

    assert feature.latest_rule_snapshot_id == "rule_rate_cut_rule_change_2026_v1"
    assert feature.latest_rule_diff_id is None


def test_feature_hash_is_deterministic(tmp_path: Path) -> None:
    session_factory = _session_factory(tmp_path, "feature_hash.db")
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        first = build_market_feature_snapshot(market_id, asof, repo=repo)
        second = build_market_feature_snapshot(market_id, asof, repo=repo)

    assert first.input_hash == second.input_hash
    assert first.feature_snapshot_id == second.feature_snapshot_id


def _session_factory(tmp_path: Path, filename: str):
    database_url = f"sqlite:///{tmp_path / filename}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)


def _price_snapshot(
    *,
    market_id: str,
    snapshot_id: str,
    observed_at: datetime,
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
        captured_at=available_at,
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
        captured_at=available_at,
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
