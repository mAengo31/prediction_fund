"""Service facade for read-only dataops workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from prediction_desk.dataops.backfill import (
    DataOpsBackfillError,
)
from prediction_desk.dataops.backfill import (
    create_backfill_job as create_backfill_job_impl,
)
from prediction_desk.dataops.backfill import (
    run_backfill_job as run_backfill_job_impl,
)
from prediction_desk.dataops.coverage import (
    compute_global_coverage,
    compute_market_coverage,
    compute_universe_coverage,
    compute_venue_coverage,
)
from prediction_desk.dataops.enums import CoverageScopeType
from prediction_desk.dataops.gaps import detect_data_gaps
from prediction_desk.dataops.models import (
    BackfillJob,
    BackfillJobResult,
    BackfillSegment,
    CollectionPlan,
    CollectionRun,
    CollectionRunResult,
    DataCoverageReport,
    DataGap,
    DataRetentionPolicy,
    MarketUniverseDefinition,
    MarketUniverseMember,
)
from prediction_desk.dataops.orchestrator import (
    DataOpsCollectionError,
)
from prediction_desk.dataops.orchestrator import (
    run_collection_once as run_collection_once_impl,
)
from prediction_desk.dataops.plans import create_default_collection_plans_if_missing
from prediction_desk.dataops.universe import (
    build_market_universe,
    create_default_universes_if_missing,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository


class DataOpsServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class DataOpsService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def setup_default_dataops_objects(
        self,
    ) -> dict[str, list[MarketUniverseDefinition] | list[CollectionPlan]]:
        return {
            "universes": create_default_universes_if_missing(repo=self.repo),
            "collection_plans": create_default_collection_plans_if_missing(repo=self.repo),
        }

    def run_collection_once(
        self,
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
    ) -> CollectionRunResult:
        try:
            return run_collection_once_impl(
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
                repo=self.repo,
            )
        except DataOpsCollectionError as exc:
            raise DataOpsServiceError(exc.code, exc.message) from exc

    def create_backfill_job(
        self,
        *,
        venue_name: str,
        endpoint_types: list[str],
        start_time: datetime,
        end_time: datetime,
        market_ids: list[str] | None = None,
        job_name: str | None = None,
        interval_seconds: int | None = None,
        allow_network: bool = False,
        max_segments: int = 1000,
        metadata: dict[str, Any] | None = None,
    ) -> BackfillJob:
        try:
            return create_backfill_job_impl(
                venue_name=venue_name,
                endpoint_types=endpoint_types,
                start_time=start_time,
                end_time=end_time,
                market_ids=market_ids,
                job_name=job_name,
                interval_seconds=interval_seconds,
                allow_network=allow_network,
                max_segments=max_segments,
                metadata=metadata,
                repo=self.repo,
            )
        except DataOpsBackfillError as exc:
            raise DataOpsServiceError(exc.code, exc.message) from exc

    def run_backfill_job(self, job_id: str, *, force: bool = False) -> BackfillJobResult:
        try:
            return run_backfill_job_impl(job_id, force=force, repo=self.repo)
        except DataOpsBackfillError as exc:
            raise DataOpsServiceError(exc.code, exc.message) from exc

    def compute_coverage_report(
        self,
        *,
        scope_type: CoverageScopeType,
        asof_timestamp: datetime | None = None,
        universe_id: str | None = None,
        market_id: str | None = None,
        venue_name: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DataCoverageReport:
        asof = asof_timestamp or datetime.now(tz=UTC)
        if scope_type == CoverageScopeType.MARKET:
            return compute_market_coverage(
                market_id or "",
                asof,
                start_time=start_time,
                end_time=end_time,
                repo=self.repo,
            )
        if scope_type == CoverageScopeType.UNIVERSE:
            return compute_universe_coverage(
                universe_id or "",
                asof,
                start_time=start_time,
                end_time=end_time,
                repo=self.repo,
            )
        if scope_type == CoverageScopeType.VENUE:
            return compute_venue_coverage(
                venue_name or "",
                asof,
                start_time=start_time,
                end_time=end_time,
                repo=self.repo,
            )
        return compute_global_coverage(
            asof,
            start_time=start_time,
            end_time=end_time,
            repo=self.repo,
        )

    def detect_gaps(
        self,
        *,
        scope_type: CoverageScopeType,
        asof_timestamp: datetime | None = None,
        universe_id: str | None = None,
        market_id: str | None = None,
        venue_name: str | None = None,
        expected_cadence_seconds: int | None = None,
        coverage_report: DataCoverageReport | None = None,
    ) -> list[DataGap]:
        return detect_data_gaps(
            scope_type,
            asof_timestamp or datetime.now(tz=UTC),
            universe_id=universe_id,
            market_id=market_id,
            venue_name=venue_name,
            expected_cadence_seconds=expected_cadence_seconds,
            coverage_report=coverage_report,
            repo=self.repo,
        )

    def build_universe(
        self,
        universe_id: str,
        asof_timestamp: datetime,
        *,
        force: bool = False,
    ) -> list[MarketUniverseMember]:
        try:
            return build_market_universe(
                universe_id,
                asof_timestamp,
                force=force,
                repo=self.repo,
            )
        except ValueError as exc:
            raise DataOpsServiceError(str(exc)) from exc

    def list_collection_runs(self, *, limit: int = 500, offset: int = 0) -> list[CollectionRun]:
        return self.repo.list_collection_runs(limit=limit, offset=offset)

    def get_collection_run(self, collection_run_id: str) -> CollectionRun:
        run = self.repo.get_collection_run(collection_run_id)
        if run is None:
            raise DataOpsServiceError("collection_run_not_found")
        return run

    def list_backfill_jobs(self, *, limit: int = 500, offset: int = 0) -> list[BackfillJob]:
        return self.repo.list_backfill_jobs(limit=limit, offset=offset)

    def get_backfill_job(self, backfill_job_id: str) -> BackfillJob:
        job = self.repo.get_backfill_job(backfill_job_id)
        if job is None:
            raise DataOpsServiceError("backfill_job_not_found")
        return job

    def list_backfill_segments(
        self,
        *,
        backfill_job_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[BackfillSegment]:
        return self.repo.list_backfill_segments(
            backfill_job_id=backfill_job_id,
            limit=limit,
            offset=offset,
        )

    def list_coverage_reports(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DataCoverageReport]:
        return self.repo.list_data_coverage_reports(limit=limit, offset=offset)

    def list_data_gaps(self, *, limit: int = 500, offset: int = 0) -> list[DataGap]:
        return self.repo.list_data_gaps(limit=limit, offset=offset)

    def list_market_universes(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketUniverseDefinition]:
        return self.repo.list_market_universe_definitions(limit=limit, offset=offset)

    def list_universe_members(
        self,
        universe_id: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketUniverseMember]:
        return self.repo.list_market_universe_members(
            universe_id=universe_id,
            limit=limit,
            offset=offset,
        )

    def list_collection_plans(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CollectionPlan]:
        return self.repo.list_collection_plans(limit=limit, offset=offset)

    def list_data_retention_policies(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DataRetentionPolicy]:
        return self.repo.list_data_retention_policies(limit=limit, offset=offset)

