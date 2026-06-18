"""Review queue generation for the desk workbench."""

from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.workbench.enums import ReviewStatus
from prediction_desk.workbench.evidence import latest_data_gaps_for_market
from prediction_desk.workbench.models import (
    MarketReviewQueueItem,
    workbench_object_id,
)
from prediction_desk.workbench.scoring import (
    priority_bucket,
    recommended_action,
    score_review_context_details,
)


def build_market_review_queue(
    asof_timestamp: datetime,
    market_ids: list[str] | None = None,
    queue_name: str = "default_review_queue",
    limit: int = 500,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> list[MarketReviewQueueItem]:
    if repo is not None:
        return _build_market_review_queue(
            repo,
            asof_timestamp,
            market_ids=market_ids,
            queue_name=queue_name,
            limit=limit,
            force=force,
        )
    with session_scope() as session:
        return _build_market_review_queue(
            PredictionMarketRepository(session),
            asof_timestamp,
            market_ids=market_ids,
            queue_name=queue_name,
            limit=limit,
            force=force,
        )


def _build_market_review_queue(
    repo: PredictionMarketRepository,
    asof_timestamp: datetime,
    *,
    market_ids: list[str] | None,
    queue_name: str,
    limit: int,
    force: bool,
) -> list[MarketReviewQueueItem]:
    markets = _resolve_markets(repo, market_ids, limit)
    items: list[MarketReviewQueueItem] = []
    for market_id in markets:
        quality = repo.get_latest_quality_report_asof(market_id, asof_timestamp)
        integrity = repo.get_latest_integrity_assessment_asof(market_id, asof_timestamp)
        equivalences = repo.list_latest_equivalence_assessments_for_market_asof(
            market_id,
            asof_timestamp,
            limit=25,
        )
        divergences = repo.list_latest_divergence_assessments_for_market_asof(
            market_id,
            asof_timestamp,
            limit=25,
        )
        pretrade = repo.get_latest_pretrade_decision_asof(market_id, asof_timestamp)
        research_signals = repo.list_research_signals(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            limit=25,
        )
        paper_orders = [
            order
            for order in repo.list_paper_orders(market_id=market_id, limit=25)
            if _as_utc(order.available_at) <= _as_utc(asof_timestamp)
        ]
        scenario = repo.get_latest_scenario_feature_asof(market_id, asof_timestamp)
        gaps = latest_data_gaps_for_market(repo, market_id, asof_timestamp, limit=100)
        score_details = score_review_context_details(
            quality_report=quality,
            integrity_assessment=integrity,
            divergence_assessments=divergences,
            pretrade_decision=pretrade,
            research_signals=research_signals,
            data_gaps=gaps,
            scenario_feature=scenario,
        )
        score = score_details.priority_score
        reason_codes = score_details.reason_codes
        evidence_ref_ids = _dedupe(
            [
                quality.quality_report_id if quality else None,
                integrity.integrity_assessment_id if integrity else None,
                pretrade.pretrade_decision_id if pretrade else None,
                *[item.equivalence_assessment_id for item in equivalences],
                *[item.divergence_assessment_id for item in divergences],
                *[item.research_signal_id for item in research_signals],
                *[item.paper_order_id for item in paper_orders],
                *[gap.data_gap_id for gap in gaps],
            ]
        )
        queue_item_id = workbench_object_id(
            "queue_item",
            {
                "version": "market_review_queue_item_v1",
                "market_id": market_id,
                "asof_timestamp": asof_timestamp,
                "queue_name": queue_name,
                "reason_codes": reason_codes,
                "evidence_ref_ids": evidence_ref_ids,
            },
        )
        existing = repo.get_market_review_queue_item(queue_item_id)
        if existing is not None and not force:
            items.append(existing)
            continue
        item = MarketReviewQueueItem(
            queue_item_id=queue_item_id,
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            generated_at=datetime.now(tz=UTC),
            available_at=asof_timestamp,
            queue_name=queue_name,
            priority_score=score,
            priority_bucket=priority_bucket(score),
            review_status=ReviewStatus.NEW,
            primary_reason_code=reason_codes[0],
            reason_codes=reason_codes,
            evidence_ref_ids=evidence_ref_ids,
            latest_quality_report_id=quality.quality_report_id if quality else None,
            latest_integrity_assessment_id=(
                integrity.integrity_assessment_id if integrity else None
            ),
            latest_equivalence_assessment_ids=[
                item.equivalence_assessment_id for item in equivalences
            ],
            latest_divergence_assessment_ids=[
                item.divergence_assessment_id for item in divergences
            ],
            latest_pretrade_decision_id=(
                pretrade.pretrade_decision_id if pretrade else None
            ),
            latest_research_signal_ids=[
                item.research_signal_id for item in research_signals
            ],
            latest_paper_order_ids=[item.paper_order_id for item in paper_orders],
            metadata={
                "workbench_version": "desk_workbench_v1",
                "recommended_next_review_action": recommended_action(reason_codes).value,
                "score_components": score_details.score_components,
                "score_explanation": score_details.score_explanation,
                "hard_escalators": score_details.hard_escalators,
                "soft_escalators": score_details.soft_escalators,
                "dampeners": score_details.dampeners,
            },
        )
        items.append(repo.save_market_review_queue_item(item))
    return sorted(items, key=lambda item: (-item.priority_score, item.market_id))[:limit]


def _resolve_markets(
    repo: PredictionMarketRepository,
    market_ids: list[str] | None,
    limit: int,
) -> list[str]:
    if market_ids:
        return sorted(dict.fromkeys(market_ids))[:limit]
    return [market.market_id for market in repo.list_markets(limit=limit)]


def _dedupe(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
