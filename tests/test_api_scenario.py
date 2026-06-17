from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url

SCENARIO_MARKET_ID = "mkt_sfo_rain_2026_09_01"


def test_api_scenario_seed_import_latest_and_run_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_scenario.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    seed = client.post(
        "/api/v1/scenario/seeds/build",
        json={"market_id": SCENARIO_MARKET_ID, "asof_timestamp": "2026-06-16T12:00:00Z"},
    )
    artifacts = client.post(
        "/api/v1/scenario/import-fixtures",
        json={
            "market_ids": [SCENARIO_MARKET_ID],
            "asof_timestamp": "2026-06-16T12:00:00Z",
        },
    )
    artifact_id = artifacts.json()[0]["scenario_artifact_id"]
    feature = client.post(f"/api/v1/scenario/artifacts/{artifact_id}/normalize")
    latest = client.get(
        f"/api/v1/markets/{SCENARIO_MARKET_ID}/scenario/latest",
        params={"asof_timestamp": "2026-06-16T12:00:00Z"},
    )
    run = client.post(
        "/api/v1/scenario/runs",
        json={
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "market_ids": [SCENARIO_MARKET_ID],
            "mode": "IMPORT_FIXTURES",
            "max_items": 10,
        },
    )

    assert seed.status_code == 200
    assert artifacts.status_code == 200
    assert feature.status_code == 200
    assert latest.status_code == 200
    assert latest.json()["market_id"] == SCENARIO_MARKET_ID
    assert run.status_code == 200
    assert run.json()["summary"]["total_features"] >= 1
