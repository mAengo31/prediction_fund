from __future__ import annotations

from pathlib import Path

from prediction_desk.equivalence.models import EquivalenceRunConfig
from prediction_desk.equivalence.runner import run_equivalence_scan
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.equivalence_helpers import ASOF, KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues


def test_equivalence_run_creates_candidates_assessments_summary_and_classes(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_runner.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = run_equivalence_scan(
            EquivalenceRunConfig(
                name="test equivalence",
                asof_timestamp=ASOF,
                market_ids=[KALSHI_RAIN, POLYMARKET_RAIN],
                min_candidate_score=40,
                max_pairs=10,
                build_classes=True,
            ),
            repo=repo,
        )
        stored_run = repo.get_equivalence_run(result.run.equivalence_run_id)
        stored_summary = repo.get_equivalence_run_summary(result.run.equivalence_run_id)

    assert result.summary.total_candidates == 1
    assert result.summary.total_assessments == 1
    assert result.summary.comparable_rate > 0
    assert result.classes
    assert stored_run is not None
    assert stored_summary is not None
