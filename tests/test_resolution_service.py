from __future__ import annotations

from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.resolution.enums import ParseStatus
from prediction_desk.resolution.service import ResolutionCorpusService


def test_service_persists_predicate_and_ambiguity_assessment(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resolution_service.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        clean, *_ = load_sample_data(repo)
        analysis = ResolutionCorpusService(repo).analyze_latest_rule_snapshot(
            clean.market.market_id
        )

    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        predicate = repo.get_resolution_predicate_for_rule_snapshot(
            clean.rule_snapshot.rule_snapshot_id
        )
        assessment = repo.get_ambiguity_assessment_for_rule_snapshot(
            clean.rule_snapshot.rule_snapshot_id
        )

    assert analysis.predicate.parse_status is ParseStatus.PARSED
    assert predicate is not None
    assert predicate.predicate_id == analysis.predicate.predicate_id
    assert assessment is not None
    assert assessment.assessment_id == analysis.ambiguity_assessment.assessment_id


def test_service_avoids_duplicate_analysis_unless_force(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resolution_service.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        clean, *_ = load_sample_data(repo)
        service = ResolutionCorpusService(repo)
        first = service.analyze_latest_rule_snapshot(clean.market.market_id)
        second = service.analyze_latest_rule_snapshot(clean.market.market_id)
        forced = service.analyze_latest_rule_snapshot(clean.market.market_id, force=True)

    assert first.predicate.predicate_id == second.predicate.predicate_id
    assert first.ambiguity_assessment.assessment_id == second.ambiguity_assessment.assessment_id
    assert forced.predicate.predicate_id == first.predicate.predicate_id
    assert forced.ambiguity_assessment.assessment_id == first.ambiguity_assessment.assessment_id


def test_service_persists_latest_rule_snapshot_diff(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'resolution_service.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        *_, rule_change = load_sample_data(repo)
        diff = ResolutionCorpusService(repo).diff_latest_two_rule_snapshots(
            rule_change.market.market_id
        )
        persisted = repo.get_rule_snapshot_diff(
            diff.from_rule_snapshot_id,
            diff.to_rule_snapshot_id,
        )

    assert persisted is not None
    assert persisted.diff_id == diff.diff_id
    assert diff.resolution_source_changed is True
