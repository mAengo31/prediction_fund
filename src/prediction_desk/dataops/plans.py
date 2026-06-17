"""Collection plan defaults and validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from prediction_desk.dataops.models import CollectionPlan, collection_plan_id
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository

DEFAULT_COLLECTION_PLANS: tuple[dict[str, Any], ...] = (
    {
        "plan_name": "fixture_full_loop_v1",
        "venue_names": ["kalshi", "polymarket"],
        "endpoint_types": ["MARKET_LIST", "MARKET_DETAIL", "ORDERBOOK", "PRICE_HISTORY"],
        "cadence_seconds": 3600,
        "max_markets_per_run": 100,
        "max_payloads_per_run": 100,
        "allow_network_default": False,
        "metadata": {"fixture_safe": True},
    },
    {
        "plan_name": "read_only_market_catalog_v1",
        "venue_names": ["kalshi", "polymarket"],
        "endpoint_types": ["MARKET_LIST", "MARKET_DETAIL"],
        "cadence_seconds": 3600,
        "max_markets_per_run": 100,
        "max_payloads_per_run": 100,
        "allow_network_default": False,
    },
    {
        "plan_name": "read_only_orderbook_snapshots_v1",
        "venue_names": ["kalshi", "polymarket"],
        "endpoint_types": ["ORDERBOOK"],
        "cadence_seconds": 300,
        "max_markets_per_run": 100,
        "max_payloads_per_run": 100,
        "allow_network_default": False,
    },
    {
        "plan_name": "read_only_price_history_v1",
        "venue_names": ["polymarket"],
        "endpoint_types": ["PRICE_HISTORY"],
        "cadence_seconds": 86400,
        "lookback_seconds": 86400,
        "max_markets_per_run": 100,
        "max_payloads_per_run": 100,
        "allow_network_default": False,
    },
)


def create_default_collection_plans_if_missing(
    *,
    repo: PredictionMarketRepository | None = None,
) -> list[CollectionPlan]:
    if repo is not None:
        return _create_default_collection_plans_if_missing(repo)
    with session_scope() as session:
        return _create_default_collection_plans_if_missing(PredictionMarketRepository(session))


def get_due_collection_plans(
    asof_timestamp: datetime,
    *,
    repo: PredictionMarketRepository | None = None,
) -> list[CollectionPlan]:
    if repo is not None:
        return _get_due_collection_plans(repo, asof_timestamp)
    with session_scope() as session:
        return _get_due_collection_plans(PredictionMarketRepository(session), asof_timestamp)


def validate_collection_plan(plan: CollectionPlan) -> list[str]:
    errors: list[str] = []
    if plan.cadence_seconds <= 0:
        errors.append("INVALID_CADENCE_SECONDS")
    if plan.max_markets_per_run <= 0:
        errors.append("INVALID_MAX_MARKETS_PER_RUN")
    if plan.max_payloads_per_run <= 0:
        errors.append("INVALID_MAX_PAYLOADS_PER_RUN")
    if not plan.endpoint_types:
        errors.append("MISSING_ENDPOINT_TYPES")
    return errors


def _create_default_collection_plans_if_missing(
    repo: PredictionMarketRepository,
) -> list[CollectionPlan]:
    now = datetime.now(tz=UTC)
    plans: list[CollectionPlan] = []
    for spec in DEFAULT_COLLECTION_PLANS:
        name = str(spec["plan_name"])
        version = "v1"
        pid = collection_plan_id(name, version)
        existing = repo.get_collection_plan(pid)
        if existing is not None:
            plans.append(existing)
            continue
        plan = CollectionPlan(
            collection_plan_id=pid,
            plan_name=name,
            plan_version=version,
            created_at=now,
            is_active=True,
            universe_id=_optional_str_spec(spec, "universe_id"),
            venue_names=_list_spec(spec, "venue_names"),
            endpoint_types=_list_spec(spec, "endpoint_types"),
            cadence_seconds=_int_spec(spec, "cadence_seconds"),
            lookback_seconds=_optional_int_spec(spec, "lookback_seconds"),
            max_markets_per_run=_int_spec(spec, "max_markets_per_run"),
            max_payloads_per_run=_int_spec(spec, "max_payloads_per_run"),
            allow_network_default=bool(spec.get("allow_network_default", False)),
            derive_market_data=bool(spec.get("derive_market_data", True)),
            compute_quality=bool(spec.get("compute_quality", True)),
            analyze_rules=bool(spec.get("analyze_rules", True)),
            recompute_verdicts=bool(spec.get("recompute_verdicts", True)),
            metadata=_dict_spec(spec, "metadata"),
        )
        errors = validate_collection_plan(plan)
        if errors:
            raise ValueError(",".join(errors))
        plans.append(repo.save_collection_plan(plan))
    return plans


def _get_due_collection_plans(
    repo: PredictionMarketRepository,
    asof_timestamp: datetime,
) -> list[CollectionPlan]:
    return [
        plan
        for plan in repo.list_collection_plans(limit=1000)
        if plan.is_active and _as_utc(plan.created_at) <= _as_utc(asof_timestamp)
    ]


def _list_spec(spec: dict[str, Any], key: str) -> list[str]:
    value = spec.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dict_spec(spec: dict[str, Any], key: str) -> dict[str, Any]:
    value = spec.get(key, {})
    return dict(value) if isinstance(value, dict) else {}


def _optional_str_spec(spec: dict[str, Any], key: str) -> str | None:
    value = spec.get(key)
    return str(value) if value is not None else None


def _int_spec(spec: dict[str, Any], key: str) -> int:
    value = spec[key]
    if not isinstance(value, int):
        return int(str(value))
    return value


def _optional_int_spec(spec: dict[str, Any], key: str) -> int | None:
    value = spec.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        return int(str(value))
    return value


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
