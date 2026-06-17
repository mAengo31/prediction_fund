from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.research.attribution import (
    build_research_attribution_report,
    build_research_run_summary,
)
from tests.paper_helpers import loaded_repo
from tests.research_helpers import research_proposal, research_signal, research_trace


def test_research_summary_counts_and_simulated_fields_are_labeled(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "research_attribution.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        signal = repo.save_research_signal(research_signal())
        proposal = repo.save_research_intent_proposal(
            research_proposal(research_signal_id=signal.research_signal_id)
        )
        repo.save_research_decision_trace(
            research_trace(
                research_signal_id=signal.research_signal_id,
                proposal_id=proposal.proposal_id,
                paper_order_status="FILLED",
                filled_size_units_simulated=Decimal("1"),
            )
        )
        summary = build_research_run_summary("research_run_test", repo=repo)
        attribution = build_research_attribution_report("research_run_test", repo=repo)

    assert summary.total_signals == 1
    assert summary.total_proposals == 1
    assert summary.total_paper_fills == 1
    assert summary.proposal_to_pretrade_pass_rate == Decimal("1")
    assert "simulated" in "final_unrealized_pnl_simulated"
    assert attribution.by_strategy
    assert "simulated_pnl_by_strategy" in attribution.model_dump()


def test_attribution_report_counts_by_strategy_market_and_reason_code(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "research_attribution_counts.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        repo.save_research_decision_trace(research_trace())
        report = build_research_attribution_report("research_run_test", repo=repo)

    assert report.by_strategy
    assert report.by_market
    assert report.by_reason_code["TEST_TRACE"] == 1
    assert report.by_pretrade_action["ALLOW"] == 1

