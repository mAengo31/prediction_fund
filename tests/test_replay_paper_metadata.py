from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from prediction_desk.paper.models import (
    PaperSimulateIntentRequest,
    compute_trade_intent_from_request,
)
from prediction_desk.paper.service import PaperExecutionService
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.runner import run_replay
from tests.paper_helpers import ASOF, MARKET_ID, loaded_repo


def test_replay_includes_paper_metadata_if_available(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "replay_paper.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        request = PaperSimulateIntentRequest(
            market_id=MARKET_ID,
            side="BUY",
            intent_type="AGGRESSIVE_LIMIT",
            requested_price=Decimal("0.52"),
            requested_size_units=Decimal("1"),
            asof_timestamp=ASOF,
        )
        PaperExecutionService(repo).simulate_trade_intent(
            compute_trade_intent_from_request(request, ASOF)
        )
        result = run_replay(
            ReplayRunConfig(
                policy_name="paper_sim_gate_v1",
                start_time=ASOF,
                end_time=ASOF + timedelta(hours=1),
                interval_seconds=3600,
                market_ids=[MARKET_ID],
                max_steps=10,
            ),
            repo=repo,
        )

    metadata = result.steps[0].metadata
    assert metadata["latest_paper_position_snapshot_id"]
    assert metadata["paper_position_units"] == "1.0000000000"
    assert metadata["latest_paper_portfolio_snapshot_id"]
    assert metadata["policy"] == "paper_sim_gate_v1"
