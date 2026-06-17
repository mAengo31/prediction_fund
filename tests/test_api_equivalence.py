from __future__ import annotations

from pathlib import Path

from prediction_desk.persistence.database import init_db
from tests.api_test_helpers import build_test_client, sqlite_url
from tests.equivalence_helpers import ASOF, KALSHI_RAIN, POLYMARKET_RAIN


def test_api_equivalence_assess_candidates_run_and_classes_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_url = sqlite_url(tmp_path / "api_equivalence.db")
    init_db(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    for venue in ("kalshi", "polymarket"):
        ingest_response = client.post(
            "/api/v1/ingestion/run-once",
            json={"venue_name": venue, "mode": "fixture", "allow_network": False},
        )
        assert ingest_response.status_code == 200

    candidates_response = client.post(
        "/api/v1/equivalence/candidates",
        json={
            "market_ids": [KALSHI_RAIN, POLYMARKET_RAIN],
            "asof_timestamp": ASOF.isoformat(),
            "min_candidate_score": 40,
            "max_pairs": 10,
            "force": False,
        },
    )
    assess_response = client.post(
        "/api/v1/equivalence/assess",
        json={
            "left_market_id": KALSHI_RAIN,
            "right_market_id": POLYMARKET_RAIN,
            "asof_timestamp": ASOF.isoformat(),
            "force": False,
            "config": {},
        },
    )
    assessment_id = assess_response.json()["assessment"]["equivalence_assessment_id"]
    lookup_response = client.get(f"/api/v1/equivalence/assessments/{assessment_id}")
    outcomes_response = client.get(f"/api/v1/equivalence/assessments/{assessment_id}/outcomes")
    list_response = client.get(f"/api/v1/markets/{KALSHI_RAIN}/equivalence")
    run_response = client.post(
        "/api/v1/equivalence/runs",
        json={
            "name": "api equivalence",
            "asof_timestamp": ASOF.isoformat(),
            "market_ids": [KALSHI_RAIN, POLYMARKET_RAIN],
            "min_candidate_score": 40,
            "max_pairs": 10,
            "build_classes": True,
            "force": False,
            "metadata": {},
        },
    )
    classes_response = client.get("/api/v1/equivalence/classes")

    assert candidates_response.status_code == 200
    assert candidates_response.json()
    assert assess_response.status_code == 200
    assert assess_response.json()["assessment"]["overall_score"] >= 70
    assert lookup_response.status_code == 200
    assert outcomes_response.status_code == 200
    assert outcomes_response.json()
    assert list_response.status_code == 200
    assert run_response.status_code == 200
    assert run_response.json()["summary"]["total_assessments"] == 1
    assert classes_response.status_code == 200
    assert classes_response.json()
