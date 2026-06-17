from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import RestrictionScopeType, RestrictionType
from prediction_desk.pretrade.models import MarketRestrictionRuleCreate
from prediction_desk.pretrade.service import PreTradeService
from prediction_desk.research.service import ResearchService
from tests.paper_helpers import MARKET_ID, loaded_repo
from tests.research_helpers import ASOF, research_proposal, research_signal


def test_service_persists_features_signals_proposals_and_trace(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_service.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ResearchService(repo)
        service.create_default_research_strategies_if_missing()
        features = service.build_features_for_market(MARKET_ID, ASOF)
        signals = service.generate_research_signals(MARKET_ID, ASOF)
        proposals = service.generate_research_proposals(MARKET_ID, ASOF)
        trace = service.evaluate_research_proposal(
            proposals[0].proposal_id,
            enable_paper_simulation=False,
        )

    assert features
    assert signals
    assert proposals
    assert trace.pretrade_action == "ALLOW"
    assert trace.paper_order_id is None


def test_service_avoids_duplicate_signals_and_proposals_unless_force(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "research_service_dedupe.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ResearchService(repo)
        service.create_default_research_strategies_if_missing()
        first = service.generate_research_proposals(MARKET_ID, ASOF)
        duplicate = service.generate_research_proposals(MARKET_ID, ASOF)
        forced = service.generate_research_proposals(MARKET_ID, ASOF, force=True)

    assert [proposal.proposal_id for proposal in duplicate] == [
        proposal.proposal_id for proposal in first
    ]
    assert len(forced) == len(first)


def test_proposal_evaluation_blocks_without_paper_fill_when_pretrade_rejects(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "research_service_pretrade_reject.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        PreTradeService(repo).save_market_restriction_rule(
            MarketRestrictionRuleCreate(
                restriction_type=RestrictionType.NO_TRADE,
                scope_type=RestrictionScopeType.MARKET,
                market_id=MARKET_ID,
                reason_code="RESEARCH_TEST_BLOCK",
            )
        )
        proposal = repo.save_research_intent_proposal(research_proposal())
        trace = ResearchService(repo).evaluate_research_proposal(
            proposal.proposal_id,
            enable_paper_simulation=True,
        )

    assert trace.pretrade_action == "NO_TRADE"
    assert trace.paper_order_id is None
    assert trace.paper_fill_ids == []


def test_paper_enabled_proposal_evaluation_creates_fill_when_allowed_and_fillable(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "research_service_paper_fill.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        proposal = repo.save_research_intent_proposal(
            research_proposal(
                requested_price=Decimal("0.52"),
                intent_type="AGGRESSIVE_LIMIT",
            )
        )
        trace = ResearchService(repo).evaluate_research_proposal(
            proposal.proposal_id,
            enable_paper_simulation=True,
        )

    assert trace.pretrade_action == "ALLOW"
    assert trace.paper_order_status == "FILLED"
    assert trace.filled_size_units_simulated == Decimal("1.0000000000")
    assert trace.paper_fill_ids


def test_future_research_outputs_not_returned_by_asof_lookup(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_asof_outputs.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        signal = repo.save_research_signal(research_signal())
        future_signal = signal.model_copy(
            update={
                "research_signal_id": "future_research_signal",
                "available_at": ASOF + timedelta(days=1),
                "output_hash": "future_research_signal_output",
            }
        )
        repo.save_research_signal(future_signal)

        signals = repo.list_research_signals(market_id=MARKET_ID, asof_timestamp=ASOF)

    assert [item.research_signal_id for item in signals] == [signal.research_signal_id]
