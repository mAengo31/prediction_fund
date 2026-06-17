from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app

MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"


def test_cli_pretrade_commands_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_pretrade.db'}"
    runner = CliRunner()
    _load_samples(runner, database_url)

    policy_result = runner.invoke(
        app,
        ["pretrade-create-default-policy", "--database-url", database_url],
    )
    check_result = runner.invoke(
        app,
        [
            "pretrade-check",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )
    run_result = runner.invoke(
        app,
        [
            "pretrade-run",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--asof",
            "2026-06-16T12:00:00+00:00",
            "--max-checks",
            "10",
        ],
    )
    latest_result = runner.invoke(
        app,
        ["pretrade-latest", "--database-url", database_url, "--market-id", MARKET_ID],
    )
    decisions_result = runner.invoke(
        app,
        ["pretrade-decisions", "--database-url", database_url],
    )
    restriction_result = runner.invoke(
        app,
        [
            "pretrade-add-restriction",
            "--database-url",
            database_url,
            "--restriction-type",
            "NO_TRADE",
            "--scope-type",
            "MARKET",
            "--market-id",
            MARKET_ID,
            "--reason-code",
            "CLI_BLOCK",
        ],
    )
    restrictions_result = runner.invoke(
        app,
        ["pretrade-restrictions", "--database-url", database_url],
    )
    exposure_result = runner.invoke(
        app,
        [
            "pretrade-add-exposure",
            "--database-url",
            database_url,
            "--market-id",
            MARKET_ID,
            "--event-id",
            "event_cpi_threshold_2026_09",
            "--venue-id",
            "sample_research_venue",
            "--strategy-context",
            "RESEARCH",
            "--asof",
            "2026-06-16T12:00:00+00:00",
        ],
    )

    assert policy_result.exit_code == 0
    assert "default_pretrade_policy" in policy_result.output
    assert check_result.exit_code == 0
    assert "composite_risk_score" in check_result.output
    assert run_result.exit_code == 0
    assert "hard_block_rate" in run_result.output
    assert latest_result.exit_code == 0
    assert MARKET_ID in latest_result.output
    assert decisions_result.exit_code == 0
    assert "final_size" in decisions_result.output
    assert restriction_result.exit_code == 0
    assert "CLI_BLOCK" in restriction_result.output
    assert restrictions_result.exit_code == 0
    assert "CLI_BLOCK" in restrictions_result.output
    assert exposure_result.exit_code == 0
    assert re.search(r"exposure_snapshot_[a-f0-9]{24}", exposure_result.output)


def _load_samples(runner: CliRunner, database_url: str) -> None:
    init_result = runner.invoke(app, ["init-db", "--database-url", database_url])
    load_result = runner.invoke(app, ["load-sample-data", "--database-url", database_url])
    assert init_result.exit_code == 0
    assert load_result.exit_code == 0
