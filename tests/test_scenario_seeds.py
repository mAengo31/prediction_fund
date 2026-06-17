from __future__ import annotations

from datetime import timedelta

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scenario.seeds import build_scenario_seed_bundle
from tests.paper_helpers import MARKET_ID, loaded_repo
from tests.research_helpers import ASOF


def test_seed_bundle_hash_is_deterministic(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "scenario_seed.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        first = build_scenario_seed_bundle(MARKET_ID, ASOF, force=True, repo=repo)
        second = build_scenario_seed_bundle(MARKET_ID, ASOF, force=True, repo=repo)

    assert first.input_hash == second.input_hash
    assert first.output_hash == second.output_hash


def test_seed_bundle_builder_uses_only_asof_safe_inputs(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "scenario_seed_asof.db")
    future = ASOF + timedelta(days=1)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        current = repo.get_latest_rule_snapshot_asof(MARKET_ID, ASOF)
        assert current is not None
        repo.save_rule_snapshot(
            current.model_copy(
                update={
                    "rule_snapshot_id": "future_scenario_rule",
                    "captured_at": future,
                    "rule_hash": "future_scenario_hash",
                }
            )
        )

        bundle = build_scenario_seed_bundle(MARKET_ID, ASOF, force=True, repo=repo)

    assert bundle.rule_snapshot_id == current.rule_snapshot_id
    assert bundle.rule_snapshot_hash == current.rule_hash
