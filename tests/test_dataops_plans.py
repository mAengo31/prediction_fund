from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.dataops.plans import (
    create_default_collection_plans_if_missing,
    get_due_collection_plans,
    validate_collection_plan,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.paper_helpers import loaded_repo

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_default_collection_plans_created_idempotently(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "dataops_plans.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        first = create_default_collection_plans_if_missing(repo=repo)
        second = create_default_collection_plans_if_missing(repo=repo)

    assert [plan.collection_plan_id for plan in first] == [
        plan.collection_plan_id for plan in second
    ]
    assert all(plan.allow_network_default is False for plan in first)


def test_collection_plan_validation_rejects_bad_cadence_and_payloads(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "dataops_plan_validation.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        plan = create_default_collection_plans_if_missing(repo=repo)[0]
        invalid = plan.model_copy(
            update={
                "cadence_seconds": 0,
                "max_markets_per_run": 0,
                "max_payloads_per_run": 0,
                "endpoint_types": [],
            },
        )

    errors = validate_collection_plan(invalid)
    assert "INVALID_CADENCE_SECONDS" in errors
    assert "INVALID_MAX_PAYLOADS_PER_RUN" in errors
    assert "MISSING_ENDPOINT_TYPES" in errors


def test_due_collection_plans_are_active_and_created_asof(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "dataops_due_plans.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        plans = create_default_collection_plans_if_missing(repo=repo)
        due = get_due_collection_plans(datetime.now(tz=UTC), repo=repo)

    assert {plan.collection_plan_id for plan in plans} <= {
        plan.collection_plan_id for plan in due
    }
