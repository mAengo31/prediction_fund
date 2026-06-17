from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app

MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"


def test_cli_paper_commands_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_paper.db'}"
    runner = CliRunner()
    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    assert runner.invoke(app, ["load-sample-data", "--database-url", database_url]).exit_code == 0

    policy = runner.invoke(app, ["paper-create-default-policy", "--database-url", database_url])
    simulate = runner.invoke(
        app,
        [
            "paper-simulate-intent",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
            "--intent-type",
            "AGGRESSIVE_LIMIT",
            "--requested-price",
            "0.52",
        ],
    )
    orders = runner.invoke(app, ["paper-orders", "--database-url", database_url])
    fills = runner.invoke(app, ["paper-fills", "--database-url", database_url])
    position = runner.invoke(
        app,
        ["paper-position-latest", "--database-url", database_url, "--market-id", MARKET_ID],
    )
    portfolio = runner.invoke(app, ["paper-portfolio-latest", "--database-url", database_url])
    run = runner.invoke(
        app,
        [
            "paper-run",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--start",
            "2026-06-16T12:00:00+00:00",
            "--end",
            "2026-06-16T13:00:00+00:00",
            "--max-orders",
            "10",
        ],
    )

    assert policy.exit_code == 0
    assert "default_paper_execution_policy" in policy.output
    assert simulate.exit_code == 0
    assert "portfolio_equity_simulated" in simulate.output
    assert orders.exit_code == 0
    assert "paper_order" in orders.output
    assert fills.exit_code == 0
    assert "paper_fill" in fills.output
    assert position.exit_code == 0
    assert "unrealized_simulated" in position.output
    assert portfolio.exit_code == 0
    assert "equity_simulated" in portfolio.output
    assert run.exit_code == 0
    assert "final_equity_simulated" in run.output

