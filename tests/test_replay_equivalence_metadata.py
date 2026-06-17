from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.service import ReplayService
from tests.equivalence_helpers import ASOF, KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues


def test_replay_step_stores_equivalence_metadata(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_equivalence.db'}"
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
        result = ReplayService(repo).run(
            ReplayRunConfig(
                name="replay equivalence",
                policy_name="trust_verdict_v1",
                start_time=ASOF,
                end_time=ASOF + timedelta(seconds=1),
                interval_seconds=3600,
                market_ids=[KALSHI_RAIN],
                max_steps=10,
            )
        )

    step = result.steps[0]
    assert step.metadata["latest_equivalence_assessment_ids"] == [
        response.assessment.equivalence_assessment_id
    ]
    assert step.metadata["count_comparable_markets"] == 1
    assert step.metadata["count_manual_review_equivalence"] == 0
    assert step.metadata["count_do_not_compare_equivalence"] == 0
