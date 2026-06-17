from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.research.models import ResearchRunConfig
from prediction_desk.research.runner import ResearchRunError, run_research_simulation
from tests.paper_helpers import ASOF, MARKET_ID, loaded_repo


def test_research_run_persists_outputs_summary_and_attribution(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_runner.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = run_research_simulation(
            ResearchRunConfig(
                name="research test",
                start_time=ASOF,
                end_time=ASOF,
                interval_seconds=3600,
                strategy_ids=["research_strategy_baseline_research_only_v1"],
                market_ids=[MARKET_ID],
                max_steps=10,
                max_proposals=10,
                enable_paper_simulation=False,
            ),
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.summary.total_signals == 1
    assert result.summary.total_proposals == 1
    assert result.summary.total_pretrade_checks == 1
    assert result.attribution.by_strategy


def test_research_run_enforces_max_steps(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_runner_max_steps.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        try:
            run_research_simulation(
                ResearchRunConfig(
                    start_time=ASOF,
                    end_time=ASOF,
                    interval_seconds=3600,
                    market_ids=[MARKET_ID],
                    max_steps=1,
                    max_proposals=10,
                ),
                repo=repo,
            )
        except ResearchRunError as exc:
            assert exc.code == "too_many_research_steps"
        else:  # pragma: no cover
            raise AssertionError("expected max step guardrail")


def test_research_run_enforces_max_proposals(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_runner_max_proposals.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = run_research_simulation(
            ResearchRunConfig(
                start_time=ASOF,
                end_time=ASOF + timedelta(hours=1),
                interval_seconds=3600,
                strategy_ids=["research_strategy_baseline_research_only_v1"],
                market_ids=[MARKET_ID],
                max_steps=10,
                max_proposals=1,
                enable_paper_simulation=False,
            ),
            repo=repo,
        )

    assert result.run.errors_count == 1
    assert result.summary.total_proposals == 1


def test_research_runner_database_url_path_works(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_runner_url.db")
    database_url = f"sqlite:///{tmp_path / 'research_runner_url.db'}"
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        assert PredictionMarketRepository(session).get_market(MARKET_ID) is not None

    result = run_research_simulation(
        ResearchRunConfig(
            start_time=ASOF,
            end_time=ASOF,
            interval_seconds=3600,
            strategy_ids=["research_strategy_baseline_research_only_v1"],
            market_ids=[MARKET_ID],
            max_steps=10,
            max_proposals=10,
            enable_paper_simulation=False,
        ),
        database_url=database_url,
    )

    assert factory is not None
    assert result.summary.total_proposals == 1
