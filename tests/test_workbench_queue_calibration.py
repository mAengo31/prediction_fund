from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.workbench.enums import ReviewOutcome, ReviewPriorityBucket, ReviewStatus
from prediction_desk.workbench.models import WorkbenchQueueItemStatusUpdateRequest
from prediction_desk.workbench.scoring import (
    priority_bucket,
    score_review_context_details,
)
from prediction_desk.workbench.service import WorkbenchService
from tests.paper_helpers import MARKET_ID, loaded_repo

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_low_data_quality_alone_is_not_critical() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=20),
        integrity_assessment=None,
        divergence_assessments=[],
        pretrade_decision=None,
        research_signals=[],
        data_gaps=[],
        scenario_feature=None,
    )

    assert "LOW_DATA_QUALITY" in details.reason_codes
    assert priority_bucket(details.priority_score) != ReviewPriorityBucket.CRITICAL
    assert "DATA_GAP_ONLY_CONTEXT" in details.dampeners


def test_pretrade_no_trade_with_hard_blocker_is_critical() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=90),
        integrity_assessment=None,
        divergence_assessments=[],
        pretrade_decision=SimpleNamespace(
            action="NO_TRADE",
            hard_blockers=["MARKET_NOT_ACTIVE"],
            reason_codes=["MARKET_NOT_ACTIVE"],
        ),
        research_signals=[],
        data_gaps=[],
        scenario_feature=None,
    )

    assert priority_bucket(details.priority_score) == ReviewPriorityBucket.CRITICAL
    assert "PRETRADE_HARD_BLOCK" in details.hard_escalators


def test_pretrade_manual_review_is_high() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=90),
        integrity_assessment=None,
        divergence_assessments=[],
        pretrade_decision=SimpleNamespace(
            action="MANUAL_REVIEW",
            hard_blockers=[],
            reason_codes=["MISSING_RULE_SNAPSHOT"],
        ),
        research_signals=[],
        data_gaps=[],
        scenario_feature=None,
    )

    assert priority_bucket(details.priority_score) == ReviewPriorityBucket.HIGH
    assert "PRETRADE_MANUAL_REVIEW" in details.soft_escalators


def test_divergence_needs_review_is_high() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=90),
        integrity_assessment=None,
        divergence_assessments=[
            SimpleNamespace(
                status="NEEDS_REVIEW",
                action_hint="MANUAL_REVIEW",
                overall_divergence_score=45,
            )
        ],
        pretrade_decision=None,
        research_signals=[],
        data_gaps=[],
        scenario_feature=None,
    )

    assert priority_bucket(details.priority_score) == ReviewPriorityBucket.HIGH
    assert "DIVERGENCE_NEEDS_REVIEW" in details.soft_escalators


def test_divergence_do_not_compare_is_critical() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=90),
        integrity_assessment=None,
        divergence_assessments=[
            SimpleNamespace(
                status="DO_NOT_COMPARE",
                action_hint="DO_NOT_COMPARE",
                overall_divergence_score=0,
            )
        ],
        pretrade_decision=None,
        research_signals=[],
        data_gaps=[],
        scenario_feature=None,
    )

    assert priority_bucket(details.priority_score) == ReviewPriorityBucket.CRITICAL
    assert "DIVERGENCE_DO_NOT_COMPARE" in details.hard_escalators


def test_public_empty_rule_gap_is_dampened() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=90),
        integrity_assessment=None,
        divergence_assessments=[],
        pretrade_decision=None,
        research_signals=[],
        data_gaps=[
            SimpleNamespace(
                gap_type="MISSING_RULE_SNAPSHOT",
                severity="WARNING",
                reason_code="NO_RULE_TEXT_IN_PUBLIC_DETAIL_PAYLOAD",
                description="Public detail rule fields were empty.",
                metadata={},
            )
        ],
        scenario_feature=None,
    )

    assert priority_bucket(details.priority_score) in {
        ReviewPriorityBucket.INFO,
        ReviewPriorityBucket.LOW,
    }
    assert "PUBLIC_DETAIL_RULE_TEXT_EMPTY" in details.dampeners


def test_multiple_soft_warnings_escalate_without_defaulting_to_critical() -> None:
    details = score_review_context_details(
        quality_report=SimpleNamespace(quality_score=20),
        integrity_assessment=SimpleNamespace(
            action_hint="MANUAL_REVIEW",
            overall_risk_score=75,
            severity="ERROR",
            reason_codes=["LOW_DATA_QUALITY"],
        ),
        divergence_assessments=[],
        pretrade_decision=SimpleNamespace(
            action="NO_TRADE",
            hard_blockers=["INTEGRITY_ACTION_HINT_NO_TRADE"],
            reason_codes=["INTEGRITY_ACTION_HINT_NO_TRADE"],
        ),
        research_signals=[
            SimpleNamespace(signal_type="REVIEW_ONLY", action_bias="REVIEW_ONLY")
        ],
        data_gaps=[],
        scenario_feature=None,
    )

    assert priority_bucket(details.priority_score) == ReviewPriorityBucket.HIGH
    assert not details.hard_escalators


def test_latest_queue_view_keeps_history_but_returns_one_item_per_market(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "workbench_latest_queue.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = WorkbenchService(repo)
        first = service.build_queue(ASOF, market_ids=[MARKET_ID], queue_name="latest_test")
        second = service.build_queue(
            ASOF + timedelta(minutes=5),
            market_ids=[MARKET_ID],
            queue_name="latest_test",
        )
        historical = service.list_queue_items(queue_name="latest_test", limit=10)
        latest = service.list_latest_queue_items(queue_name="latest_test", limit=10)
        summary = service.summarize_queue(queue_name="latest_test")

    assert first[0].queue_item_id != second[0].queue_item_id
    assert len(historical) == 2
    assert len(latest) == 1
    assert latest[0].queue_item_id == second[0].queue_item_id
    assert summary.total_items == 1


def test_queue_status_update_creates_note_and_active_view_excludes_resolved(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "workbench_status_update.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = WorkbenchService(repo)
        item = service.build_queue(
            ASOF,
            market_ids=[MARKET_ID],
            queue_name="review_status_test",
        )[0]
        updated = service.update_queue_item_status(
            item.queue_item_id,
            WorkbenchQueueItemStatusUpdateRequest(
                review_status=ReviewStatus.RESOLVED,
                reviewed_by="operator",
                review_outcome=ReviewOutcome.DATA_ISSUE_CONFIRMED,
                review_reason="Known fixture data gap.",
                note_text="Review update test note. No trading action.",
                tags=["data-gap"],
            ),
        )
        active = service.list_latest_queue_items(queue_name="review_status_test")
        include_resolved = service.list_latest_queue_items(
            queue_name="review_status_test",
            include_resolved=True,
        )
        notes = service.list_notes(market_id=MARKET_ID)
        status = service.get_status(queue_name="review_status_test")

    assert updated.review_status == ReviewStatus.RESOLVED
    assert updated.metadata["review_outcome"] == ReviewOutcome.DATA_ISSUE_CONFIRMED.value
    assert updated.metadata["reviewed_by"] == "operator"
    assert updated.metadata["linked_note_id"].startswith("desk_note_")
    assert len(active) == 0
    assert len(include_resolved) == 1
    assert include_resolved[0].queue_item_id == item.queue_item_id
    assert notes[0].queue_item_id == item.queue_item_id
    assert status.latest_queue_item_count == 0
    assert status.review_status_counts == {ReviewStatus.RESOLVED.value: 1}
    assert status.public_read_schedule_status == "HELD"
