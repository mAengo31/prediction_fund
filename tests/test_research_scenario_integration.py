from __future__ import annotations

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.research.enums import ResearchFeatureSource, ResearchSignalType
from prediction_desk.research.features import build_research_features
from prediction_desk.research.strategies import strategy_from_definition
from prediction_desk.scenario.service import ScenarioService
from tests.paper_helpers import MARKET_ID, loaded_repo
from tests.research_helpers import ASOF, research_feature, strategy_definition

SCENARIO_MARKET_ID = "mkt_sfo_rain_2026_09_01"


def test_scenario_feature_integrates_into_research_feature_snapshot(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "research_scenario_feature.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ScenarioService(repo)
        artifact = service.import_fixture_artifacts(
            market_ids=[SCENARIO_MARKET_ID],
            asof_timestamp=ASOF,
        )[0]
        scenario_feature = service.normalize_scenario_artifact(
            artifact.scenario_artifact_id
        )

        features = build_research_features(
            SCENARIO_MARKET_ID,
            ASOF,
            include_sources=["SCENARIO"],
            force=True,
            repo=repo,
        )

    assert features[0].feature_source == ResearchFeatureSource.SCENARIO_SIMULATION_PLACEHOLDER
    assert (
        features[0].values["scenario_feature_snapshot_id"]
        == scenario_feature.scenario_feature_snapshot_id
    )


def test_existing_default_strategies_ignore_scenario_aggression(tmp_path) -> None:
    strategy = strategy_from_definition(strategy_definition("baseline_research_only_v1"))
    features = [
        research_feature(
            ResearchFeatureSource.SCENARIO_SIMULATION_PLACEHOLDER,
            {"scenario_confidence_score": 95, "narrative_risk_score": 5},
        )
    ]

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, features, {})

    assert result.signals[0].signal_type == ResearchSignalType.REVIEW_ONLY
    assert result.proposals[0].intent_type == "RESEARCH_ONLY"


def test_scenario_context_strategy_produces_watch_or_review_only_without_proposals() -> None:
    strategy = strategy_from_definition(strategy_definition("scenario_context_research_v1"))
    features = [
        research_feature(
            ResearchFeatureSource.SCENARIO_SIMULATION_PLACEHOLDER,
            {
                "scenario_feature_snapshot_id": "scenario_feature_test",
                "scenario_confidence_score": 62,
                "scenario_uncertainty_score": 38,
                "narrative_risk_score": 20,
                "shock_risk_score": 15,
                "polarization_score": 25,
                "key_scenario_labels": ["context narrows"],
            },
        )
    ]

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, features, {})

    assert result.signals[0].signal_type == ResearchSignalType.WATCH
    assert not result.proposals
