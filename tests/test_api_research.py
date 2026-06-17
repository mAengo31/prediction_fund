from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url
from tests.paper_helpers import MARKET_ID


def test_api_research_closed_loop_workflow(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_research.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    defaults = client.post("/api/v1/research/strategies/default")
    features = client.post(
        "/api/v1/research/features/build",
        json={
            "market_id": MARKET_ID,
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "force": True,
        },
    )
    signals = client.post(
        "/api/v1/research/signals/generate",
        json={
            "market_id": MARKET_ID,
            "asof_timestamp": "2026-06-16T12:00:00Z",
        },
    )
    proposals = client.post(
        "/api/v1/research/proposals/generate",
        json={
            "market_id": MARKET_ID,
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "strategy_ids": ["research_strategy_baseline_research_only_v1"],
        },
    )
    proposal_id = proposals.json()[0]["proposal_id"]
    trace = client.post(
        f"/api/v1/research/proposals/{proposal_id}/evaluate",
        json={"enable_paper_simulation": False, "paper_policy_id": None},
    )
    traces = client.get("/api/v1/research/traces", params={"market_id": MARKET_ID})
    latest = client.get(f"/api/v1/markets/{MARKET_ID}/research/latest")

    assert defaults.status_code == 200
    assert features.status_code == 200
    assert signals.status_code == 200
    assert proposals.status_code == 200
    assert trace.status_code == 200
    assert trace.json()["pretrade_action"] == "ALLOW"
    assert traces.status_code == 200
    assert latest.status_code == 200
    assert latest.json()["signals"]


def test_api_research_run_summary_and_attribution_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_research_run.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    run = client.post(
        "/api/v1/research/runs",
        json={
            "name": "api research",
            "start_time": "2026-06-16T12:00:00Z",
            "end_time": "2026-06-16T12:00:00Z",
            "interval_seconds": 3600,
            "strategy_ids": ["research_strategy_baseline_research_only_v1"],
            "market_ids": [MARKET_ID],
            "max_steps": 10,
            "max_proposals": 10,
            "enable_paper_simulation": False,
            "initial_cash_simulated": "1000",
            "metadata": {},
        },
    )
    run_id = run.json()["run"]["research_run_id"]
    summary = client.get(f"/api/v1/research/runs/{run_id}/summary")
    attribution = client.get(f"/api/v1/research/runs/{run_id}/attribution")
    runs = client.get("/api/v1/research/runs")

    assert run.status_code == 200
    assert run.json()["summary"]["total_proposals"] == 1
    assert summary.status_code == 200
    assert attribution.status_code == 200
    assert runs.status_code == 200

