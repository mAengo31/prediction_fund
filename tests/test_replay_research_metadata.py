from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.runner import run_replay
from prediction_desk.research.service import ResearchService
from tests.paper_helpers import ASOF, MARKET_ID, loaded_repo


def test_replay_includes_research_metadata_if_available(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "replay_research.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        service = ResearchService(repo)
        service.create_default_research_strategies_if_missing()
        proposal = service.generate_research_proposals(
            MARKET_ID,
            ASOF,
            strategy_ids=["research_strategy_baseline_research_only_v1"],
        )[0]
        service.evaluate_research_proposal(
            proposal.proposal_id,
            enable_paper_simulation=False,
        )
        result = run_replay(
            ReplayRunConfig(
                policy_name="research_policy_v1",
                start_time=ASOF,
                end_time=ASOF + timedelta(hours=1),
                interval_seconds=3600,
                market_ids=[MARKET_ID],
                max_steps=10,
            ),
            repo=repo,
        )

    metadata = result.steps[0].metadata
    assert metadata["latest_research_signal_ids"]
    assert metadata["latest_research_proposal_ids"]
    assert metadata["latest_research_trace_ids"]
    assert metadata["research_signal_count"] >= 1
    assert metadata["research_pretrade_action_counts"]["ALLOW"] == 1
    assert metadata["policy"] == "research_policy_v1"
    assert result.steps[0].action == "ALLOW"
