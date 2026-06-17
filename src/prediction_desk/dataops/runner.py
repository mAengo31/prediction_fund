"""Synchronous dataops cycle runner."""

from __future__ import annotations

from prediction_desk.dataops.enums import CoverageScopeType
from prediction_desk.dataops.models import DataOpsCycleConfig, DataOpsCycleResult
from prediction_desk.dataops.service import DataOpsService
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


def run_dataops_cycle(
    config: DataOpsCycleConfig,
    *,
    repo: PredictionMarketRepository | None = None,
) -> DataOpsCycleResult:
    if repo is not None:
        return _run_dataops_cycle(repo, config)
    with session_scope() as session:
        return _run_dataops_cycle(PredictionMarketRepository(session), config)


def _run_dataops_cycle(
    repo: PredictionMarketRepository,
    config: DataOpsCycleConfig,
) -> DataOpsCycleResult:
    service = DataOpsService(repo)
    metadata = dict(config.metadata)
    if config.setup_defaults:
        defaults = service.setup_default_dataops_objects()
        metadata["default_universes"] = len(defaults["universes"])
        metadata["default_collection_plans"] = len(defaults["collection_plans"])
    collection_run = None
    if config.run_collection:
        collection_run = service.run_collection_once(
            plan_id=config.plan_id,
            universe_id=config.universe_id,
            venue_names=config.venue_names,
            market_ids=config.market_ids,
            mode=config.mode.value,
            allow_network=config.allow_network,
            asof_timestamp=config.asof_timestamp,
            max_payloads=config.max_payloads,
            metadata={"cycle_name": config.name, **config.metadata},
        ).run
    coverage_report = None
    if config.compute_coverage:
        coverage_report = service.compute_coverage_report(
            scope_type=CoverageScopeType.UNIVERSE
            if config.universe_id
            else CoverageScopeType.GLOBAL,
            universe_id=config.universe_id,
            asof_timestamp=config.asof_timestamp,
        )
    gaps = []
    if config.detect_gaps:
        gaps = service.detect_gaps(
            scope_type=CoverageScopeType.UNIVERSE
            if config.universe_id
            else CoverageScopeType.GLOBAL,
            universe_id=config.universe_id,
            asof_timestamp=config.asof_timestamp,
            coverage_report=coverage_report,
        )
    return DataOpsCycleResult(
        collection_run=collection_run,
        coverage_report=coverage_report,
        gaps=gaps,
        metadata=metadata,
    )

