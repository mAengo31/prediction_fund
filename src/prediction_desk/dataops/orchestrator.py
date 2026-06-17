"""Run-once read-only collection orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from prediction_desk.dataops.enums import CollectionRunMode, CollectionRunStatus
from prediction_desk.dataops.models import CollectionRun, CollectionRunResult, dataops_object_id
from prediction_desk.ingestion.scheduler import run_ingestion_once
from prediction_desk.ingestion.service import IngestionServiceError
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


class DataOpsCollectionError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_collection_once(
    *,
    plan_id: str | None = None,
    universe_id: str | None = None,
    venue_names: list[str] | None = None,
    market_ids: list[str] | None = None,
    endpoint_types: list[str] | None = None,
    mode: str = "FIXTURE",
    allow_network: bool = False,
    asof_timestamp: datetime | None = None,
    max_payloads: int | None = None,
    metadata: dict[str, Any] | None = None,
    repo: PredictionMarketRepository | None = None,
) -> CollectionRunResult:
    if repo is not None:
        return _run_collection_once(
            repo=repo,
            plan_id=plan_id,
            universe_id=universe_id,
            venue_names=venue_names,
            market_ids=market_ids,
            endpoint_types=endpoint_types,
            mode=mode,
            allow_network=allow_network,
            asof_timestamp=asof_timestamp,
            max_payloads=max_payloads,
            metadata=metadata,
        )
    with session_scope() as session:
        return _run_collection_once(
            repo=PredictionMarketRepository(session),
            plan_id=plan_id,
            universe_id=universe_id,
            venue_names=venue_names,
            market_ids=market_ids,
            endpoint_types=endpoint_types,
            mode=mode,
            allow_network=allow_network,
            asof_timestamp=asof_timestamp,
            max_payloads=max_payloads,
            metadata=metadata,
        )


def _run_collection_once(
    *,
    repo: PredictionMarketRepository,
    plan_id: str | None,
    universe_id: str | None,
    venue_names: list[str] | None,
    market_ids: list[str] | None,
    endpoint_types: list[str] | None,
    mode: str,
    allow_network: bool,
    asof_timestamp: datetime | None,
    max_payloads: int | None,
    metadata: dict[str, Any] | None,
) -> CollectionRunResult:
    asof = asof_timestamp or datetime.now(tz=UTC)
    plan = repo.get_collection_plan(plan_id) if plan_id else None
    if plan_id and plan is None:
        raise DataOpsCollectionError("collection_plan_not_found")
    normalized_mode = CollectionRunMode(str(mode).upper())
    if normalized_mode == CollectionRunMode.MANUAL_PUBLIC_FETCH and not allow_network:
        raise DataOpsCollectionError("public_network_disabled")
    resolved_venue_names = list(venue_names or (plan.venue_names if plan else []))
    if not resolved_venue_names:
        resolved_venue_names = _venues_from_markets(repo, market_ids)
    if not resolved_venue_names:
        resolved_venue_names = ["kalshi", "polymarket"]
    resolved_market_ids = _resolve_market_ids(repo, universe_id, market_ids, asof)
    resolved_endpoint_types = list(endpoint_types or (plan.endpoint_types if plan else []))
    payload_limit = max_payloads or (plan.max_payloads_per_run if plan else 100)
    created_at = datetime.now(tz=UTC)
    run = CollectionRun(
        collection_run_id=dataops_object_id(
            "collection_run",
            {
                "created_at": created_at,
                "plan_id": plan_id,
                "universe_id": universe_id,
                "mode": normalized_mode.value,
                "asof_timestamp": asof,
            },
        ),
        collection_plan_id=plan_id,
        universe_id=universe_id,
        created_at=created_at,
        started_at=created_at,
        status=CollectionRunStatus.RUNNING,
        mode=normalized_mode,
        asof_timestamp=asof,
        allow_network=allow_network,
        venue_names=sorted(set(resolved_venue_names), key=str.casefold),
        market_ids=resolved_market_ids,
        endpoint_types=resolved_endpoint_types,
        metadata={**dict(metadata or {}), "runner_version": "collection_orchestrator_v1"},
    )
    repo.save_collection_run(run)
    errors: list[dict[str, str]] = []
    counters = {
        "payloads_archived": 0,
        "markets_processed": 0,
        "price_snapshots_created": 0,
        "liquidity_snapshots_created": 0,
        "quality_reports_created": 0,
        "ingestion_runs_created": 0,
    }
    ingestion_mode = (
        "fixture" if normalized_mode == CollectionRunMode.FIXTURE else "manual_public_fetch"
    )
    for venue_name in run.venue_names:
        if counters["payloads_archived"] >= payload_limit:
            break
        try:
            result = run_ingestion_once(
                venue_name=venue_name,
                mode=ingestion_mode,
                limit=payload_limit,
                allow_network=allow_network,
                analyze_rules=plan.analyze_rules if plan else True,
                recompute_verdicts=plan.recompute_verdicts if plan else True,
                derive_market_data=plan.derive_market_data if plan else True,
                compute_quality=plan.compute_quality if plan else True,
                metadata={
                    "collection_run_id": run.collection_run_id,
                    "endpoint_types": resolved_endpoint_types,
                },
                repo=repo,
            )
            ingestion_run = result.ingestion.run
            counters["ingestion_runs_created"] += 1
            counters["payloads_archived"] += ingestion_run.payloads_archived
            counters["markets_processed"] += ingestion_run.markets_seen
            counters["price_snapshots_created"] += ingestion_run.price_snapshots_created
            counters["liquidity_snapshots_created"] += ingestion_run.liquidity_snapshots_created
            counters["quality_reports_created"] += ingestion_run.quality_reports_created
        except IngestionServiceError as exc:
            errors.append({"venue_name": venue_name, "code": exc.code})
    completed = run.model_copy(
        update={
            **counters,
            "completed_at": datetime.now(tz=UTC),
            "status": CollectionRunStatus.COMPLETED if not errors else CollectionRunStatus.PARTIAL,
            "errors_count": len(errors),
            "metadata": {**run.metadata, "errors": errors},
        }
    )
    repo.update_collection_run(completed)
    return CollectionRunResult(run=completed)


def _resolve_market_ids(
    repo: PredictionMarketRepository,
    universe_id: str | None,
    market_ids: list[str] | None,
    asof_timestamp: datetime,
) -> list[str]:
    if market_ids:
        return sorted(set(market_ids))
    if universe_id:
        members = repo.list_market_universe_members(
            universe_id=universe_id,
            asof_timestamp=asof_timestamp,
            limit=10000,
        )
        return sorted({member.market_id for member in members})
    return []


def _venues_from_markets(
    repo: PredictionMarketRepository,
    market_ids: list[str] | None,
) -> list[str]:
    names: set[str] = set()
    for market_id in market_ids or []:
        market = repo.get_market(market_id)
        if market is None:
            continue
        venue = repo.get_venue(market.venue_id)
        if venue is not None:
            names.add(venue.name)
        names.add(market.venue_id)
    return sorted(names, key=str.casefold)
