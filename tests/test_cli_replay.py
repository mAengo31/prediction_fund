from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app


def test_cli_replay_run_summary_and_steps_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_replay.db'}"
    runner = CliRunner()
    _load_samples(runner, database_url)

    run_result = runner.invoke(
        app,
        [
            "replay-run",
            "--database-url",
            database_url,
            "--policy",
            "trust_verdict_v1",
            "--start",
            "2026-06-16T12:00:00+00:00",
            "--end",
            "2026-06-16T13:00:00+00:00",
            "--interval-seconds",
            "3600",
            "--market-id",
            "mkt_cpi_yoy_at_least_3pct_2026_09",
            "--max-steps",
            "10",
            "--name",
            "cli replay",
        ],
    )

    assert run_result.exit_code == 0
    run_id = _run_id(run_result.output)
    assert run_id is not None

    summary_result = runner.invoke(
        app,
        ["replay-summary", "--database-url", database_url, "--run-id", run_id],
    )
    steps_result = runner.invoke(
        app,
        [
            "replay-steps",
            "--database-url",
            database_url,
            "--run-id",
            run_id,
            "--limit",
            "1",
        ],
    )

    assert summary_result.exit_code == 0
    assert run_id in summary_result.output
    assert steps_result.exit_code == 0
    assert "mkt_cpi_yoy_at_least_3pct_2026_09" in steps_result.output
    assert "resolution_risk_score" in steps_result.output


def _load_samples(runner: CliRunner, database_url: str) -> None:
    init_result = runner.invoke(app, ["init-db", "--database-url", database_url])
    load_result = runner.invoke(app, ["load-sample-data", "--database-url", database_url])
    assert init_result.exit_code == 0
    assert load_result.exit_code == 0


def _run_id(output: str) -> str | None:
    match = re.search(r"replay_run_[a-f0-9]{24}", output)
    return match.group(0) if match else None
