from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from prediction_desk.dataops.enums import CollectionRunMode
from prediction_desk.dataops.models import (
    BackfillJobCreateRequest,
    CollectionPlan,
    DataOpsCycleConfig,
    collection_plan_id,
    universe_id,
)

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_dataops_default_ids_are_deterministic() -> None:
    assert universe_id("all_active_prediction_markets_v1", "v1") == universe_id(
        "all_active_prediction_markets_v1",
        "v1",
    )
    assert collection_plan_id("fixture_full_loop_v1", "v1") == collection_plan_id(
        "fixture_full_loop_v1",
        "v1",
    )


def test_collection_plan_model_uses_decimal_thresholds() -> None:
    plan = CollectionPlan(
        collection_plan_id="plan_test",
        plan_name="fixture",
        plan_version="v1",
        created_at=ASOF,
        is_active=True,
        universe_id=None,
        venue_names=["kalshi"],
        endpoint_types=["ORDERBOOK"],
        cadence_seconds=60,
        lookback_seconds=None,
        max_markets_per_run=10,
        max_payloads_per_run=10,
        allow_network_default=False,
        derive_market_data=True,
        compute_quality=True,
        analyze_rules=True,
        recompute_verdicts=True,
        metadata={"min_depth": Decimal("1.25")},
    )

    assert plan.allow_network_default is False
    assert plan.metadata["min_depth"] == Decimal("1.25")


def test_backfill_create_request_requires_endpoint_types() -> None:
    with pytest.raises(ValidationError):
        BackfillJobCreateRequest(
            venue_name="polymarket",
            endpoint_types=[],
            start_time=ASOF,
            end_time=ASOF,
        )


def test_cycle_config_defaults_to_fixture_no_network() -> None:
    config = DataOpsCycleConfig(asof_timestamp=ASOF)

    assert config.mode == CollectionRunMode.FIXTURE
    assert config.allow_network is False
