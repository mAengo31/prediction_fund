from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app


def test_cli_dataops_commands_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_dataops.db'}"
    runner = CliRunner()

    init = runner.invoke(app, ["init-db", "--database-url", database_url])
    defaults = runner.invoke(app, ["dataops-defaults", "--database-url", database_url])
    universes = runner.invoke(app, ["dataops-universes", "--database-url", database_url])
    plans = runner.invoke(app, ["dataops-collection-plans", "--database-url", database_url])
    collection = runner.invoke(
        app,
        [
            "dataops-run-collection",
            "--database-url",
            database_url,
            "--venue",
            "kalshi",
            "--mode",
            "FIXTURE",
        ],
    )
    coverage = runner.invoke(app, ["dataops-coverage", "--database-url", database_url])
    cycle = runner.invoke(
        app,
        [
            "dataops-cycle",
            "--database-url",
            database_url,
            "--no-collection",
        ],
    )
    gaps = runner.invoke(app, ["dataops-gaps", "--database-url", database_url])

    assert init.exit_code == 0
    assert defaults.exit_code == 0
    assert "collection_plans" in defaults.output
    assert universes.exit_code == 0
    assert "all_active_prediction_markets_v1" in universes.output
    assert plans.exit_code == 0
    assert "fixture_full_loop_v1" in plans.output
    assert collection.exit_code == 0
    assert "COMPLETED" in collection.output
    assert coverage.exit_code == 0
    assert "coverage_report_" in coverage.output
    assert cycle.exit_code == 0
    assert "coverage_score" in cycle.output
    assert gaps.exit_code == 0


def test_cli_dataops_backfill_create_and_run_unsupported(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_dataops_backfill.db'}"
    runner = CliRunner()
    assert runner.invoke(app, ["init-db", "--database-url", database_url]).exit_code == 0
    created = runner.invoke(
        app,
        [
            "dataops-backfill-create",
            "--database-url",
            database_url,
            "--venue",
            "kalshi",
            "--endpoint-type",
            "ORDERBOOK",
            "--market-id",
            "kalshi_market_kxweather_nyc_rain_20260930",
            "--start",
            "2026-06-16T11:00:00+00:00",
            "--end",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    assert created.exit_code == 0
    job_id = next(
        line.split("|", maxsplit=1)[0].strip()
        for line in created.output.splitlines()
        if line.startswith("backfill_job_")
    )
    run = runner.invoke(
        app,
        [
            "dataops-backfill-run",
            "--database-url",
            database_url,
            "--job-id",
            job_id,
        ],
    )

    assert run.exit_code == 0
    assert "COMPLETED" in run.output
