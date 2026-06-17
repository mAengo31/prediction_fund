from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url

MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"


def test_api_pretrade_check_run_policy_restriction_and_exposure_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_pretrade.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    policy_response = client.post("/api/v1/pretrade/policies/default")
    check_response = client.post(
        "/api/v1/pretrade/check",
        json={
            "market_id": MARKET_ID,
            "strategy_context": "RESEARCH",
            "side": "BUY",
            "intent_type": "RESEARCH_ONLY",
            "requested_size_units": "1",
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "metadata": {},
        },
    )
    exposure_response = client.post(
        "/api/v1/pretrade/exposures",
        json={
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "source": "MANUAL",
            "market_id": MARKET_ID,
            "event_id": "event_cpi_threshold_2026_09",
            "venue_id": "sample_research_venue",
            "strategy_context": "RESEARCH",
            "market_exposure_units": "0",
            "event_exposure_units": "0",
            "venue_exposure_units": "0",
            "metadata": {},
        },
    )
    restriction_response = client.post(
        "/api/v1/pretrade/restrictions",
        json={
            "restriction_type": "MANUAL_REVIEW",
            "scope_type": "MARKET",
            "market_id": MARKET_ID,
            "reason_code": "API_REVIEW_RULE",
            "metadata": {},
        },
    )
    run_response = client.post(
        "/api/v1/pretrade/runs",
        json={
            "name": "api pretrade",
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "market_ids": [MARKET_ID],
            "max_checks": 10,
            "default_requested_size_units": "1",
            "strategy_context": "RESEARCH",
            "intent_type": "RESEARCH_ONLY",
            "metadata": {},
        },
    )
    latest_response = client.get(f"/api/v1/markets/{MARKET_ID}/pretrade/latest")
    decisions_response = client.get("/api/v1/pretrade/decisions")
    policies_response = client.get("/api/v1/pretrade/policies")
    restrictions_response = client.get("/api/v1/pretrade/restrictions")
    exposures_response = client.get("/api/v1/pretrade/exposures")

    assert policy_response.status_code == 200
    assert check_response.status_code == 200
    assert check_response.json()["decision"]["market_id"] == MARKET_ID
    assert exposure_response.status_code == 200
    assert restriction_response.status_code == 200
    assert run_response.status_code == 200
    assert run_response.json()["summary"]["total_decisions"] == 1
    assert latest_response.status_code == 200
    assert decisions_response.status_code == 200
    assert policies_response.status_code == 200
    assert restrictions_response.status_code == 200
    assert exposures_response.status_code == 200


def test_api_pretrade_decision_lookup_works(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_pretrade_lookup.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    check_response = client.post(
        "/api/v1/pretrade/check-market/" + MARKET_ID,
        json={
            "asof_timestamp": "2026-06-16T12:00:00Z",
            "strategy_context": "RESEARCH",
            "requested_size_units": "1",
        },
    )
    decision_id = check_response.json()["decision"]["pretrade_decision_id"]
    lookup_response = client.get(f"/api/v1/pretrade/decisions/{decision_id}")

    assert check_response.status_code == 200
    assert lookup_response.status_code == 200
    assert lookup_response.json()["pretrade_decision_id"] == decision_id
