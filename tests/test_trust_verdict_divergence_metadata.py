from __future__ import annotations

from pathlib import Path

from prediction_desk.divergence.service import DivergenceService
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scoring.trust_verdict import build_trust_verdict
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues
from tests.test_divergence_service import DIVERGENCE_ASOF


def test_trust_verdict_stores_divergence_metadata_when_available(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'trust_divergence.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        equivalence = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            DIVERGENCE_ASOF,
        )
        divergence = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )
        market = repo.get_market(KALSHI_RAIN)
        assert market is not None
        verdict = build_trust_verdict(
            market=market,
            rule_snapshot=repo.get_latest_rule_snapshot(KALSHI_RAIN),
            orderbook_snapshot=repo.get_latest_orderbook_snapshot(KALSHI_RAIN),
            asof_timestamp=DIVERGENCE_ASOF,
            divergence_assessments=[divergence.assessment],
        )

    assert verdict.metadata["divergence"]["material_divergence_count"] == 1
    assert verdict.metadata["divergence"]["max_divergence_score"] > 0
    assert verdict.data_versions["divergence_assessment_ids"] == [
        divergence.assessment.divergence_assessment_id
    ]


def test_trust_verdict_behavior_unchanged_without_divergence(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'trust_no_divergence.db'}"
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
            asof_timestamp=DIVERGENCE_ASOF,
        )

    assert "divergence" not in verdict.metadata
    assert verdict.data_versions["divergence_assessment_ids"] == []

