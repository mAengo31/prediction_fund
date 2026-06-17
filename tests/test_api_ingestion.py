from __future__ import annotations

from pathlib import Path

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url


def test_api_fixture_ingestion_and_mapping_lookup_work(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = sqlite_url(tmp_path / "api_ingestion.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        "/api/v1/ingestion/fixtures/kalshi",
        json={
            "fixture_dir": None,
            "captured_at": None,
            "analyze_rules": True,
            "recompute_verdicts": True,
        },
    )
    markets_response = client.get("/api/v1/markets?venue_id=kalshi")
    mappings_response = client.get("/api/v1/venue-mappings?venue_name=Kalshi")
    runs_response = client.get("/api/v1/ingestion/runs?venue_name=Kalshi")

    assert response.status_code == 200
    assert response.json()["run"]["status"] == "COMPLETED"
    assert markets_response.status_code == 200
    assert any(
        market["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
        for market in markets_response.json()
    )
    assert mappings_response.status_code == 200
    assert mappings_response.json()[0]["external_market_id"] == "KXWEATHER-NYC-RAIN-20260930"
    assert runs_response.status_code == 200
    assert runs_response.json()[0]["ingestion_run_id"] == response.json()["run"]["ingestion_run_id"]


def test_api_public_sample_with_network_disabled_returns_400(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = sqlite_url(tmp_path / "api_ingestion.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        "/api/v1/ingestion/public-sample/kalshi",
        json={
            "limit": 10,
            "allow_network": False,
            "analyze_rules": True,
            "recompute_verdicts": True,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "public_network_disabled"
