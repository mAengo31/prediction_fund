from __future__ import annotations

from datetime import timedelta

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scenario.service import ScenarioService
from tests.paper_helpers import loaded_repo
from tests.research_helpers import ASOF

SCENARIO_MARKET_ID = "mkt_sfo_rain_2026_09_01"


def test_service_imports_and_normalizes_fixture_artifacts(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "scenario_service.db")
    with factory.begin() as session:
        service = ScenarioService(PredictionMarketRepository(session))
        artifacts = service.import_fixture_artifacts(
            market_ids=[SCENARIO_MARKET_ID],
            asof_timestamp=ASOF,
        )
        features = [
            service.normalize_scenario_artifact(artifact.scenario_artifact_id)
            for artifact in artifacts
        ]

    assert artifacts
    assert features
    assert features[0].market_id == SCENARIO_MARKET_ID


def test_future_scenario_feature_is_not_returned_by_asof_lookup(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "scenario_service_asof.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ScenarioService(repo)
        artifact = service.import_fixture_artifacts(
            market_ids=[SCENARIO_MARKET_ID],
            asof_timestamp=ASOF,
        )[0]
        current = service.normalize_scenario_artifact(artifact.scenario_artifact_id)
        future = current.model_copy(
            update={
                "scenario_feature_snapshot_id": "future_scenario_feature",
                "available_at": ASOF + timedelta(days=1),
                "input_hash": "future_scenario_feature_input",
                "output_hash": "future_scenario_feature_output",
            }
        )
        repo.save_scenario_feature_snapshot(future)

        latest = service.get_latest_scenario_feature_asof(SCENARIO_MARKET_ID, ASOF)

    assert latest is not None
    assert latest.scenario_feature_snapshot_id == current.scenario_feature_snapshot_id
