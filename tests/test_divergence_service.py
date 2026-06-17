from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from prediction_desk.divergence.enums import DivergenceStatus
from prediction_desk.divergence.service import DivergenceService
from prediction_desk.equivalence.enums import ComparisonPermission
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.equivalence_helpers import (
    KALSHI_RAIN,
    POLYMARKET_RAIN,
    POLYMARKET_TEMP,
    ingest_fixture_venues,
)

DIVERGENCE_ASOF = datetime(2026, 6, 16, 12, 20, tzinfo=UTC)


def test_service_persists_snapshot_signals_and_assessment(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'divergence_service.db'}"
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
        analysis = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )
        duplicate = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )

    assert analysis.snapshot.comparable
    assert analysis.assessment.status == DivergenceStatus.MATERIAL_DIVERGENCE
    assert analysis.assessment.absolute_mid_gap is not None
    assert analysis.signals
    assert (
        duplicate.assessment.divergence_assessment_id
        == analysis.assessment.divergence_assessment_id
    )


def test_service_uses_only_asof_available_market_data(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'divergence_asof.db'}"
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
        current = repo.get_latest_price_snapshot_asof(POLYMARKET_RAIN, DIVERGENCE_ASOF)
        assert current is not None
        future = current.model_copy(
            update={
                "price_snapshot_id": "future_divergence_price",
                "available_at": DIVERGENCE_ASOF + timedelta(days=1),
                "data_hash": "future_divergence_price_hash",
                "price": 0,
                "mid": 0,
            }
        )
        repo.save_market_price_snapshot(future)
        analysis = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
            force=True,
        )

    assert analysis.snapshot.right_price_snapshot_id == current.price_snapshot_id


def test_do_not_compare_equivalence_produces_do_not_compare_status(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'divergence_do_not_compare.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        equivalence = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_TEMP,
            DIVERGENCE_ASOF,
        )
        assert equivalence.assessment.comparison_permission in {
            ComparisonPermission.DO_NOT_COMPARE,
            ComparisonPermission.MANUAL_REVIEW,
        }
        analysis = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )

    if equivalence.assessment.comparison_permission == ComparisonPermission.DO_NOT_COMPARE:
        assert analysis.assessment.status == DivergenceStatus.DO_NOT_COMPARE
    else:
        assert analysis.assessment.status == DivergenceStatus.NEEDS_REVIEW


def test_future_divergence_assessment_not_returned_by_asof_lookup(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'divergence_future.db'}"
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
        analysis = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )
        future = analysis.assessment.model_copy(
            update={
                "divergence_assessment_id": "future_divergence_assessment",
                "available_at": DIVERGENCE_ASOF + timedelta(days=1),
                "output_hash": "future_divergence_output_hash",
            }
        )
        repo.save_divergence_assessment(future)
        latest = repo.get_latest_divergence_assessment_asof(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            DIVERGENCE_ASOF + timedelta(hours=1),
        )

    assert latest is not None
    assert latest.divergence_assessment_id == analysis.assessment.divergence_assessment_id
