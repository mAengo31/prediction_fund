"""Desk review journal helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.workbench.models import (
    DeskReviewNote,
    DeskReviewNoteCreate,
    workbench_object_id,
)


def create_desk_review_note(
    note: DeskReviewNoteCreate,
    *,
    repo: PredictionMarketRepository | None = None,
) -> DeskReviewNote:
    if repo is not None:
        return _create(repo, note)
    with session_scope() as session:
        return _create(PredictionMarketRepository(session), note)


def list_desk_review_notes(
    *,
    market_id: str | None = None,
    limit: int = 500,
    offset: int = 0,
    repo: PredictionMarketRepository | None = None,
) -> list[DeskReviewNote]:
    if repo is not None:
        return repo.list_desk_review_notes(market_id=market_id, limit=limit, offset=offset)
    with session_scope() as session:
        return PredictionMarketRepository(session).list_desk_review_notes(
            market_id=market_id,
            limit=limit,
            offset=offset,
        )


def get_desk_review_note(
    note_id: str,
    *,
    repo: PredictionMarketRepository | None = None,
) -> DeskReviewNote | None:
    if repo is not None:
        return repo.get_desk_review_note(note_id)
    with session_scope() as session:
        return PredictionMarketRepository(session).get_desk_review_note(note_id)


def _create(repo: PredictionMarketRepository, note: DeskReviewNoteCreate) -> DeskReviewNote:
    created_at = datetime.now(tz=UTC)
    saved = DeskReviewNote(
        note_id=workbench_object_id(
            "desk_note",
            {
                "created_at": created_at,
                "market_id": note.market_id,
                "queue_item_id": note.queue_item_id,
                "decision_card_id": note.decision_card_id,
                "comparison_card_id": note.comparison_card_id,
                "text": note.text,
            },
        ),
        created_at=created_at,
        market_id=note.market_id,
        queue_item_id=note.queue_item_id,
        decision_card_id=note.decision_card_id,
        comparison_card_id=note.comparison_card_id,
        author=note.author,
        note_type=note.note_type,
        text=note.text,
        tags=list(note.tags),
        metadata=dict(note.metadata),
    )
    return repo.save_desk_review_note(saved)

