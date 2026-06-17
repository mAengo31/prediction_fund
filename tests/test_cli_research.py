from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app
from tests.paper_helpers import MARKET_ID


def test_cli_research_commands_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_research.db'}"
    runner = CliRunner()
    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    assert runner.invoke(app, ["load-sample-data", "--database-url", database_url]).exit_code == 0

    defaults = runner.invoke(
        app,
        ["research-create-default-strategies", "--database-url", database_url],
    )
    strategies = runner.invoke(app, ["research-strategies", "--database-url", database_url])
    features = runner.invoke(
        app,
        [
            "research-build-features",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    signals = runner.invoke(
        app,
        [
            "research-generate-signals",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    proposals = runner.invoke(
        app,
        [
            "research-generate-proposals",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
            "--strategy-id",
            "research_strategy_baseline_research_only_v1",
        ],
    )

    assert defaults.exit_code == 0
    assert "baseline_research_only_v1" in defaults.output
    assert strategies.exit_code == 0
    assert features.exit_code == 0
    assert "MARKET_DATA" in features.output
    assert signals.exit_code == 0
    assert "signal_type" in signals.output
    assert proposals.exit_code == 0
    assert "proposal_id" in proposals.output


def test_cli_research_run_and_attribution_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_research_run.db'}"
    runner = CliRunner()
    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    assert runner.invoke(app, ["load-sample-data", "--database-url", database_url]).exit_code == 0

    run = runner.invoke(
        app,
        [
            "research-run",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--strategy-id",
            "research_strategy_baseline_research_only_v1",
            "--start",
            "2026-06-16T12:00:00+00:00",
            "--end",
            "2026-06-16T12:00:00+00:00",
            "--max-steps",
            "10",
            "--max-proposals",
            "10",
            "--no-paper-simulation",
        ],
    )
    assert run.exit_code == 0
    run_id = next(
        line.split()[0]
        for line in run.output.splitlines()
        if line.startswith("research_run_")
    )
    summary = runner.invoke(
        app,
        ["research-summary", "--database-url", database_url, "--run-id", run_id],
    )
    attribution = runner.invoke(
        app,
        ["research-attribution", "--database-url", database_url, "--run-id", run_id],
    )

    assert "proposal_pass_rate" in run.output
    assert summary.exit_code == 0
    assert "paper_fills" in summary.output
    assert attribution.exit_code == 0
    assert "strategies" in attribution.output
