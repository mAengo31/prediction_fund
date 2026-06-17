from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.dataops.enums import CoverageScopeType
from prediction_desk.dataops.models import DataOpsCycleConfig
from prediction_desk.dataops.runner import run_dataops_cycle
from prediction_desk.dataops.service import DataOpsService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_dataops_service_sets_up_defaults_and_lists_objects(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_service.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        service = DataOpsService(PredictionMarketRepository(session))
        defaults = service.setup_default_dataops_objects()

    assert len(defaults["universes"]) >= 4
    assert len(defaults["collection_plans"]) >= 4


def test_dataops_cycle_runs_in_fixture_mode(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_cycle.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        result = run_dataops_cycle(
            DataOpsCycleConfig(asof_timestamp=ASOF, mode="FIXTURE"),
            repo=PredictionMarketRepository(session),
        )

    assert result.collection_run is not None
    assert result.collection_run.allow_network is False
    assert result.coverage_report is not None
    assert result.coverage_report.scope_type == CoverageScopeType.GLOBAL


def test_service_computes_coverage_and_gaps(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_service_coverage.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        service = DataOpsService(PredictionMarketRepository(session))
        service.run_collection_once(venue_names=["kalshi"], mode="FIXTURE")
        report = service.compute_coverage_report(scope_type=CoverageScopeType.GLOBAL)
        gaps = service.detect_gaps(
            scope_type=CoverageScopeType.GLOBAL,
            coverage_report=report,
        )

    assert report.total_markets >= 1
    assert isinstance(gaps, list)
