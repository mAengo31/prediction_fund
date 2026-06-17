from __future__ import annotations

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scenario.enums import ScenarioRunMode, ScenarioRunStatus
from prediction_desk.scenario.models import ScenarioRunConfig
from prediction_desk.scenario.runner import run_scenario_import
from tests.paper_helpers import loaded_repo
from tests.research_helpers import ASOF

SCENARIO_MARKET_ID = "mkt_sfo_rain_2026_09_01"


def test_scenario_runner_imports_fixtures_and_creates_summary(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "scenario_runner.db")
    with factory.begin() as session:
        result = run_scenario_import(
                ScenarioRunConfig(
                    asof_timestamp=ASOF,
                    market_ids=[SCENARIO_MARKET_ID],
                mode=ScenarioRunMode.IMPORT_FIXTURES,
                max_items=10,
            ),
            repo=PredictionMarketRepository(session),
        )

    assert result.run.status == ScenarioRunStatus.COMPLETED
    assert result.summary.total_artifacts >= 1
    assert result.summary.total_features >= 1
