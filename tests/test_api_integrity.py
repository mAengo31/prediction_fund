from __future__ import annotations

from pathlib import Path

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url


def test_api_integrity_analyze_latest_and_lists_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_integrity.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)
    market_id = "kalshi_market_kxweather_nyc_rain_20260930"

    ingest_response = client.post(
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
    analyze_response = client.post(
        f"/api/v1/markets/{market_id}/integrity/analyze",
        json={"asof_timestamp": "2026-06-16T12:45:00Z", "force": False, "thresholds": {}},
    )
    latest_response = client.get(
        f"/api/v1/markets/{market_id}/integrity/latest"
        "?asof_timestamp=2026-06-16T12:45:00Z"
    )
    signals_response = client.get(f"/api/v1/markets/{market_id}/integrity/signals")
    assessments_response = client.get(f"/api/v1/markets/{market_id}/integrity/assessments")

    assert ingest_response.status_code == 200
    assert analyze_response.status_code == 200
    assert analyze_response.json()["assessment"]["market_id"] == market_id
    assert latest_response.status_code == 200
    assert latest_response.json()["integrity_assessment_id"] == analyze_response.json()[
        "assessment"
    ]["integrity_assessment_id"]
    assert signals_response.status_code == 200
    assert signals_response.json()
    assert assessments_response.status_code == 200
    assert assessments_response.json()


def test_api_integrity_batch_analyze_and_run_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_integrity_run.db")
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
            "compute_quality": True,
            "metadata": {},
        },
    )
    analyze_response = client.post(
        "/api/v1/integrity/analyze",
        json={
            "market_ids": [market_id],
            "asof_timestamp": "2026-06-16T12:45:00Z",
            "force": False,
            "thresholds": {},
            "metadata": {},
        },
    )
    run_response = client.post(
        "/api/v1/integrity/runs",
        json={
            "name": "api integrity run",
            "asof_timestamp": "2026-06-16T12:45:00Z",
            "market_ids": [market_id],
            "max_steps": 10,
            "force": False,
            "thresholds": {},
            "metadata": {},
        },
    )
    run_id = run_response.json()["run"]["integrity_run_id"]
    lookup_response = client.get(f"/api/v1/integrity/runs/{run_id}")
    summary_response = client.get(f"/api/v1/integrity/runs/{run_id}/summary")

    assert analyze_response.status_code == 200
    assert analyze_response.json()[0]["market_id"] == market_id
    assert run_response.status_code == 200
    assert run_response.json()["summary"]["total_assessments"] == 1
    assert lookup_response.status_code == 200
    assert summary_response.status_code == 200


def test_api_integrity_run_rejects_too_many_steps(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_integrity_guardrail.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

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
            "compute_quality": True,
            "metadata": {},
        },
    )
    response = client.post(
        "/api/v1/integrity/runs",
        json={
            "start_time": "2026-06-16T12:00:00Z",
            "end_time": "2026-06-16T13:00:00Z",
            "interval_seconds": 3600,
            "max_steps": 1,
            "thresholds": {},
            "metadata": {},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "too_many_integrity_steps"
