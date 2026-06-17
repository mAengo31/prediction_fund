from __future__ import annotations

from datetime import timedelta

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.runner import run_replay
from prediction_desk.scenario.service import ScenarioService
from tests.paper_helpers import loaded_repo
from tests.research_helpers import ASOF

SCENARIO_MARKET_ID = "mkt_sfo_rain_2026_09_01"


def test_replay_includes_scenario_metadata_when_available(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "replay_scenario.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ScenarioService(repo)
        artifact = service.import_fixture_artifacts(
            market_ids=[SCENARIO_MARKET_ID],
            asof_timestamp=ASOF,
        )[0]
        feature = service.normalize_scenario_artifact(artifact.scenario_artifact_id)

        result = run_replay(
            ReplayRunConfig(
                start_time=ASOF,
                end_time=ASOF + timedelta(hours=1),
                interval_seconds=3600,
                policy_name="trust_verdict_v1",
                market_ids=[SCENARIO_MARKET_ID],
                persist_steps=False,
            ),
            repo=repo,
        )

    assert result.steps[0].metadata["latest_scenario_feature_snapshot_id"] == (
        feature.scenario_feature_snapshot_id
    )
    assert result.steps[0].metadata["scenario_confidence_score"] == (
        feature.scenario_confidence_score
    )
