from __future__ import annotations

import pytest

from prediction_desk.dataops.orchestrator import DataOpsCollectionError, run_collection_once
from prediction_desk.dataops.plans import create_default_collection_plans_if_missing
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_collection_run_fixture_mode_uses_no_network(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_collection.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        plan = create_default_collection_plans_if_missing(repo=repo)[0]
        result = run_collection_once(
            plan_id=plan.collection_plan_id,
            venue_names=["kalshi"],
            mode="FIXTURE",
            allow_network=False,
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.allow_network is False
    assert result.run.payloads_archived >= 1
    assert result.run.price_snapshots_created >= 1


def test_manual_public_fetch_without_allow_network_fails_safely(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_collection_no_network.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        with pytest.raises(DataOpsCollectionError) as exc:
            run_collection_once(
                venue_names=["kalshi"],
                mode="MANUAL_PUBLIC_FETCH",
                allow_network=False,
                repo=repo,
            )

    assert exc.value.code == "public_network_disabled"
