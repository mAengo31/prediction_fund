from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.dataops.models import MarketUniverseDefinition
from prediction_desk.dataops.universe import (
    build_market_universe,
    create_default_universes_if_missing,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository
from tests.paper_helpers import loaded_repo

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_default_universes_created_idempotently(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "dataops_universes.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        first = create_default_universes_if_missing(repo=repo)
        second = create_default_universes_if_missing(repo=repo)

    assert [item.universe_id for item in first] == [item.universe_id for item in second]
    assert len(first) >= 4


def test_universe_builder_filters_titles_and_exclusions(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "dataops_universe_filters.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        universe = MarketUniverseDefinition(
            universe_id="market_universe_weather_no_candidate",
            universe_name="weather_no_candidate",
            universe_version="v1",
            created_at=ASOF,
            is_active=True,
            venue_names=[],
            categories=[],
            market_statuses=["ACTIVE"],
            market_types=[],
            include_market_ids=[],
            exclude_market_ids=["mkt_candidate_announcement_vague_2026"],
            title_include_patterns=["rain"],
            title_exclude_patterns=["candidate"],
            min_market_data_quality_score=None,
            min_liquidity_depth=None,
            metadata={},
        )
        repo.save_market_universe_definition(universe)
        members = build_market_universe(universe.universe_id, ASOF, repo=repo)

    market_ids = {member.market_id for member in members}
    assert "mkt_sfo_rain_2026_09_01" in market_ids
    assert "mkt_candidate_announcement_vague_2026" not in market_ids


def test_universe_builder_can_filter_by_liquidity_asof(tmp_path) -> None:
    factory = loaded_repo(tmp_path, "dataops_universe_liquidity.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        universe = MarketUniverseDefinition(
            universe_id="market_universe_liquid",
            universe_name="liquid",
            universe_version="v1",
            created_at=ASOF,
            is_active=True,
            venue_names=[],
            categories=[],
            market_statuses=["ACTIVE"],
            market_types=[],
            include_market_ids=[],
            exclude_market_ids=[],
            title_include_patterns=[],
            title_exclude_patterns=[],
            min_market_data_quality_score=None,
            min_liquidity_depth=Decimal("1"),
            metadata={},
        )
        repo.save_market_universe_definition(universe)
        members = build_market_universe(universe.universe_id, ASOF, repo=repo)

    assert {member.market_id for member in members} == {"mkt_cpi_yoy_at_least_3pct_2026_09"}
