from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from prediction_desk.cli import app


def test_cli_market_data_derive_and_latest_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_marketdata.db'}"
    runner = CliRunner()

    load_result = runner.invoke(
        app,
        ["load-sample-data", "--database-url", database_url],
    )
    derive_result = runner.invoke(
        app,
        [
            "market-data-derive",
            "--database-url",
            database_url,
            "--market-id",
            "mkt_cpi_yoy_at_least_3pct_2026_09",
        ],
    )
    latest_result = runner.invoke(
        app,
        [
            "market-data-latest",
            "--database-url",
            database_url,
            "--market-id",
            "mkt_cpi_yoy_at_least_3pct_2026_09",
            "--asof",
            "2026-06-16T13:00:00Z",
        ],
    )
    prices_result = runner.invoke(
        app,
        [
            "market-data-prices",
            "--database-url",
            database_url,
            "--market-id",
            "mkt_cpi_yoy_at_least_3pct_2026_09",
        ],
    )

    assert load_result.exit_code == 0
    assert derive_result.exit_code == 0
    assert "price_snapshots_created" in derive_result.output
    assert latest_result.exit_code == 0
    assert "price_" in latest_result.output
    assert prices_result.exit_code == 0
    assert "ORDERBOOK_DERIVED" in prices_result.output


def test_cli_data_quality_and_ingestion_run_once_work(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_marketdata.db'}"
    runner = CliRunner()

    run_once_result = runner.invoke(
        app,
        [
            "ingestion-run-once",
            "--database-url",
            database_url,
            "--venue",
            "kalshi",
        ],
    )
    quality_result = runner.invoke(
        app,
        [
            "data-quality",
            "--database-url",
            database_url,
            "--market-id",
            "kalshi_market_kxweather_nyc_rain_20260930",
            "--asof",
            "2026-06-16T12:45:00Z",
        ],
    )
    cursors_result = runner.invoke(
        app,
        ["ingestion-cursors", "--database-url", database_url, "--venue", "Kalshi"],
    )

    assert run_once_result.exit_code == 0
    assert "quality_reports_created" in run_once_result.output
    assert quality_result.exit_code == 0
    assert "kalshi_market_kxweather_nyc_rain_20260930" in quality_result.output
    assert cursors_result.exit_code == 0
    assert "cursor_" in cursors_result.output


def test_cli_ingestion_run_once_manual_fetch_without_network_fails(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cli_marketdata.db'}"
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "ingestion-run-once",
            "--database-url",
            database_url,
            "--venue",
            "kalshi",
            "--mode",
            "manual_public_fetch",
        ],
    )

    assert result.exit_code == 1
    assert "requires --allow-network" in result.output
