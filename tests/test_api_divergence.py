from __future__ import annotations

from pathlib import Path

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN
from tests.test_divergence_service import DIVERGENCE_ASOF


def test_api_divergence_analyze_run_and_latest_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_divergence.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    for venue in ("kalshi", "polymarket"):
        assert client.post(
            "/api/v1/ingestion/run-once",
            json={"venue_name": venue, "mode": "fixture", "allow_network": False},
        ).status_code == 200

    assess_response = client.post(
        "/api/v1/equivalence/assess",
        json={
            "left_market_id": KALSHI_RAIN,
            "right_market_id": POLYMARKET_RAIN,
            "asof_timestamp": DIVERGENCE_ASOF.isoformat(),
            "force": False,
            "config": {},
        },
    )
    assessment_id = assess_response.json()["assessment"]["equivalence_assessment_id"]
    analyze_response = client.post(
        "/api/v1/divergence/analyze",
        json={
            "equivalence_assessment_id": assessment_id,
            "asof_timestamp": DIVERGENCE_ASOF.isoformat(),
            "force": False,
            "config": {},
        },
    )
    run_response = client.post(
        "/api/v1/divergence/runs",
        json={
            "name": "api divergence",
            "asof_timestamp": DIVERGENCE_ASOF.isoformat(),
            "equivalence_assessment_ids": [assessment_id],
            "max_pairs": 10,
            "force": False,
            "config": {},
            "metadata": {},
        },
    )
    latest_response = client.get(f"/api/v1/markets/{KALSHI_RAIN}/divergence/latest")
    signals_response = client.get("/api/v1/divergence/signals")
    assessments_response = client.get("/api/v1/divergence/assessments")
    nested_response = client.post(
        f"/api/v1/equivalence/assessments/{assessment_id}/divergence/analyze",
        json={"asof_timestamp": DIVERGENCE_ASOF.isoformat(), "force": False, "config": {}},
    )

    assert analyze_response.status_code == 200
    assert analyze_response.json()[0]["assessment"]["status"] == "MATERIAL_DIVERGENCE"
    assert run_response.status_code == 200
    assert run_response.json()["summary"]["total_assessments"] == 1
    assert latest_response.status_code == 200
    assert signals_response.status_code == 200
    assert assessments_response.status_code == 200
    assert nested_response.status_code == 200


def test_api_divergence_analyze_requires_market_or_assessment(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_divergence_bad_request.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post("/api/v1/divergence/analyze", json={})

    assert response.status_code == 400

