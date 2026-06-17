from __future__ import annotations

from pathlib import Path

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url


def test_api_market_data_latest_prices_and_liquidity_work(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = sqlite_url(tmp_path / "api_marketdata.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    run_response = client.post(
        "/api/v1/ingestion/run-once",
        json={
            "venue_name": "kalshi",
            "mode": "fixture",
            "limit": 10,
            "allow_network": False,
            "analyze_rules": True,
            "recompute_verdicts": True,
            "derive_market_data": True,
            "compute_quality": True,
            "metadata": {},
        },
    )
    market_id = "kalshi_market_kxweather_nyc_rain_20260930"
    latest_response = client.get(f"/api/v1/markets/{market_id}/market-data/latest")
    prices_response = client.get(f"/api/v1/markets/{market_id}/market-data/prices")
    liquidity_response = client.get(f"/api/v1/markets/{market_id}/market-data/liquidity")

    assert run_response.status_code == 200
    assert latest_response.status_code == 200
    assert latest_response.json()["price_snapshot"] is not None
    assert prices_response.status_code == 200
    assert len(prices_response.json()) == 3
    assert liquidity_response.status_code == 200
    assert len(liquidity_response.json()) == 3


def test_api_data_quality_recompute_and_latest_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_marketdata.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)
    market_id = "kalshi_market_kxweather_nyc_rain_20260930"

    client.post(
        "/api/v1/ingestion/run-once",
        json={
            "venue_name": "kalshi",
            "mode": "fixture",
            "limit": 10,
            "allow_network": False,
            "analyze_rules": True,
            "recompute_verdicts": True,
            "derive_market_data": True,
            "compute_quality": False,
            "metadata": {},
        },
    )
    recompute_response = client.post(
        f"/api/v1/markets/{market_id}/data-quality/recompute",
        json={
            "asof_timestamp": "2026-06-16T12:45:00Z",
            "freshness_threshold_seconds": 3600,
            "wide_spread_threshold": "0.10",
        },
    )
    latest_response = client.get(
        f"/api/v1/markets/{market_id}/data-quality/latest"
        "?asof_timestamp=2026-06-16T12:45:00Z"
    )

    assert recompute_response.status_code == 200
    assert recompute_response.json()["market_id"] == market_id
    assert latest_response.status_code == 200
    assert latest_response.json()["quality_report_id"] == recompute_response.json()[
        "quality_report_id"
    ]


def test_api_market_data_derive_endpoint_works(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_marketdata.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)
    market_id = "kalshi_market_kxweather_nyc_rain_20260930"

    ingest_response = client.post(
        "/api/v1/ingestion/fixtures/kalshi",
        json={
            "fixture_dir": None,
            "captured_at": None,
            "analyze_rules": True,
            "recompute_verdicts": True,
        },
    )
    derive_response = client.post(f"/api/v1/markets/{market_id}/market-data/derive")

    assert ingest_response.status_code == 200
    assert derive_response.status_code == 200
    assert derive_response.json()["market_id"] == market_id


def test_api_ingestion_run_once_and_cursors_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_marketdata.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        "/api/v1/ingestion/run-once",
        json={
            "venue_name": "kalshi",
            "mode": "fixture",
            "limit": 10,
            "allow_network": False,
            "analyze_rules": True,
            "recompute_verdicts": True,
            "derive_market_data": True,
            "compute_quality": True,
            "metadata": {"test": True},
        },
    )
    cursors_response = client.get("/api/v1/ingestion/cursors?venue_name=Kalshi")

    assert response.status_code == 200
    assert response.json()["ingestion"]["run"]["status"] == "COMPLETED"
    assert response.json()["price_snapshots_created"] == 3
    assert cursors_response.status_code == 200
    assert cursors_response.json()
