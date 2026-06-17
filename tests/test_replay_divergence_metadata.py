from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from prediction_desk.divergence.service import DivergenceService
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.service import ReplayService
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues
from tests.test_divergence_service import DIVERGENCE_ASOF


def test_replay_step_stores_divergence_metadata(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_divergence.db'}"
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
        result = ReplayService(repo).run(
            ReplayRunConfig(
                name="replay divergence",
                policy_name="trust_verdict_v1",
                start_time=DIVERGENCE_ASOF,
                end_time=DIVERGENCE_ASOF + timedelta(seconds=1),
                interval_seconds=3600,
                market_ids=[KALSHI_RAIN],
                max_steps=10,
            )
        )

    step = result.steps[0]
    assert step.metadata["latest_divergence_assessment_ids"] == [
        divergence.assessment.divergence_assessment_id
    ]
    assert step.metadata["material_divergence_count"] == 1
    assert step.metadata["max_divergence_score"] > 0

