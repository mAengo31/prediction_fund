from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app


def test_cli_analyze_rules_works(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_resolution.db'}"
    runner = CliRunner()
    _load_samples(runner, database_url)

    result = runner.invoke(
        app,
        [
            "analyze-rules",
            "--database-url",
            database_url,
            "--market-id",
            "mkt_sfo_rain_2026_09_01",
        ],
    )

    assert result.exit_code == 0
    assert "mkt_sfo_rain_2026_09_01" in result.output
    assert "PARSED" in result.output
    assert "SCALAR_THRESHOLD" in result.output


def test_cli_diff_rule_snapshots_works(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_resolution.db'}"
    runner = CliRunner()
    _load_samples(runner, database_url)

    result = runner.invoke(
        app,
        [
            "diff-rule-snapshots",
            "--database-url",
            database_url,
            "--market-id",
            "mkt_rate_cut_rule_change_2026",
        ],
    )

    assert result.exit_code == 0
    assert "mkt_rate_cut_rule_change_2026" in result.output
    assert "RESOLUTION_SOURCE_CHANGED" in result.output
    assert "DEADLINE_CHANGED" in result.output


def _load_samples(runner: CliRunner, database_url: str) -> None:
    init_result = runner.invoke(app, ["init-db", "--database-url", database_url])
    load_result = runner.invoke(app, ["load-sample-data", "--database-url", database_url])
    assert init_result.exit_code == 0
    assert load_result.exit_code == 0
