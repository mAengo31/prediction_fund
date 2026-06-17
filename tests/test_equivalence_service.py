from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from prediction_desk.domain.enums import MarketStatus, MarketType, VenueType
from prediction_desk.domain.models import Event, Market, Outcome, Venue
from prediction_desk.equivalence.enums import ComparisonPermission, EquivalenceStatus
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.equivalence_helpers import (
    ASOF,
    KALSHI_RAIN,
    POLYMARKET_RAIN,
    POLYMARKET_TEMP,
    ingest_fixture_venues,
)


def test_service_persists_assessment_and_outcome_mappings(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_service.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = EquivalenceService(repo)
        response = service.assess_market_equivalence(KALSHI_RAIN, POLYMARKET_RAIN, ASOF)
        duplicate = service.assess_market_equivalence(KALSHI_RAIN, POLYMARKET_RAIN, ASOF)

    assert response.assessment.status in {
        EquivalenceStatus.EQUIVALENT,
        EquivalenceStatus.NEAR_EQUIVALENT,
    }
    assert response.assessment.comparison_permission in {
        ComparisonPermission.COMPARABLE,
        ComparisonPermission.COMPARABLE_WITH_HAIRCUT,
    }
    assert response.outcome_mappings
    assert (
        duplicate.assessment.equivalence_assessment_id
        == response.assessment.equivalence_assessment_id
    )


def test_service_classifies_different_deadline_or_threshold_as_not_equivalent(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_service_negative.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        response = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_TEMP,
            ASOF,
        )

    assert response.assessment.status in {
        EquivalenceStatus.NOT_EQUIVALENT,
        EquivalenceStatus.NEEDS_REVIEW,
    }
    assert response.assessment.comparison_permission in {
        ComparisonPermission.DO_NOT_COMPARE,
        ComparisonPermission.MANUAL_REVIEW,
    }


def test_missing_rule_data_leads_to_needs_review(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_service_missing.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_bare_market(repo, "left", "Will NYC record rain?")
        _save_bare_market(repo, "right", "Will NYC record rain?")
        response = EquivalenceService(repo).assess_market_equivalence("left", "right", ASOF)

    assert response.assessment.status == EquivalenceStatus.NEEDS_REVIEW
    assert response.assessment.insufficient_rule_data


def test_future_equivalence_assessment_not_returned_by_asof_lookup(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'equiv_service_asof.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = EquivalenceService(repo)
        response = service.assess_market_equivalence(KALSHI_RAIN, POLYMARKET_RAIN, ASOF)
        future = response.assessment.model_copy(
            update={
                "equivalence_assessment_id": "future_equivalence_assessment",
                "available_at": ASOF + timedelta(days=1),
                "output_hash": "future_output_hash",
            }
        )
        repo.save_market_equivalence_assessment(future)
        latest = repo.get_latest_equivalence_assessment_asof(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            ASOF + timedelta(hours=1),
        )

    assert latest is not None
    assert latest.equivalence_assessment_id == response.assessment.equivalence_assessment_id


def _save_bare_market(repo: PredictionMarketRepository, market_id: str, title: str) -> None:
    repo.save_venue(
        Venue(
            venue_id=f"venue_{market_id}",
            name=f"Venue {market_id}",
            venue_type=VenueType.OTHER,
        )
    )
    repo.save_event(
        Event(
            event_id=f"event_{market_id}",
            venue_id=f"venue_{market_id}",
            title=title,
            category="weather",
        )
    )
    repo.create_market(
        Market(
            market_id=market_id,
            venue_id=f"venue_{market_id}",
            event_id=f"event_{market_id}",
            title=title,
            market_type=MarketType.BINARY,
            status=MarketStatus.ACTIVE,
        )
    )
    repo.save_outcome(
        Outcome(outcome_id=f"{market_id}_yes", market_id=market_id, label="Yes", payout=1)
    )
    repo.save_outcome(
        Outcome(outcome_id=f"{market_id}_no", market_id=market_id, label="No", payout=0)
    )
