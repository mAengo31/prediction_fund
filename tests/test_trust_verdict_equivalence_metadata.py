from __future__ import annotations

from pathlib import Path

from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scoring.trust_verdict import build_trust_verdict
from tests.equivalence_helpers import ASOF, KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues


def test_trust_verdict_stores_equivalence_metadata_when_available(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'trust_equivalence.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        response = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            ASOF,
        )
        market = repo.get_market(KALSHI_RAIN)
        assert market is not None
        verdict = build_trust_verdict(
            market=market,
            rule_snapshot=repo.get_latest_rule_snapshot(KALSHI_RAIN),
            orderbook_snapshot=repo.get_latest_orderbook_snapshot(KALSHI_RAIN),
            asof_timestamp=ASOF,
            equivalence_assessments=[response.assessment],
        )

    assert verdict.metadata["equivalence"]["comparable_market_count"] == 1
    assert verdict.metadata["equivalence"]["latest_equivalence_assessment_ids"] == [
        response.assessment.equivalence_assessment_id
    ]
    assert "equivalence_assessment_ids" in verdict.data_versions


def test_trust_verdict_behavior_unchanged_without_equivalence(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'trust_no_equivalence.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        market = repo.get_market(KALSHI_RAIN)
        assert market is not None
        verdict = build_trust_verdict(
            market=market,
            rule_snapshot=repo.get_latest_rule_snapshot(KALSHI_RAIN),
            orderbook_snapshot=repo.get_latest_orderbook_snapshot(KALSHI_RAIN),
            asof_timestamp=ASOF,
        )

    assert "equivalence" not in verdict.metadata
    assert verdict.data_versions["equivalence_assessment_ids"] == []
