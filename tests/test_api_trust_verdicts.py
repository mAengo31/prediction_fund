from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, load_samples, sqlite_url


def test_recompute_trust_verdict_creates_and_returns_verdict(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = sqlite_url(tmp_path / "verdicts.db")
    clean, *_ = load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    recompute_response = client.post(
        f"/api/v1/markets/{clean.market.market_id}/trust-verdicts/recompute"
    )
    latest_response = client.get(
        f"/api/v1/markets/{clean.market.market_id}/trust-verdicts/latest"
    )

    assert recompute_response.status_code == 200
    verdict = recompute_response.json()
    assert verdict["market_id"] == clean.market.market_id
    assert verdict["resolution_risk_score"] == 0
    assert verdict["liquidity_risk_score"] == 10
    assert verdict["action"] == "ALLOW"
    assert latest_response.status_code == 200
    assert latest_response.json()["verdict_id"] == verdict["verdict_id"]


def test_latest_trust_verdict_returns_404_when_missing(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "verdicts.db")
    clean, *_ = load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.get(f"/api/v1/markets/{clean.market.market_id}/trust-verdicts/latest")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "trust_verdict_not_found"


def test_recompute_trust_verdict_missing_market_returns_404(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = sqlite_url(tmp_path / "verdicts.db")
    load_samples(database_url)
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.post("/api/v1/markets/does-not-exist/trust-verdicts/recompute")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "market_not_found"
