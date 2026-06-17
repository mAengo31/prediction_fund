from __future__ import annotations

from pathlib import Path

from prediction_desk.equivalence.matching import generate_equivalence_candidates
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.equivalence_helpers import ASOF, KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues


def test_candidate_generation_prefers_cross_venue_pairs(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_matching.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        candidates = generate_equivalence_candidates(
            repo=repo,
            market_ids=[KALSHI_RAIN, POLYMARKET_RAIN],
            asof_timestamp=ASOF,
            min_candidate_score=40,
            max_pairs=10,
        )

    assert len(candidates) == 1
    assert candidates[0].left_market_id != candidates[0].right_market_id
    assert candidates[0].candidate_score >= 40
    assert "CROSS_VENUE_PAIR" in candidates[0].candidate_reasons


def test_candidate_generation_respects_max_pairs(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_matching_max.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        candidates = generate_equivalence_candidates(
            repo=repo,
            market_ids=None,
            asof_timestamp=ASOF,
            venue_names=["kalshi", "polymarket"],
            min_candidate_score=0,
            max_pairs=1,
        )

    assert len(candidates) <= 1
