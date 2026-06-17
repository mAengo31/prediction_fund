from __future__ import annotations

from pathlib import Path

from prediction_desk.divergence.models import CrossVenueDivergenceRunConfig
from prediction_desk.divergence.runner import run_divergence_scan
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues
from tests.test_divergence_service import DIVERGENCE_ASOF


def test_runner_creates_run_and_summary(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'divergence_runner.db'}"
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
        result = run_divergence_scan(
            CrossVenueDivergenceRunConfig(
                name="runner test",
                asof_timestamp=DIVERGENCE_ASOF,
                equivalence_assessment_ids=[equivalence.assessment.equivalence_assessment_id],
                max_pairs=10,
            ),
            repo=repo,
        )

    assert result.run.assessments_created == 1
    assert result.summary.total_assessments == 1
    assert result.summary.material_divergence_rate > 0

