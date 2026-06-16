from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from prediction_desk.api.app import create_app
from prediction_desk.examples.sample_markets import SampleMarketBundle, load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository

API_TOKEN = "test-api-token"


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def configure_api_env(
    monkeypatch: MonkeyPatch,
    *,
    database_url: str,
    require_token: bool = False,
) -> None:
    monkeypatch.setenv("APP_ENV", "production" if require_token else "local")
    monkeypatch.setenv("APP_VERSION", "test-version")
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ENABLE_OPENAPI_DOCS", "true")
    monkeypatch.setenv("GIT_COMMIT", "test-commit")
    monkeypatch.setenv("PREDICTION_DESK_API_TOKEN", API_TOKEN)
    monkeypatch.setenv("REQUIRE_API_TOKEN", "true" if require_token else "false")


def build_test_client(
    monkeypatch: MonkeyPatch,
    *,
    database_url: str,
    require_token: bool = False,
) -> TestClient:
    configure_api_env(monkeypatch, database_url=database_url, require_token=require_token)
    return TestClient(create_app())


def load_samples(database_url: str) -> tuple[SampleMarketBundle, ...]:
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        return load_sample_data(repo)
