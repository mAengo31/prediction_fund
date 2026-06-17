from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.examples.sample_markets import load_sample_data, sample_markets
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.policies import PreTradeGatePolicy
from prediction_desk.replay.runner import run_replay

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"


def test_pretrade_gate_policy_requires_repository() -> None:
    clean, *_ = sample_markets()

    decision = PreTradeGatePolicy().decide(
        market=clean.market,
        rule_snapshot=None,
        orderbook_snapshot=None,
        resolution_analysis=None,
        integrity_assessment=None,
        trust_verdict=None,
        asof_timestamp=ASOF,
        repo=None,
    )

    assert decision.action == VerdictAction.MANUAL_REVIEW.value
    assert decision.allowed_size_multiplier == Decimal("0.0")
    assert "PRETRADE_REPOSITORY_UNAVAILABLE" in decision.reason_codes


def test_replay_pretrade_gate_policy_maps_decision_and_metadata(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_pretrade.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = run_replay(
            ReplayRunConfig(
                policy_name="pretrade_gate_v1",
                start_time=ASOF,
                end_time=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
                interval_seconds=3600,
                market_ids=[MARKET_ID],
                max_steps=10,
            ),
            repo=repo,
        )

    assert result.steps[0].metadata["pretrade_decision_id"].startswith(
        "pretrade_decision_"
    )
    assert result.steps[0].metadata["pretrade_action"] == result.steps[0].action
    assert "pretrade_final_allowed_size_units" in result.steps[0].metadata
