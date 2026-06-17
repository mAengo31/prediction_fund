"""Run-once cross-venue equivalence scanner."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.equivalence.enums import ComparisonPermission, EquivalenceRunStatus
from prediction_desk.equivalence.models import (
    EQUIVALENCE_RUNNER_VERSION,
    EquivalenceRun,
    EquivalenceRunConfig,
    EquivalenceRunResult,
    EquivalenceRunSummary,
    MarketEquivalenceAssessment,
)
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


class EquivalenceRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_equivalence_scan(
    config: EquivalenceRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> EquivalenceRunResult:
    if repo is not None:
        return _run_equivalence_scan(config, repo)
    with session_scope(database_url) as session:
        return _run_equivalence_scan(config, PredictionMarketRepository(session))


def summarize_equivalence_run(
    equivalence_run_id: str,
    assessments: list[MarketEquivalenceAssessment],
    *,
    total_candidates: int,
    total_classes: int,
) -> EquivalenceRunSummary:
    total = len(assessments)
    status_counts = Counter(assessment.status.value for assessment in assessments)
    permission_counts = Counter(
        assessment.comparison_permission.value for assessment in assessments
    )
    score_fields = (
        "overall_score",
        "confidence_score",
        "title_similarity_score",
        "event_identity_score",
        "outcome_structure_score",
        "outcome_mapping_score",
        "predicate_similarity_score",
        "resolution_source_score",
        "settlement_authority_score",
        "temporal_alignment_score",
        "threshold_alignment_score",
        "timezone_alignment_score",
        "ambiguity_compatibility_score",
        "venue_rule_compatibility_score",
    )
    score_totals: dict[str, int] = defaultdict(int)
    markets: set[str] = set()
    for assessment in assessments:
        markets.add(assessment.left_market_id)
        markets.add(assessment.right_market_id)
        for field in score_fields:
            score_totals[field] += int(getattr(assessment, field))
    average_scores = {
        field: Decimal(score_totals[field]) / Decimal(total) if total else Decimal("0")
        for field in score_fields
    }
    comparable_count = (
        permission_counts[ComparisonPermission.COMPARABLE.value]
        + permission_counts[ComparisonPermission.COMPARABLE_WITH_HAIRCUT.value]
    )
    return EquivalenceRunSummary(
        summary_id=f"equivalence_summary_{uuid4().hex[:24]}",
        equivalence_run_id=equivalence_run_id,
        created_at=datetime.now(tz=UTC),
        total_candidates=total_candidates,
        total_assessments=total,
        total_classes=total_classes,
        status_counts=dict(sorted(status_counts.items())),
        permission_counts=dict(sorted(permission_counts.items())),
        average_scores=average_scores,
        comparable_rate=_rate(comparable_count, total),
        manual_review_rate=_rate(
            permission_counts[ComparisonPermission.MANUAL_REVIEW.value],
            total,
        ),
        do_not_compare_rate=_rate(
            permission_counts[ComparisonPermission.DO_NOT_COMPARE.value],
            total,
        ),
        markets_compared=len(markets),
        metadata={"runner_version": EQUIVALENCE_RUNNER_VERSION},
    )


def _run_equivalence_scan(
    config: EquivalenceRunConfig,
    repo: PredictionMarketRepository,
) -> EquivalenceRunResult:
    now = datetime.now(tz=UTC)
    run = EquivalenceRun(
        equivalence_run_id=f"equivalence_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=EquivalenceRunStatus.RUNNING,
        asof_timestamp=config.asof_timestamp,
        market_ids=list(config.market_ids or []),
        venue_names=list(config.venue_names or []),
        max_pairs=config.max_pairs,
        min_candidate_score=config.min_candidate_score,
        config={
            **config.model_dump(mode="json"),
            "runner_version": EQUIVALENCE_RUNNER_VERSION,
        },
        metadata=dict(config.metadata),
    )
    repo.save_equivalence_run(run)

    service = EquivalenceService(repo)
    assessments: list[MarketEquivalenceAssessment] = []
    errors: list[dict[str, Any]] = []
    classes = []
    try:
        candidates = service.generate_candidates(
            config.asof_timestamp,
            market_ids=config.market_ids,
            venue_names=config.venue_names,
            min_candidate_score=config.min_candidate_score,
            max_pairs=config.max_pairs,
            force=config.force,
        )
        if len(candidates) > config.max_pairs:
            raise EquivalenceRunError("too_many_equivalence_pairs")
        for candidate in candidates:
            try:
                response = service.assess_market_equivalence(
                    candidate.left_market_id,
                    candidate.right_market_id,
                    candidate.asof_timestamp,
                    force=config.force,
                )
                assessments.append(response.assessment)
            except Exception as exc:  # pragma: no cover - defensive run bookkeeping
                errors.append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "left_market_id": candidate.left_market_id,
                        "right_market_id": candidate.right_market_id,
                        "error_code": exc.__class__.__name__,
                        "error_message": str(exc),
                    }
                )
        if config.build_classes:
            classes = service.build_equivalence_classes(
                config.asof_timestamp,
                market_ids=config.market_ids,
                force=config.force,
            )
        status = EquivalenceRunStatus.COMPLETED if not errors else EquivalenceRunStatus.PARTIAL
        summary = summarize_equivalence_run(
            run.equivalence_run_id,
            assessments,
            total_candidates=len(candidates),
            total_classes=len(classes),
        )
        repo.save_equivalence_run_summary(summary)
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": status,
                "candidates_created": len(candidates),
                "assessments_created": len(assessments),
                "classes_created": len(classes),
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_equivalence_run(completed)
        return EquivalenceRunResult(
            run=completed,
            candidates=candidates,
            assessments=assessments,
            classes=classes,
            summary=summary,
        )
    except Exception:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": EquivalenceRunStatus.FAILED,
                "errors_count": max(1, len(errors)),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_equivalence_run(failed)
        raise


def _rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)
