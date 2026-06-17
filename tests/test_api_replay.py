from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url


def test_api_replay_run_lookup_summary_and_steps_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_replay.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        "/api/v1/replay/runs",
        json={
            "name": "api replay",
            "policy_name": "trust_verdict_v1",
            "start_time": "2026-06-16T12:00:00Z",
            "end_time": "2026-06-16T13:00:00Z",
            "interval_seconds": 3600,
            "market_ids": ["mkt_cpi_yoy_at_least_3pct_2026_09"],
            "max_steps": 10,
            "persist_steps": True,
            "force_recompute_verdicts": True,
            "metadata": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    run_id = payload["run"]["run_id"]
    assert payload["summary"]["total_steps"] == 2

    run_response = client.get(f"/api/v1/replay/runs/{run_id}")
    summary_response = client.get(f"/api/v1/replay/runs/{run_id}/summary")
    steps_response = client.get(f"/api/v1/replay/runs/{run_id}/steps?limit=1&offset=1")

    assert run_response.status_code == 200
    assert run_response.json()["run_id"] == run_id
    assert summary_response.status_code == 200
    assert summary_response.json()["run_id"] == run_id
    assert steps_response.status_code == 200
    assert len(steps_response.json()) == 1


def test_api_replay_returns_400_for_too_many_steps(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_replay.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        "/api/v1/replay/runs",
        json={
            "name": "too many",
            "policy_name": "trust_verdict_v1",
            "start_time": "2026-06-16T12:00:00Z",
            "end_time": "2026-06-16T13:00:00Z",
            "interval_seconds": 3600,
            "market_ids": ["mkt_cpi_yoy_at_least_3pct_2026_09"],
            "max_steps": 1,
            "persist_steps": True,
            "force_recompute_verdicts": False,
            "metadata": {},
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "too_many_steps"
