from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from prediction_desk.api.app import create_app
from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory
from prediction_desk.persistence.orm import Base
from prediction_desk.persistence.repositories import PredictionMarketRepository

pytestmark = pytest.mark.postgres


@pytest.fixture()
def postgres_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")
    return database_url


@pytest.fixture()
def migrated_postgres_url(postgres_database_url: str) -> str:
    _reset_with_migrations(postgres_database_url)
    return postgres_database_url


def test_postgres_repository_roundtrip(migrated_postgres_url: str) -> None:
    engine = build_engine(migrated_postgres_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        clean, _ = load_sample_data(repo)

    with session_factory() as session:
        repo = PredictionMarketRepository(session)
        market = repo.get_market(clean.market.market_id)
        rule_snapshot = repo.get_latest_rule_snapshot(clean.market.market_id)
        orderbook_snapshot = repo.get_latest_orderbook_snapshot(clean.market.market_id)

    assert market is not None
    assert market.market_id == clean.market.market_id
    assert rule_snapshot is not None
    assert rule_snapshot.rule_hash == clean.rule_snapshot.rule_hash
    assert orderbook_snapshot is not None
    assert orderbook_snapshot.snapshot_id == clean.orderbook_snapshot.snapshot_id


def test_postgres_api_market_list_and_recompute(
    migrated_postgres_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine = build_engine(migrated_postgres_url)
    session_factory = build_session_factory(engine)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        clean, _ = load_sample_data(repo)

    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", migrated_postgres_url)
    monkeypatch.setenv("REQUIRE_API_TOKEN", "false")
    monkeypatch.setenv("ENABLE_OPENAPI_DOCS", "true")
    client = TestClient(create_app())

    markets_response = client.get("/api/v1/markets")
    recompute_response = client.post(
        f"/api/v1/markets/{clean.market.market_id}/trust-verdicts/recompute"
    )

    assert markets_response.status_code == 200
    assert any(
        market["market_id"] == clean.market.market_id for market in markets_response.json()
    )
    assert recompute_response.status_code == 200
    assert recompute_response.json()["market_id"] == clean.market.market_id
    assert recompute_response.json()["action"] == "ALLOW"


def _reset_with_migrations(database_url: str) -> None:
    engine = build_engine(database_url)
    Base.metadata.drop_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))

    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
