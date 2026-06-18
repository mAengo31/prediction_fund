from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from prediction_desk.dataops.enums import CoverageScopeType
from prediction_desk.dataops.gaps import detect_data_gaps
from prediction_desk.equivalence.service import EquivalenceService
from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import RestrictionScopeType, RestrictionType
from prediction_desk.pretrade.models import MarketRestrictionRuleCreate
from prediction_desk.pretrade.service import PreTradeService
from prediction_desk.research.service import ResearchService
from prediction_desk.workbench.enums import RecommendedReviewAction
from prediction_desk.workbench.models import DeskReviewNoteCreate, WorkbenchRunConfig
from prediction_desk.workbench.runner import run_workbench_build
from prediction_desk.workbench.service import WorkbenchService
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues
from tests.paper_helpers import MARKET_ID, loaded_repo

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
DIVERGENCE_ASOF = datetime(2026, 6, 16, 12, 20, tzinfo=UTC)


def test_queue_prioritizes_data_gaps(tmp_path: Path) -> None:
    factory = _sample_factory(tmp_path, "workbench_data_gap.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        detect_data_gaps(CoverageScopeType.GLOBAL, ASOF, repo=repo)
        items = WorkbenchService(repo).build_queue(ASOF, limit=10)

    assert items
    assert any("MISSING_PRICE_SNAPSHOT" in item.reason_codes for item in items)
    assert items[0].priority_score >= items[-1].priority_score


def test_queue_prioritizes_pretrade_blocks(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "workbench_pretrade.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        PreTradeService(repo).save_market_restriction_rule(
            MarketRestrictionRuleCreate(
                restriction_type=RestrictionType.NO_TRADE,
                scope_type=RestrictionScopeType.MARKET,
                market_id=MARKET_ID,
                reason_code="WORKBENCH_TEST_BLOCK",
            )
        )
        PreTradeService(repo).check_market_default_intent(MARKET_ID, ASOF)
        item = WorkbenchService(repo).build_queue(
            ASOF,
            market_ids=[MARKET_ID],
        )[0]

    assert "PRETRADE_BLOCKED" in item.reason_codes
    assert item.priority_score >= 40


def test_queue_prioritizes_divergence_review(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'workbench_divergence.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        equivalence = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            DIVERGENCE_ASOF,
        )
        from prediction_desk.divergence.service import DivergenceService

        DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )
        review_asof = datetime.now(tz=UTC)
        item = WorkbenchService(repo).build_queue(
            review_asof,
            market_ids=[KALSHI_RAIN],
        )[0]

    assert any(code.startswith("DIVERGENCE") for code in item.reason_codes)
    assert item.priority_score >= 20


def test_clean_market_gets_low_or_info_priority(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "workbench_clean.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        PreTradeService(repo).check_market_default_intent(MARKET_ID, ASOF)
        item = WorkbenchService(repo).build_queue(ASOF, market_ids=[MARKET_ID])[0]

    assert item.priority_score < 45


def test_decision_card_aggregates_without_future_lookahead(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "workbench_card_asof.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        current = repo.get_latest_price_snapshot_asof(MARKET_ID, ASOF)
        assert current is not None
        future = current.model_copy(
            update={
                "price_snapshot_id": "future_workbench_price",
                "available_at": ASOF + timedelta(days=1),
                "data_hash": "future_workbench_price_hash",
                "price": 0,
                "mid": 0,
            }
        )
        repo.save_market_price_snapshot(future)
        card = WorkbenchService(repo).build_decision_card(MARKET_ID, ASOF)

    assert card.latest_price == current.price
    assert "future_workbench_price" not in card.source_ref_ids


def test_comparison_card_uses_equivalence_and_divergence(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'workbench_comparison.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        equivalence = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            DIVERGENCE_ASOF,
        )
        from prediction_desk.divergence.service import DivergenceService

        divergence = DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )
        review_asof = datetime.now(tz=UTC)
        card = WorkbenchService(repo).build_comparison_card(
            equivalence.assessment.equivalence_assessment_id,
            review_asof,
        )

    assert card.equivalence_assessment_id == equivalence.assessment.equivalence_assessment_id
    assert card.divergence_assessment_id == divergence.assessment.divergence_assessment_id
    assert card.recommended_next_review_action in {
        RecommendedReviewAction.REVIEW_DIVERGENCE,
        RecommendedReviewAction.NO_ACTION,
        RecommendedReviewAction.WATCH_ONLY,
    }


def test_note_create_list_get_and_runner_summary_work(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "workbench_notes_runner.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = WorkbenchService(repo)
        note = service.create_note(
            DeskReviewNoteCreate(market_id=MARKET_ID, text="Observed clean review context.")
        )
        notes = service.list_notes(market_id=MARKET_ID)
        fetched = service.get_note(note.note_id)
        result = run_workbench_build(
            WorkbenchRunConfig(asof_timestamp=ASOF, market_ids=[MARKET_ID]),
            repo=repo,
        )

    assert fetched.note_id == note.note_id
    assert [item.note_id for item in notes] == [note.note_id]
    assert result.summary.total_queue_items == 1
    assert result.summary.total_decision_cards == 1


def test_default_watchlists_are_idempotent(tmp_path: Path) -> None:
    factory = _sample_factory(tmp_path, "workbench_watchlists.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = WorkbenchService(repo)
        first = service.create_default_watchlists_if_missing()
        second = service.create_default_watchlists_if_missing()

    assert [item.watchlist_id for item in first] == [item.watchlist_id for item in second]


def test_research_signal_appears_in_decision_card(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "workbench_research.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        research = ResearchService(repo)
        research.create_default_research_strategies_if_missing()
        research.generate_research_signals(MARKET_ID, ASOF)
        card = WorkbenchService(repo).build_decision_card(MARKET_ID, ASOF)

    assert card.research_summary["signal_count"] >= 1


def _sample_factory(tmp_path: Path, name: str):
    database_url = f"sqlite:///{tmp_path / name}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        load_sample_data(PredictionMarketRepository(session))
    return factory
