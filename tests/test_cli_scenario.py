from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app

SCENARIO_MARKET_ID = "mkt_sfo_rain_2026_09_01"


def test_cli_scenario_commands_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_scenario.db'}"
    runner = CliRunner()
    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    assert runner.invoke(app, ["load-sample-data", "--database-url", database_url]).exit_code == 0

    seed = runner.invoke(
        app,
        [
            "scenario-build-seed",
            "--database-url",
            database_url,
            "--market-id",
            SCENARIO_MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    imported = runner.invoke(
        app,
        [
            "scenario-import-fixtures",
            "--database-url",
            database_url,
            "--market-id",
            SCENARIO_MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    latest = runner.invoke(
        app,
        [
            "scenario-latest",
            "--database-url",
            database_url,
            "--market-id",
            SCENARIO_MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    run = runner.invoke(
        app,
        [
            "scenario-run",
            "--database-url",
            database_url,
            "--market-id",
            SCENARIO_MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
            "--max-items",
            "10",
        ],
    )

    assert seed.exit_code == 0
    assert "scenario_seed_" in seed.output
    assert imported.exit_code == 0
    assert "scenario_feature_" in imported.output
    assert latest.exit_code == 0
    assert "scenario_feature_" in latest.output
    assert run.exit_code == 0
    assert "scenario_run_" in run.output
