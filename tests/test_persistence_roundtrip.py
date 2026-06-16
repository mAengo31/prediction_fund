from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scoring.trust_verdict import build_trust_verdict


def test_persistence_roundtrip_for_core_objects(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'prediction_desk_test.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    clean, _ = sample_markets()
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        repo.save_venue(clean.venue)
        repo.save_event(clean.event)
        repo.create_market(clean.market)
        for outcome in clean.outcomes:
            repo.save_outcome(outcome)
        repo.save_rule_snapshot(clean.rule_snapshot)
        repo.save_orderbook_snapshot(clean.orderbook_snapshot)
        verdict = build_trust_verdict(
            market=clean.market,
            rule_snapshot=clean.rule_snapshot,
            orderbook_snapshot=clean.orderbook_snapshot,
            asof_timestamp=asof,
        )
        repo.save_trust_verdict(verdict)

    with session_factory() as session:
        repo = PredictionMarketRepository(session)

        market = repo.get_market(clean.market.market_id)
        rule_snapshot = repo.get_latest_rule_snapshot(clean.market.market_id)
        orderbook_snapshot = repo.get_orderbook_snapshot(clean.orderbook_snapshot.snapshot_id)
        verdict = repo.get_latest_trust_verdict(clean.market.market_id)

        assert market is not None
        assert market.market_id == clean.market.market_id
        assert rule_snapshot is not None
        assert rule_snapshot.rule_hash == clean.rule_snapshot.rule_hash
        assert orderbook_snapshot is not None
        assert orderbook_snapshot.bids[0].price == Decimal("0.52")
        assert orderbook_snapshot.asks[0].quantity == Decimal("120")
        assert verdict is not None
        assert verdict.action is VerdictAction.ALLOW
        assert verdict.resolution_risk_score == 0
        assert verdict.liquidity_risk_score == 10
