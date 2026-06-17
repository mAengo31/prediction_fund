from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_asof_rule_snapshot_query_does_not_return_future_snapshot(tmp_path: Path) -> None:
    repo = _repo_with_samples(tmp_path)
    market_id = "mkt_rate_cut_rule_change_2026"

    earlier = repo.get_latest_rule_snapshot_asof(
        market_id,
        datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
    )
    later = repo.get_latest_rule_snapshot_asof(
        market_id,
        datetime(2026, 6, 17, 12, 0, tzinfo=UTC),
    )

    assert earlier is not None
    assert earlier.rule_snapshot_id == "rule_rate_cut_rule_change_2026_v1"
    assert later is not None
    assert later.rule_snapshot_id == "rule_rate_cut_rule_change_2026_v2"


def test_asof_orderbook_query_does_not_return_future_snapshot(tmp_path: Path) -> None:
    repo = _repo_with_samples(tmp_path)
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"

    earlier = repo.get_latest_orderbook_snapshot_asof(
        market_id,
        datetime(2026, 6, 16, 12, 30, tzinfo=UTC),
    )
    later = repo.get_latest_orderbook_snapshot_asof(
        market_id,
        datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
    )

    assert earlier is not None
    assert earlier.snapshot_id == "ob_cpi_yoy_at_least_3pct_2026_09_tight"
    assert later is not None
    assert later.snapshot_id == "ob_cpi_yoy_at_least_3pct_2026_09_wide"


def _repo_with_samples(tmp_path: Path) -> PredictionMarketRepository:
    database_url = f"sqlite:///{tmp_path / 'replay_asof.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    session = session_factory()
    repo = PredictionMarketRepository(session)
    load_sample_data(repo)
    session.commit()
    return repo
