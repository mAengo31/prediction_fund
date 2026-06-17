"""Run-once scanner for cross-venue divergence assessments."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.divergence.aggregation import rate
from prediction_desk.divergence.enums import (
    DivergenceRunStatus,
    DivergenceStatus,
)
from prediction_desk.divergence.models import (
    DIVERGENCE_RUNNER_VERSION,
    CrossVenueDivergenceAnalysis,
    CrossVenueDivergenceRun,
    CrossVenueDivergenceRunConfig,
    CrossVenueDivergenceRunResult,
    CrossVenueDivergenceRunSummary,
)
from prediction_desk.divergence.service import DivergenceService
from prediction_desk.equivalence.enums import ComparisonPermission
from prediction_desk.equivalence.models import MarketEquivalenceAssessment
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


class DivergenceRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_divergence_scan(
    config: CrossVenueDivergenceRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> CrossVenueDivergenceRunResult:
    if repo is not None:
        return _run_divergence_scan(config, repo)
    with session_scope(database_url) as session:
        return _run_divergence_scan(config, PredictionMarketRepository(session))


def summarize_divergence_run(
    divergence_run_id: str,
    analyses: list[CrossVenueDivergenceAnalysis],
) -> CrossVenueDivergenceRunSummary:
    assessments = [analysis.assessment for analysis in analyses]
    signals = [signal for analysis in analyses for signal in analysis.signals]
    status_counts = Counter(assessment.status.value for assessment in assessments)
    severity_counts = Counter(assessment.severity.value for assessment in assessments)
    action_counts = Counter(assessment.action_hint.value for assessment in assessments)
    score_fields = (
        "overall_divergence_score",
        "price_divergence_score",
        "spread_adjusted_score",
        "persistence_score",
        "stale_side_score",
        "low_liquidity_score",
        "low_data_quality_score",
        "integrity_context_score",
        "equivalence_context_score",
    )
    totals: dict[str, int] = defaultdict(int)
    markets: set[str] = set()
    for assessment in assessments:
        markets.add(assessment.left_market_id)
        markets.add(assessment.right_market_id)
        for field in score_fields:
            totals[field] += int(getattr(assessment, field))
    total = len(assessments)
    averages = {
        field: Decimal(totals[field]) / Decimal(total) if total else Decimal("0")
        for field in score_fields
    }
    return CrossVenueDivergenceRunSummary(
        summary_id=f"divergence_summary_{uuid4().hex[:24]}",
        divergence_run_id=divergence_run_id,
        created_at=datetime.now(tz=UTC),
        total_snapshots=len(analyses),
        total_signals=len(signals),
        total_assessments=total,
        status_counts=dict(sorted(status_counts.items())),
        severity_counts=dict(sorted(severity_counts.items())),
        action_hint_counts=dict(sorted(action_counts.items())),
        average_scores=averages,
        watch_rate=rate(status_counts[DivergenceStatus.WATCH.value], total),
        material_divergence_rate=rate(
            status_counts[DivergenceStatus.MATERIAL_DIVERGENCE.value],
            total,
        ),
        needs_review_rate=rate(status_counts[DivergenceStatus.NEEDS_REVIEW.value], total),
        do_not_compare_rate=rate(
            status_counts[DivergenceStatus.DO_NOT_COMPARE.value],
            total,
        ),
        markets_compared=len(markets),
        metadata={"runner_version": DIVERGENCE_RUNNER_VERSION},
    )


def _run_divergence_scan(
    config: CrossVenueDivergenceRunConfig,
    repo: PredictionMarketRepository,
) -> CrossVenueDivergenceRunResult:
    now = datetime.now(tz=UTC)
    run = CrossVenueDivergenceRun(
        divergence_run_id=f"divergence_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=DivergenceRunStatus.RUNNING,
        asof_timestamp=config.asof_timestamp,
        equivalence_assessment_ids=list(config.equivalence_assessment_ids or []),
        market_ids=list(config.market_ids or []),
        max_pairs=config.max_pairs,
        config={
            **config.model_dump(mode="json"),
            "runner_version": DIVERGENCE_RUNNER_VERSION,
        },
        metadata=dict(config.metadata),
    )
    repo.save_divergence_run(run)
    service = DivergenceService(repo)
    analyses: list[CrossVenueDivergenceAnalysis] = []
    errors: list[dict[str, Any]] = []
    try:
        assessments = _select_assessments(repo, config)
        if len(assessments) > config.max_pairs:
            raise DivergenceRunError("too_many_divergence_pairs")
        for assessment in assessments:
            try:
                analyses.append(
                    service.analyze_equivalence_divergence(
                        assessment.equivalence_assessment_id,
                        asof_timestamp=config.asof_timestamp,
                        force=config.force,
                        config=config.config,
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive run bookkeeping
                errors.append(
                    {
                        "equivalence_assessment_id": assessment.equivalence_assessment_id,
                        "error_code": exc.__class__.__name__,
                        "error_message": str(exc),
                    }
                )
        summary = summarize_divergence_run(run.divergence_run_id, analyses)
        repo.save_divergence_run_summary(summary)
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": DivergenceRunStatus.COMPLETED
                if not errors
                else DivergenceRunStatus.PARTIAL,
                "equivalence_assessment_ids": [
                    assessment.equivalence_assessment_id for assessment in assessments
                ],
                "snapshots_created": len(analyses),
                "signals_created": sum(len(analysis.signals) for analysis in analyses),
                "assessments_created": len(analyses),
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_divergence_run(completed)
        return CrossVenueDivergenceRunResult(
            run=completed,
            analyses=analyses,
            summary=summary,
        )
    except Exception:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": DivergenceRunStatus.FAILED,
                "errors_count": max(1, len(errors)),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_divergence_run(failed)
        raise


def _select_assessments(
    repo: PredictionMarketRepository,
    config: CrossVenueDivergenceRunConfig,
) -> list[MarketEquivalenceAssessment]:
    if config.equivalence_assessment_ids:
        assessments = [
            assessment
            for assessment_id in config.equivalence_assessment_ids
            if (assessment := repo.get_market_equivalence_assessment(assessment_id))
            is not None
            and _as_utc(assessment.available_at) <= _as_utc(config.asof_timestamp)
        ]
        return assessments[: config.max_pairs]
    if config.market_ids:
        by_id: dict[str, MarketEquivalenceAssessment] = {}
        for market_id in config.market_ids:
            for assessment in repo.list_latest_equivalence_assessments_for_market_asof(
                market_id,
                config.asof_timestamp,
                limit=config.max_pairs,
            ):
                by_id[assessment.equivalence_assessment_id] = assessment
        return [by_id[key] for key in sorted(by_id)][: config.max_pairs]
    allowed = {
        ComparisonPermission.COMPARABLE,
        ComparisonPermission.COMPARABLE_WITH_HAIRCUT,
        ComparisonPermission.MANUAL_REVIEW,
    }
    assessments = [
        assessment
        for assessment in repo.list_equivalence_assessments(limit=config.max_pairs)
        if _as_utc(assessment.available_at) <= _as_utc(config.asof_timestamp)
        and assessment.comparison_permission in allowed
    ]
    return assessments[: config.max_pairs]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
