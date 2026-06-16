from __future__ import annotations

from pathlib import Path

from tests.api_test_helpers import API_TOKEN, build_test_client, sqlite_url


def test_protected_endpoint_rejects_missing_token(tmp_path: Path, monkeypatch) -> None:
    client = build_test_client(
        monkeypatch,
        database_url=sqlite_url(tmp_path / "auth.db"),
        require_token=True,
    )

    response = client.get("/version")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"
    assert body["error"]["message"] == "Unauthorized."
    assert body["error"]["request_id"]
    assert response.headers["x-request-id"] == body["error"]["request_id"]


def test_protected_endpoint_rejects_invalid_token(tmp_path: Path, monkeypatch) -> None:
    client = build_test_client(
        monkeypatch,
        database_url=sqlite_url(tmp_path / "auth.db"),
        require_token=True,
    )

    response = client.get("/version", headers={"Authorization": "Bearer wrong-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_protected_endpoint_accepts_valid_token(tmp_path: Path, monkeypatch) -> None:
    client = build_test_client(
        monkeypatch,
        database_url=sqlite_url(tmp_path / "auth.db"),
        require_token=True,
    )

    response = client.get("/version", headers={"Authorization": f"Bearer {API_TOKEN}"})

    assert response.status_code == 200
    assert response.json() == {
        "service": "prediction-desk",
        "version": "test-version",
        "commit": "test-commit",
        "environment": "production",
    }
