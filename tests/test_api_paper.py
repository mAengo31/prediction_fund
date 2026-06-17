from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url

MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"


def test_api_paper_simulate_intent_and_run_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_paper.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    policy_response = client.post("/api/v1/paper/policies/default")
    simulate_response = client.post(
        "/api/v1/paper/simulate-intent",
        json={
            "market_id": MARKET_ID,
            "strategy_context": "RESEARCH",
            "side": "BUY",
            "intent_type": "AGGRESSIVE_LIMIT",
            "requested_price": "0.52",
            "requested_size_units": "1",
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "metadata": {},
        },
    )
    orders_response = client.get("/api/v1/paper/orders")
    fills_response = client.get("/api/v1/paper/fills")
    position_response = client.get(f"/api/v1/markets/{MARKET_ID}/paper/position/latest")
    portfolio_response = client.get("/api/v1/paper/portfolio/latest")
    run_response = client.post(
        "/api/v1/paper/runs",
        json={
            "name": "api paper",
            "start_time": "2026-06-16T12:00:00Z",
            "end_time": "2026-06-16T13:00:00Z",
            "interval_seconds": 3600,
            "market_ids": [MARKET_ID],
            "max_orders": 10,
            "initial_cash_simulated": "1000",
            "default_order_size_units": "1",
            "default_intent_type": "RESEARCH_ONLY",
            "default_strategy_context": "RESEARCH",
            "metadata": {},
        },
    )

    assert policy_response.status_code == 200
    assert simulate_response.status_code == 200
    assert simulate_response.json()["order"]["status"] == "FILLED"
    assert orders_response.status_code == 200
    assert fills_response.status_code == 200
    assert position_response.status_code == 200
    assert portfolio_response.status_code == 200
    assert run_response.status_code == 200
    assert run_response.json()["summary"]["total_orders"] == 2


def test_api_paper_order_lookup_works(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_paper_lookup.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        "/api/v1/paper/simulate-intent",
        json={
            "market_id": MARKET_ID,
            "side": "BUY",
            "intent_type": "RESEARCH_ONLY",
            "requested_size_units": "1",
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "metadata": {},
        },
    )
    order_id = response.json()["order"]["paper_order_id"]
    lookup = client.get(f"/api/v1/paper/orders/{order_id}")

    assert response.status_code == 200
    assert lookup.status_code == 200
    assert lookup.json()["paper_order_id"] == order_id

