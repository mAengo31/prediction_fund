from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app


def test_cli_integrity_analyze_latest_and_signals_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_integrity.db'}"
    runner = CliRunner()

    run_once_result = runner.invoke(
        app,
        ["ingestion-run-once", "--database-url", database_url, "--venue", "kalshi"],
    )
    analyze_result = runner.invoke(
        app,
        [
            "integrity-analyze",
            "--database-url",
            database_url,
            "--market-id",
            "kalshi_market_kxweather_nyc_rain_20260930",
            "--asof",
            "2026-06-16T12:45:00Z",
        ],
    )
    latest_result = runner.invoke(
        app,
        [
            "integrity-latest",
            "--database-url",
            database_url,
            "--market-id",
            "kalshi_market_kxweather_nyc_rain_20260930",
            "--asof",
            "2026-06-16T12:45:00Z",
        ],
    )
    signals_result = runner.invoke(
        app,
        [
            "integrity-signals",
            "--database-url",
            database_url,
            "--market-id",
            "kalshi_market_kxweather_nyc_rain_20260930",
        ],
    )

    assert run_once_result.exit_code == 0
    assert analyze_result.exit_code == 0
    assert "overall_risk_score" in analyze_result.output
    assert latest_result.exit_code == 0
    assert "action_hint" in latest_result.output
    assert signals_result.exit_code == 0
    assert "signal_name" in signals_result.output


def test_cli_integrity_run_works(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_integrity_run.db'}"
    runner = CliRunner()

    run_once_result = runner.invoke(
        app,
        ["ingestion-run-once", "--database-url", database_url, "--venue", "kalshi"],
    )
    run_result = runner.invoke(
        app,
        [
            "integrity-run",
            "--database-url",
            database_url,
            "--asof",
            "2026-06-16T12:45:00Z",
            "--market-id",
            "kalshi_market_kxweather_nyc_rain_20260930",
            "--max-steps",
            "10",
            "--name",
            "cli integrity",
        ],
    )

    assert run_once_result.exit_code == 0
    assert run_result.exit_code == 0
    assert re.search(r"integrity_run_[a-f0-9]{24}", run_result.output)
    assert "total_assessments" in run_result.output
