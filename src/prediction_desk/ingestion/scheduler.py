"""Run-once ingestion scheduler orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from prediction_desk.ingestion.cursors import cursor_from_mapping
from prediction_desk.ingestion.models import IngestionCursor, IngestionRunResult
from prediction_desk.ingestion.service import IngestionService, IngestionServiceError
from prediction_desk.marketdata.service import MarketDataService, MarketDataServiceError
from prediction_desk.persistence.database import session_scope

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


class IngestionSchedulerModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class IngestionRunOnceRequest(IngestionSchedulerModel):
    venue_name: str
    mode: str = "fixture"
    limit: int = Field(default=10, ge=1, le=100)
    market_ids: list[str] | None = None
    endpoint_types: list[str] | None = None
    allow_network: bool = False
    analyze_rules: bool = True
    recompute_verdicts: bool = True
    derive_market_data: bool = True
    compute_quality: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestionRunOnceResult(IngestionSchedulerModel):
    ingestion: IngestionRunResult
    cursors: list[IngestionCursor] = Field(default_factory=list)
    price_snapshots_created: int = 0
    liquidity_snapshots_created: int = 0
    quality_reports_created: int = 0


def run_ingestion_once(
    *,
    venue_name: str,
    mode: str = "fixture",
    limit: int = 10,
    market_ids: list[str] | None = None,
    endpoint_types: list[str] | None = None,
    allow_network: bool = False,
    analyze_rules: bool = True,
    recompute_verdicts: bool = True,
    derive_market_data: bool = True,
    compute_quality: bool = True,
    metadata: dict[str, Any] | None = None,
    repo: PredictionMarketRepository | None = None,
    database_url: str | None = None,
) -> IngestionRunOnceResult:
    if repo is not None:
        return _run_ingestion_once(
            repo=repo,
            venue_name=venue_name,
            mode=mode,
            limit=limit,
            market_ids=market_ids,
            endpoint_types=endpoint_types,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
            compute_quality=compute_quality,
            metadata=metadata or {},
        )
    with session_scope(database_url) as session:
        from prediction_desk.persistence.repositories import PredictionMarketRepository

        return _run_ingestion_once(
            repo=PredictionMarketRepository(session),
            venue_name=venue_name,
            mode=mode,
            limit=limit,
            market_ids=market_ids,
            endpoint_types=endpoint_types,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
            compute_quality=compute_quality,
            metadata=metadata or {},
        )


def _run_ingestion_once(
    *,
    repo: PredictionMarketRepository,
    venue_name: str,
    mode: str,
    limit: int,
    market_ids: list[str] | None,
    endpoint_types: list[str] | None,
    allow_network: bool,
    analyze_rules: bool,
    recompute_verdicts: bool,
    derive_market_data: bool,
    compute_quality: bool,
    metadata: dict[str, Any],
) -> IngestionRunOnceResult:
    service = IngestionService(repo)
    normalized_mode = mode.lower()
    if normalized_mode == "fixture":
        ingestion = service.ingest_fixture_payloads(
            venue_name=venue_name,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )
    elif normalized_mode == "manual_public_fetch":
        if not allow_network:
            raise IngestionServiceError("public_network_disabled")
        ingestion = service.ingest_public_endpoint_payloads(
            venue_name=venue_name,
            endpoint_types=endpoint_types,
            market_ids=market_ids,
            limit=limit,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )
    else:
        raise IngestionServiceError("unsupported_ingestion_mode")

    run = ingestion.run.model_copy(update={"metadata": {**ingestion.run.metadata, **metadata}})
    repo.update_ingestion_run(run)
    now = datetime.now(tz=UTC)
    mappings = repo.list_venue_market_mappings(venue_name=run.venue_name, limit=500)
    cursors: list[IngestionCursor] = []
    quality_reports_created = 0
    market_data = MarketDataService(repo)
    for mapping in mappings:
        for endpoint_type in run.endpoint_types or ["UNKNOWN"]:
            cursor = cursor_from_mapping(
                run=run,
                mapping=mapping,
                endpoint_type=endpoint_type,
                last_success_at=now,
            )
            repo.upsert_ingestion_cursor(cursor)
            cursors.append(cursor)
        if compute_quality and mapping.canonical_market_id is not None:
            try:
                market_data.compute_market_data_quality(
                    mapping.canonical_market_id,
                    now,
                    wide_spread_threshold=Decimal("0.10"),
                )
                quality_reports_created += 1
            except MarketDataServiceError:
                continue
    if quality_reports_created:
        run.quality_reports_created += quality_reports_created
        repo.update_ingestion_run(run)
        ingestion = ingestion.model_copy(update={"run": run})
    return IngestionRunOnceResult(
        ingestion=ingestion,
        cursors=cursors,
        price_snapshots_created=run.price_snapshots_created,
        liquidity_snapshots_created=run.liquidity_snapshots_created,
        quality_reports_created=run.quality_reports_created,
    )
