"""Historical read-only backfill planning and execution."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from prediction_desk.dataops.enums import BackfillJobStatus, BackfillSegmentStatus
from prediction_desk.dataops.models import (
    BackfillJob,
    BackfillJobResult,
    BackfillSegment,
    dataops_object_id,
)
from prediction_desk.ingestion.adapters.kalshi import KalshiReadOnlyAdapter
from prediction_desk.ingestion.adapters.polymarket import PolymarketReadOnlyAdapter
from prediction_desk.ingestion.enums import VenueEndpointType
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


class DataOpsBackfillError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def create_backfill_job(
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
    repo: PredictionMarketRepository | None = None,
) -> BackfillJob:
    if repo is not None:
        return _create_backfill_job(
            repo,
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
        )
    with session_scope() as session:
        return _create_backfill_job(
            PredictionMarketRepository(session),
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
        )


def plan_backfill_segments(
    job: BackfillJob,
    *,
    repo: PredictionMarketRepository,
) -> list[BackfillSegment]:
    segments: list[BackfillSegment] = []
    windows = _windows(job.start_time, job.end_time, job.interval_seconds)
    market_ids: list[str | None] = list(job.market_ids) if job.market_ids else [None]
    for market_id in market_ids:
        for endpoint_type in job.endpoint_types:
            for start, end in windows:
                if len(segments) >= job.max_segments:
                    return segments
                supported, reason = _supported(job.venue_name, endpoint_type)
                segment = BackfillSegment(
                    backfill_segment_id=dataops_object_id(
                        "backfill_segment",
                        {
                            "job": job.backfill_job_id,
                            "venue": job.venue_name,
                            "market_id": market_id,
                            "endpoint_type": endpoint_type,
                            "start": start,
                            "end": end,
                        },
                    ),
                    backfill_job_id=job.backfill_job_id,
                    venue_name=job.venue_name,
                    market_id=market_id,
                    endpoint_type=endpoint_type,
                    segment_start_time=start,
                    segment_end_time=end,
                    status=(
                        BackfillSegmentStatus.PENDING
                        if supported
                        else BackfillSegmentStatus.SKIPPED_UNSUPPORTED
                    ),
                    supported=supported,
                    unsupported_reason=reason,
                    metadata={"planner_version": "backfill_planner_v1"},
                )
                segments.append(repo.save_backfill_segment(segment))
    return segments


def run_backfill_job(
    job_id: str,
    *,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> BackfillJobResult:
    if repo is not None:
        return _run_backfill_job(repo, job_id, force=force)
    with session_scope() as session:
        return _run_backfill_job(PredictionMarketRepository(session), job_id, force=force)


def _create_backfill_job(
    repo: PredictionMarketRepository,
    *,
    venue_name: str,
    endpoint_types: list[str],
    start_time: datetime,
    end_time: datetime,
    market_ids: list[str] | None,
    job_name: str | None,
    interval_seconds: int | None,
    allow_network: bool,
    max_segments: int,
    metadata: dict[str, Any] | None,
) -> BackfillJob:
    if end_time < start_time:
        raise DataOpsBackfillError("invalid_backfill_time_range")
    if not endpoint_types:
        raise DataOpsBackfillError("missing_backfill_endpoint_types")
    job = BackfillJob(
        backfill_job_id=dataops_object_id(
            "backfill_job",
            {
                "created_at": datetime.now(tz=UTC),
                "venue_name": venue_name,
                "market_ids": sorted(market_ids or []),
                "endpoint_types": sorted(endpoint_types),
                "start_time": start_time,
                "end_time": end_time,
            },
        ),
        job_name=job_name,
        created_at=datetime.now(tz=UTC),
        status=BackfillJobStatus.PENDING,
        venue_name=venue_name,
        market_ids=sorted(set(market_ids or [])),
        endpoint_types=sorted(set(endpoint_types)),
        start_time=start_time,
        end_time=end_time,
        interval_seconds=interval_seconds,
        allow_network=allow_network,
        max_segments=max_segments,
        metadata=dict(metadata or {}),
    )
    saved = repo.save_backfill_job(job)
    segments = plan_backfill_segments(saved, repo=repo)
    saved = saved.model_copy(update={"segments_created": len(segments)})
    return repo.update_backfill_job(saved)


def _run_backfill_job(
    repo: PredictionMarketRepository,
    job_id: str,
    *,
    force: bool,
) -> BackfillJobResult:
    job = repo.get_backfill_job(job_id)
    if job is None:
        raise DataOpsBackfillError("backfill_job_not_found")
    if not job.allow_network and _requires_network(job):
        raise DataOpsBackfillError("public_network_disabled")
    started = job.model_copy(
        update={"started_at": datetime.now(tz=UTC), "status": BackfillJobStatus.RUNNING}
    )
    repo.update_backfill_job(started)
    segments = repo.list_backfill_segments(backfill_job_id=job.backfill_job_id, limit=10000)
    if not segments:
        segments = plan_backfill_segments(started, repo=repo)
    completed_segments: list[BackfillSegment] = []
    failed = 0
    completed = 0
    for segment in segments:
        if segment.status == BackfillSegmentStatus.SKIPPED_UNSUPPORTED:
            completed_segments.append(segment)
            continue
        try:
            completed_segment = _run_segment(repo, started, segment, force=force)
            completed += 1
        except Exception as exc:
            failed += 1
            completed_segment = segment.model_copy(
                update={
                    "status": BackfillSegmentStatus.FAILED,
                    "errors_count": segment.errors_count + 1,
                    "metadata": {**segment.metadata, "error": str(exc)},
                }
            )
            repo.update_backfill_segment(completed_segment)
        completed_segments.append(completed_segment)
    final = started.model_copy(
        update={
            "completed_at": datetime.now(tz=UTC),
            "status": BackfillJobStatus.COMPLETED if failed == 0 else BackfillJobStatus.PARTIAL,
            "segments_completed": completed,
            "segments_failed": failed,
        }
    )
    repo.update_backfill_job(final)
    return BackfillJobResult(job=final, segments=completed_segments)


def _run_segment(
    repo: PredictionMarketRepository,
    job: BackfillJob,
    segment: BackfillSegment,
    *,
    force: bool,
) -> BackfillSegment:
    if segment.endpoint_type != VenueEndpointType.PRICE_HISTORY.value:
        skipped = segment.model_copy(
            update={
                "status": BackfillSegmentStatus.SKIPPED_UNSUPPORTED,
                "supported": False,
                "unsupported_reason": "unsupported_historical_endpoint",
            }
        )
        return repo.update_backfill_segment(skipped)
    if segment.market_id is None:
        skipped = segment.model_copy(
            update={
                "status": BackfillSegmentStatus.SKIPPED_UNSUPPORTED,
                "supported": False,
                "unsupported_reason": "market_id_required",
            }
        )
        return repo.update_backfill_segment(skipped)
    mapping = repo.get_mapping_by_canonical_market_id(segment.market_id)
    if mapping is None or mapping.external_market_id is None:
        skipped = segment.model_copy(
            update={
                "status": BackfillSegmentStatus.SKIPPED_UNSUPPORTED,
                "supported": False,
                "unsupported_reason": "venue_mapping_missing",
            }
        )
        return repo.update_backfill_segment(skipped)
    adapter = _adapter(job.venue_name)
    payload = adapter.fetch_price_history(
        mapping.external_market_id,
        allow_network=job.allow_network,
        captured_at=segment.segment_end_time,
    )
    saved_payload = repo.save_raw_venue_payload(payload)
    result = MarketDataService(repo).normalize_price_history_payload(
        saved_payload.payload_id,
        force=force,
    )
    updated = segment.model_copy(
        update={
            "status": BackfillSegmentStatus.COMPLETED,
            "payloads_archived": 1,
            "snapshots_created": result.price_snapshots_created,
            "metadata": {**segment.metadata, "payload_id": saved_payload.payload_id},
        }
    )
    return repo.update_backfill_segment(updated)


def _adapter(venue_name: str) -> KalshiReadOnlyAdapter | PolymarketReadOnlyAdapter:
    normalized = venue_name.casefold()
    if normalized == "kalshi":
        return KalshiReadOnlyAdapter()
    if normalized == "polymarket":
        return PolymarketReadOnlyAdapter()
    raise DataOpsBackfillError("unsupported_venue")


def _supported(venue_name: str, endpoint_type: str) -> tuple[bool, str | None]:
    if endpoint_type != VenueEndpointType.PRICE_HISTORY.value:
        return False, "unsupported_historical_endpoint"
    if venue_name.casefold() != "polymarket":
        return False, "unsupported_historical_endpoint"
    return True, None


def _requires_network(job: BackfillJob) -> bool:
    return job.allow_network


def _windows(
    start_time: datetime,
    end_time: datetime,
    interval_seconds: int | None,
) -> list[tuple[datetime, datetime]]:
    if interval_seconds is None:
        return [(start_time, end_time)]
    windows: list[tuple[datetime, datetime]] = []
    cursor = start_time
    delta = timedelta(seconds=interval_seconds)
    while cursor < end_time:
        nxt = min(cursor + delta, end_time)
        windows.append((cursor, nxt))
        cursor = nxt
    return windows or [(start_time, end_time)]
