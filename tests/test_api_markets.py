from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url


def test_sample_market_can_be_listed_and_retrieved(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "markets.db")
    clean, *_ = load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    list_response = client.get("/api/v1/markets")
    market_response = client.get(f"/api/v1/markets/{clean.market.market_id}")
    rule_response = client.get(
        f"/api/v1/markets/{clean.market.market_id}/rule-snapshots/latest"
    )

    assert list_response.status_code == 200
    markets = list_response.json()
    assert len(markets) == 5
    assert {
        "mkt_cpi_yoy_at_least_3pct_2026_09",
        "mkt_candidate_announcement_vague_2026",
        "mkt_rate_cut_rule_change_2026",
        clean.market.market_id,
        "mkt_vague_deadline_before_end_september_2026",
    } == {market["market_id"] for market in markets}
    assert market_response.status_code == 200
    assert market_response.json()["title"] == clean.market.title
    assert rule_response.status_code == 200
    assert rule_response.json()["rule_hash"] == clean.rule_snapshot.rule_hash


def test_market_list_supports_filters_and_pagination(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "markets.db")
    clean, *_ = load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.get(
        "/api/v1/markets",
        params={"status": "ACTIVE", "venue_id": clean.market.venue_id, "limit": 1, "offset": 0},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_missing_market_returns_404(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "markets.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.get("/api/v1/markets/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "market_not_found"
