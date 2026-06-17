"""Run-once integrity scan runner."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from prediction_desk.integrity.enums import IntegrityActionHint, IntegrityRunStatus
from prediction_desk.integrity.models import (
    RUNNER_VERSION,
    IntegrityAssessment,
    IntegrityRun,
    IntegrityRunConfig,
    IntegrityRunResult,
    IntegrityRunSummary,
)
from prediction_desk.integrity.service import IntegrityService
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


class IntegrityRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_integrity_scan(
    config: IntegrityRunConfig,
    repo: PredictionMarketRepository | None = None,
    *,
    database_url: str | None = None,
) -> IntegrityRunResult:
    if repo is not None:
        return _run_integrity_scan(config, repo)
    with session_scope(database_url) as session:
        return _run_integrity_scan(config, PredictionMarketRepository(session))


def generate_integrity_timestamps(config: IntegrityRunConfig) -> list[datetime]:
    if config.asof_timestamp is not None:
        return [config.asof_timestamp]
    if config.start_time is None or config.end_time is None or config.interval_seconds is None:
        raise IntegrityRunError("invalid_integrity_scan")
    timestamps: list[datetime] = []
    current = config.start_time
    interval = timedelta(seconds=config.interval_seconds)
    while current <= config.end_time:
        timestamps.append(current)
        current += interval
    return timestamps


def _run_integrity_scan(
    config: IntegrityRunConfig,
    repo: PredictionMarketRepository,
) -> IntegrityRunResult:
    timestamps = generate_integrity_timestamps(config)
    markets = (
        [repo.get_market(market_id) for market_id in config.market_ids]
        if config.market_ids
        else repo.list_markets(limit=500)
    )
    market_ids = [market.market_id for market in markets if market is not None]
    total_steps = len(timestamps) * len(market_ids)
    if total_steps > config.max_steps:
        raise IntegrityRunError(
            "too_many_integrity_steps",
            f"Integrity scan would create {total_steps} assessments.",
        )

    now = datetime.now(tz=UTC)
    run = IntegrityRun(
        integrity_run_id=f"integrity_run_{uuid4().hex[:24]}",
        name=config.name,
        created_at=now,
        started_at=now,
        completed_at=None,
        status=IntegrityRunStatus.RUNNING,
        start_time=config.start_time,
        end_time=config.end_time,
        interval_seconds=config.interval_seconds,
        asof_timestamp=config.asof_timestamp,
        market_ids=market_ids,
        max_steps=config.max_steps,
        config={
            **config.model_dump(mode="json"),
            "runner_version": RUNNER_VERSION,
            "timestamp_window": "inclusive_start_inclusive_end",
        },
        metadata=dict(config.metadata),
    )
    repo.save_integrity_run(run)

    service = IntegrityService(repo)
    assessments: list[IntegrityAssessment] = []
    errors: list[dict[str, Any]] = []
    signals_created = 0
    try:
        for asof_timestamp in timestamps:
            for market_id in market_ids:
                try:
                    before_signals = len(
                        repo.list_integrity_signals(market_id=market_id, limit=10000)
                    )
                    analysis = service.analyze_market_integrity_details(
                        market_id,
                        asof_timestamp,
                        config=config.thresholds,
                        force=config.force,
                    )
                    after_signals = len(
                        repo.list_integrity_signals(market_id=market_id, limit=10000)
                    )
                    signals_created += max(0, after_signals - before_signals)
                    assessments.append(analysis.assessment)
                except Exception as exc:  # pragma: no cover - defensive run bookkeeping
                    errors.append(
                        {
                            "market_id": market_id,
                            "asof_timestamp": asof_timestamp.isoformat(),
                            "error_code": exc.__class__.__name__,
                            "error_message": str(exc),
                        }
                    )
        status = IntegrityRunStatus.COMPLETED if not errors else IntegrityRunStatus.PARTIAL
        summary = summarize_integrity_run(run.integrity_run_id, assessments)
        repo.save_integrity_run_summary(summary)
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": status,
                "assessments_created": len(assessments),
                "signals_created": signals_created,
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_integrity_run(completed)
        return IntegrityRunResult(run=completed, assessments=assessments, summary=summary)
    except Exception:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": IntegrityRunStatus.FAILED,
                "errors_count": max(1, len(errors)),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_integrity_run(failed)
        raise


def summarize_integrity_run(
    integrity_run_id: str,
    assessments: list[IntegrityAssessment],
) -> IntegrityRunSummary:
    total = len(assessments)
    severity_counts = Counter(assessment.severity.value for assessment in assessments)
    action_hint_counts = Counter(assessment.action_hint.value for assessment in assessments)
    category_counts: Counter[str] = Counter()
    score_totals: dict[str, int] = defaultdict(int)
    score_fields = (
        "overall_risk_score",
        "price_anomaly_score",
        "liquidity_anomaly_score",
        "freshness_risk_score",
        "orderbook_structure_score",
        "rule_change_risk_score",
        "rule_price_coupling_score",
        "data_quality_risk_score",
        "manipulation_proxy_score",
    )
    for assessment in assessments:
        if assessment.price_anomaly_score:
            category_counts["PRICE_ANOMALY"] += 1
        if assessment.liquidity_anomaly_score:
            category_counts["LIQUIDITY_ANOMALY"] += 1
        if assessment.freshness_risk_score:
            category_counts["DATA_FRESHNESS"] += 1
        if assessment.orderbook_structure_score:
            category_counts["ORDERBOOK_STRUCTURE"] += 1
        if assessment.rule_change_risk_score:
            category_counts["RULE_CHANGE"] += 1
        if assessment.rule_price_coupling_score:
            category_counts["RULE_PRICE_COUPLING"] += 1
        if assessment.data_quality_risk_score:
            category_counts["DATA_QUALITY"] += 1
        if assessment.manipulation_proxy_score:
            category_counts["MANIPULATION_PROXY"] += 1
        for field in score_fields:
            score_totals[field] += int(getattr(assessment, field))

    average_scores = {
        field: (Decimal(score_totals[field]) / Decimal(total)) if total else Decimal("0")
        for field in score_fields
    }
    return IntegrityRunSummary(
        summary_id=f"integrity_summary_{uuid4().hex[:24]}",
        integrity_run_id=integrity_run_id,
        created_at=datetime.now(tz=UTC),
        total_assessments=total,
        total_signals=sum(len(assessment.signal_ids) for assessment in assessments),
        severity_counts=dict(sorted(severity_counts.items())),
        category_counts=dict(sorted(category_counts.items())),
        action_hint_counts=dict(sorted(action_hint_counts.items())),
        average_scores=average_scores,
        no_trade_rate=_rate(action_hint_counts[IntegrityActionHint.NO_TRADE.value], total),
        manual_review_rate=_rate(
            action_hint_counts[IntegrityActionHint.MANUAL_REVIEW.value],
            total,
        ),
        passive_only_rate=_rate(
            action_hint_counts[IntegrityActionHint.PASSIVE_ONLY.value],
            total,
        ),
        allow_smaller_size_rate=_rate(
            action_hint_counts[IntegrityActionHint.ALLOW_SMALLER_SIZE.value],
            total,
        ),
        markets_scanned=len({assessment.market_id for assessment in assessments}),
        metadata={"runner_version": RUNNER_VERSION},
    )


def _rate(count: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0")
    return Decimal(count) / Decimal(total)
