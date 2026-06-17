from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url


def test_api_dataops_defaults_collection_coverage_and_gaps_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_dataops.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    defaults = client.post("/api/v1/dataops/defaults")
    universes = client.get("/api/v1/dataops/universes")
    plans = client.get("/api/v1/dataops/collection-plans")
    collection = client.post(
        "/api/v1/dataops/collection/run-once",
        json={"venue_names": ["kalshi"], "mode": "FIXTURE", "allow_network": False},
    )
    coverage = client.post(
        "/api/v1/dataops/coverage/compute",
        json={"scope_type": "GLOBAL", "asof_timestamp": "2026-06-16T12:00:00Z"},
    )
    gaps = client.post(
        "/api/v1/dataops/gaps/detect",
        json={"scope_type": "GLOBAL", "asof_timestamp": "2026-06-16T12:00:00Z"},
    )

    assert defaults.status_code == 200
    assert len(defaults.json()["universes"]) >= 4
    assert universes.status_code == 200
    assert plans.status_code == 200
    assert collection.status_code == 200
    assert collection.json()["run"]["allow_network"] is False
    assert coverage.status_code == 200
    assert coverage.json()["total_markets"] >= 1
    assert gaps.status_code == 200
    assert isinstance(gaps.json(), list)


def test_api_dataops_backfill_unsupported_endpoint_workflow(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_dataops_backfill.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    created = client.post(
        "/api/v1/dataops/backfill/jobs",
        json={
            "venue_name": "kalshi",
            "market_ids": ["kalshi_market_kxweather_nyc_rain_20260930"],
            "endpoint_types": ["ORDERBOOK"],
            "start_time": "2026-06-16T11:00:00Z",
            "end_time": "2026-06-16T12:00:00Z",
            "allow_network": False,
        },
    )
    job_id = created.json()["backfill_job_id"]
    run = client.post(f"/api/v1/dataops/backfill/jobs/{job_id}/run")
    segments = client.get(f"/api/v1/dataops/backfill/jobs/{job_id}/segments")

    assert created.status_code == 200
    assert run.status_code == 200
    assert segments.status_code == 200
    assert segments.json()[0]["status"] == "SKIPPED_UNSUPPORTED"
