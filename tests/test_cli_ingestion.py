from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app


def test_cli_ingest_fixtures_runs_and_lists_mappings(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_ingestion.db'}"
    runner = CliRunner()

    ingest_result = runner.invoke(
        app,
        [
            "ingest-fixtures",
            "--database-url",
            database_url,
            "--venue",
            "kalshi",
        ],
    )
    runs_result = runner.invoke(
        app,
        ["ingestion-runs", "--database-url", database_url, "--venue", "Kalshi"],
    )
    mappings_result = runner.invoke(
        app,
        ["venue-mappings", "--database-url", database_url, "--venue", "Kalshi"],
    )

    assert ingest_result.exit_code == 0
    assert "Kalshi" in ingest_result.output
    assert "COMPLETED" in ingest_result.output
    assert runs_result.exit_code == 0
    assert "ingestion_run_" in runs_result.output
    assert mappings_result.exit_code == 0
    assert "KXWEATHER-NYC-RAIN-20260930" in mappings_result.output


def test_cli_ingest_public_sample_without_allow_network_fails_safely(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_ingestion.db'}"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ingest-public-sample",
            "--database-url",
            database_url,
            "--venue",
            "kalshi",
        ],
    )

    assert result.exit_code == 1
    assert "requires --allow-network" in result.output
