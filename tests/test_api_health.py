from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import build_test_client, sqlite_url


def test_health_endpoint_is_public_when_auth_required(
    tmp_path: Path, monkeypatch
) -> None:
    client = build_test_client(
        monkeypatch,
        database_url=sqlite_url(tmp_path / "health.db"),
        require_token=True,
    )

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json() == {
        "status": "ok",
        "service": "prediction-desk",
        "version": "test-version",
        "environment": "production",
    }


def test_ready_endpoint_reports_database_availability(tmp_path: Path, monkeypatch) -> None:
    database_url = sqlite_url(tmp_path / "ready.db")
    client = build_test_client(monkeypatch, database_url=database_url)

    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["migrated"] is False


def test_ready_endpoint_returns_503_when_database_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    missing_directory = tmp_path / "missing"
    client = build_test_client(
        monkeypatch,
        database_url=sqlite_url(missing_directory / "ready.db"),
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "database_unreachable"
    assert body["error"]["message"] == "Database is unreachable."
    assert body["error"]["request_id"]
