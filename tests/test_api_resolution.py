from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url


def test_api_analyze_latest_and_resolution_latest_work(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_resolution.db")
    clean, *_ = load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    missing_response = client.get(
        f"/api/v1/markets/{clean.market.market_id}/resolution/latest"
    )
    analyze_response = client.post(
        f"/api/v1/markets/{clean.market.market_id}/resolution/analyze-latest"
    )
    latest_response = client.get(
        f"/api/v1/markets/{clean.market.market_id}/resolution/latest"
    )
    snapshot_response = client.get(
        f"/api/v1/rule-snapshots/{clean.rule_snapshot.rule_snapshot_id}/resolution"
    )

    assert missing_response.status_code == 404
    assert missing_response.json()["error"]["code"] == "resolution_analysis_not_found"
    assert analyze_response.status_code == 200
    analysis = analyze_response.json()
    assert analysis["market"]["market_id"] == clean.market.market_id
    assert analysis["predicate"]["parse_status"] == "PARSED"
    assert latest_response.status_code == 200
    assert (
        latest_response.json()["predicate"]["predicate_id"]
        == analysis["predicate"]["predicate_id"]
    )
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["ambiguity_assessment"]["overall_score"] == 0


def test_api_diff_latest_rule_snapshots_works(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_resolution.db")
    *_, rule_change = load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post(
        f"/api/v1/markets/{rule_change.market.market_id}/rule-snapshots/diff-latest"
    )

    assert response.status_code == 200
    diff = response.json()
    assert diff["market_id"] == rule_change.market.market_id
    assert diff["resolution_source_changed"] is True
    assert "RESOLUTION_SOURCE_CHANGED" in diff["semantic_change_flags"]
    assert "DEADLINE_CHANGED" in diff["semantic_change_flags"]


def test_api_resolution_missing_market_returns_404(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "api_resolution.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post("/api/v1/markets/does-not-exist/resolution/analyze-latest")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "market_not_found"
