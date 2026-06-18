"""Service layer for the desk decision workbench."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.workbench.cards import (
    build_cross_venue_comparison_card,
    build_market_decision_card,
)
from prediction_desk.workbench.enums import ReviewPriorityBucket, ReviewStatus, WorkbenchRunStatus
from prediction_desk.workbench.models import (
    CrossVenueComparisonCard,
    DeskReviewNote,
    DeskReviewNoteCreate,
    DeskWatchlist,
    MarketDecisionCard,
    MarketReviewQueueItem,
    WorkbenchQueueSummary,
    WorkbenchRun,
    WorkbenchRunConfig,
    WorkbenchRunResult,
    WorkbenchRunSummary,
    default_watchlists,
    workbench_object_id,
)
from prediction_desk.workbench.notes import create_desk_review_note
from prediction_desk.workbench.queues import build_market_review_queue
from prediction_desk.workbench.scoring import recommended_action


class WorkbenchServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class WorkbenchService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def create_default_watchlists_if_missing(self) -> list[DeskWatchlist]:
        saved: list[DeskWatchlist] = []
        for watchlist in default_watchlists(datetime.now(tz=UTC)):
            existing = self.repo.get_desk_watchlist(watchlist.watchlist_id)
            saved.append(
                existing
                if existing is not None
                else self.repo.save_desk_watchlist(watchlist)
            )
        return saved

    def list_watchlists(self, *, limit: int = 500, offset: int = 0) -> list[DeskWatchlist]:
        return self.repo.list_desk_watchlists(limit=limit, offset=offset)

    def build_queue(
        self,
        asof_timestamp: datetime,
        *,
        market_ids: list[str] | None = None,
        queue_name: str = "default_review_queue",
        limit: int = 500,
        force: bool = False,
    ) -> list[MarketReviewQueueItem]:
        return build_market_review_queue(
            asof_timestamp,
            market_ids=market_ids,
            queue_name=queue_name,
            limit=limit,
            force=force,
            repo=self.repo,
        )

    def build_decision_card(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        force: bool = False,
    ) -> MarketDecisionCard:
        try:
            return build_market_decision_card(
                market_id,
                asof_timestamp,
                force=force,
                repo=self.repo,
            )
        except ValueError as exc:
            raise WorkbenchServiceError(str(exc)) from exc

    def build_comparison_card(
        self,
        equivalence_assessment_id: str,
        asof_timestamp: datetime,
        *,
        force: bool = False,
    ) -> CrossVenueComparisonCard:
        try:
            return build_cross_venue_comparison_card(
                equivalence_assessment_id,
                asof_timestamp,
                force=force,
                repo=self.repo,
            )
        except ValueError as exc:
            raise WorkbenchServiceError(str(exc)) from exc

    def list_queue_items(
        self,
        *,
        market_id: str | None = None,
        queue_name: str | None = None,
        priority_bucket: ReviewPriorityBucket | str | None = None,
        review_status: ReviewStatus | str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketReviewQueueItem]:
        return self.repo.list_market_review_queue_items(
            market_id=market_id,
            queue_name=queue_name,
            priority_bucket=priority_bucket,
            review_status=review_status,
            limit=limit,
            offset=offset,
        )

    def list_latest_queue_items(
        self,
        *,
        market_id: str | None = None,
        queue_name: str | None = None,
        priority_bucket: ReviewPriorityBucket | str | None = None,
        review_status: ReviewStatus | str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketReviewQueueItem]:
        return self.repo.list_latest_market_review_queue_items(
            market_id=market_id,
            queue_name=queue_name,
            priority_bucket=priority_bucket,
            review_status=review_status,
            asof_timestamp=asof_timestamp,
            limit=limit,
            offset=offset,
        )

    def list_latest_queue_items_for_run(
        self,
        workbench_run_id: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketReviewQueueItem]:
        run = self.get_run(workbench_run_id)
        queue_name = str(run.metadata.get("queue_name", "default_review_queue"))
        run_market_ids = set(run.market_ids)
        items = self.list_latest_queue_items(
            queue_name=queue_name,
            asof_timestamp=run.asof_timestamp,
            limit=10000,
        )
        return [item for item in items if item.market_id in run_market_ids][
            offset : offset + limit
        ]

    def list_active_queue_view(
        self,
        *,
        market_id: str | None = None,
        queue_name: str | None = None,
        priority_bucket: ReviewPriorityBucket | str | None = None,
        review_status: ReviewStatus | str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketReviewQueueItem]:
        return self.list_latest_queue_items(
            market_id=market_id,
            queue_name=queue_name,
            priority_bucket=priority_bucket,
            review_status=review_status,
            asof_timestamp=asof_timestamp,
            limit=limit,
            offset=offset,
        )

    def summarize_queue(
        self,
        *,
        queue_name: str | None = None,
        latest_only: bool = True,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
    ) -> WorkbenchQueueSummary:
        items = (
            self.list_latest_queue_items(
                queue_name=queue_name,
                asof_timestamp=asof_timestamp,
                limit=limit,
            )
            if latest_only
            else self.list_queue_items(queue_name=queue_name, limit=limit)
        )
        generated_at = max((item.generated_at for item in items), default=None)
        item_asof = max((item.asof_timestamp for item in items), default=None)
        return WorkbenchQueueSummary(
            queue_name=queue_name,
            latest_only=latest_only,
            asof_timestamp=asof_timestamp or item_asof,
            generated_at=generated_at,
            total_items=len(items),
            priority_bucket_counts=dict(
                Counter(item.priority_bucket.value for item in items)
            ),
            review_action_counts=dict(
                Counter(_queue_review_action(item) for item in items)
            ),
            top_reason_codes=dict(
                Counter(reason for item in items for reason in item.reason_codes).most_common(
                    20
                )
            ),
            hard_escalator_counts=dict(
                Counter(
                    escalator
                    for item in items
                    for escalator in item.metadata.get("hard_escalators", [])
                )
            ),
            soft_escalator_counts=dict(
                Counter(
                    escalator
                    for item in items
                    for escalator in item.metadata.get("soft_escalators", [])
                )
            ),
            metadata={"workbench_version": "desk_workbench_v1"},
        )

    def list_decision_cards(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketDecisionCard]:
        return self.repo.list_market_decision_cards(
            market_id=market_id,
            limit=limit,
            offset=offset,
        )

    def get_latest_decision_card(self, market_id: str) -> MarketDecisionCard:
        card = self.repo.get_latest_market_decision_card(market_id)
        if card is None:
            raise WorkbenchServiceError("decision_card_not_found")
        return card

    def list_comparison_cards(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueComparisonCard]:
        return self.repo.list_cross_venue_comparison_cards(limit=limit, offset=offset)

    def create_note(self, note: DeskReviewNoteCreate) -> DeskReviewNote:
        return create_desk_review_note(note, repo=self.repo)

    def list_notes(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DeskReviewNote]:
        return self.repo.list_desk_review_notes(
            market_id=market_id,
            limit=limit,
            offset=offset,
        )

    def get_note(self, note_id: str) -> DeskReviewNote:
        note = self.repo.get_desk_review_note(note_id)
        if note is None:
            raise WorkbenchServiceError("desk_review_note_not_found")
        return note

    def get_run(self, workbench_run_id: str) -> WorkbenchRun:
        run = self.repo.get_workbench_run(workbench_run_id)
        if run is None:
            raise WorkbenchServiceError("workbench_run_not_found")
        return run

    def list_runs(self, *, limit: int = 500, offset: int = 0) -> list[WorkbenchRun]:
        return self.repo.list_workbench_runs(limit=limit, offset=offset)

    def get_run_summary(self, workbench_run_id: str) -> WorkbenchRunSummary:
        summary = self.repo.get_workbench_run_summary(workbench_run_id)
        if summary is None:
            raise WorkbenchServiceError("workbench_run_summary_not_found")
        return summary

    def run_workbench(self, config: WorkbenchRunConfig) -> WorkbenchRunResult:
        created_at = datetime.now(tz=UTC)
        market_ids = _resolve_market_ids(self.repo, config.market_ids, config.limit)
        run = WorkbenchRun(
            workbench_run_id=workbench_object_id(
                "workbench_run",
                {
                    "created_at": created_at,
                    "asof_timestamp": config.asof_timestamp,
                    "market_ids": market_ids,
                    "name": config.name,
                },
            ),
            name=config.name,
            created_at=created_at,
            started_at=created_at,
            completed_at=None,
            status=WorkbenchRunStatus.RUNNING,
            asof_timestamp=config.asof_timestamp,
            market_ids=market_ids,
            metadata={**dict(config.metadata), "queue_name": config.queue_name},
        )
        self.repo.save_workbench_run(run)
        queue_items: list[MarketReviewQueueItem] = []
        decision_cards: list[MarketDecisionCard] = []
        comparison_cards: list[CrossVenueComparisonCard] = []
        errors = 0
        try:
            if config.build_queue:
                queue_items = self.build_queue(
                    config.asof_timestamp,
                    market_ids=market_ids,
                    queue_name=config.queue_name,
                    limit=config.limit,
                    force=config.force,
                )
            if config.build_cards:
                for market_id in market_ids:
                    try:
                        decision_cards.append(
                            self.build_decision_card(
                                market_id,
                                config.asof_timestamp,
                                force=config.force,
                            )
                        )
                    except WorkbenchServiceError:
                        errors += 1
            if config.build_comparison_cards:
                comparison_cards = _build_comparison_cards(
                    self,
                    market_ids,
                    config.asof_timestamp,
                    config.force,
                    config.limit,
                )
        finally:
            completed = datetime.now(tz=UTC)
            run = run.model_copy(
                update={
                    "completed_at": completed,
                    "status": (
                        WorkbenchRunStatus.PARTIAL
                        if errors
                        else WorkbenchRunStatus.COMPLETED
                    ),
                    "queues_built": len(queue_items),
                    "cards_built": len(decision_cards),
                    "comparison_cards_built": len(comparison_cards),
                    "errors_count": errors,
                }
            )
            self.repo.update_workbench_run(run)
        summary = _summary_for_run(run, queue_items, decision_cards, comparison_cards)
        self.repo.save_workbench_run_summary(summary)
        return WorkbenchRunResult(
            run=run,
            queue_items=queue_items,
            decision_cards=decision_cards,
            comparison_cards=comparison_cards,
            summary=summary,
        )


def _resolve_market_ids(
    repo: PredictionMarketRepository,
    market_ids: list[str] | None,
    limit: int,
) -> list[str]:
    if market_ids:
        return sorted(dict.fromkeys(market_ids))[:limit]
    return [market.market_id for market in repo.list_markets(limit=limit)]


def _build_comparison_cards(
    service: WorkbenchService,
    market_ids: list[str],
    asof_timestamp: datetime,
    force: bool,
    limit: int,
) -> list[CrossVenueComparisonCard]:
    seen: set[str] = set()
    cards: list[CrossVenueComparisonCard] = []
    for market_id in market_ids:
        for assessment in service.repo.list_latest_equivalence_assessments_for_market_asof(
            market_id,
            asof_timestamp,
            limit=25,
        ):
            if assessment.equivalence_assessment_id in seen:
                continue
            seen.add(assessment.equivalence_assessment_id)
            cards.append(
                service.build_comparison_card(
                    assessment.equivalence_assessment_id,
                    asof_timestamp,
                    force=force,
                )
            )
            if len(cards) >= limit:
                return cards
    return cards


def _summary_for_run(
    run: WorkbenchRun,
    queue_items: list[MarketReviewQueueItem],
    decision_cards: list[MarketDecisionCard],
    comparison_cards: list[CrossVenueComparisonCard],
) -> WorkbenchRunSummary:
    reason_counts = Counter(
        reason for item in queue_items for reason in item.reason_codes
    )
    return WorkbenchRunSummary(
        summary_id=workbench_object_id(
            "workbench_summary",
            {"workbench_run_id": run.workbench_run_id, "created_at": datetime.now(tz=UTC)},
        ),
        workbench_run_id=run.workbench_run_id,
        created_at=datetime.now(tz=UTC),
        total_queue_items=len(queue_items),
        total_decision_cards=len(decision_cards),
        total_comparison_cards=len(comparison_cards),
        priority_counts=dict(Counter(item.priority_bucket.value for item in queue_items)),
        review_action_counts=dict(
            Counter(card.recommended_next_review_action.value for card in decision_cards)
        ),
        top_reason_codes=dict(reason_counts.most_common(20)),
        markets_reviewed=len(set(run.market_ids)),
        metadata={"workbench_version": "desk_workbench_v1"},
    )


def _queue_review_action(item: MarketReviewQueueItem) -> str:
    action = item.metadata.get("recommended_next_review_action")
    if isinstance(action, str) and action:
        return action
    return recommended_action(item.reason_codes).value
