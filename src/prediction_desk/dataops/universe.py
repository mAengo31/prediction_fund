"""Market universe construction for read-only research dataops."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.dataops.models import (
    MarketUniverseDefinition,
    MarketUniverseMember,
    universe_id,
    universe_member_id,
)
from prediction_desk.domain.models import Event, Market, Venue
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository

DEFAULT_UNIVERSES: tuple[dict[str, Any], ...] = (
    {
        "universe_name": "all_active_prediction_markets_v1",
        "venue_names": [],
        "market_statuses": ["ACTIVE"],
        "metadata": {"fixture_safe": True},
    },
    {
        "universe_name": "kalshi_active_fixture_v1",
        "venue_names": ["kalshi", "Kalshi"],
        "market_statuses": ["ACTIVE"],
        "metadata": {"fixture_safe": True},
    },
    {
        "universe_name": "polymarket_active_fixture_v1",
        "venue_names": ["polymarket", "Polymarket"],
        "market_statuses": ["ACTIVE"],
        "metadata": {"fixture_safe": True},
    },
    {
        "universe_name": "cross_venue_comparable_fixture_v1",
        "venue_names": ["kalshi", "Kalshi", "polymarket", "Polymarket"],
        "market_statuses": ["ACTIVE"],
        "include_market_ids": [
            "kalshi_market_kxweather_nyc_rain_20260930",
            "polymarket_market_0xrainnycsep2026",
        ],
        "metadata": {"fixture_safe": True, "purpose": "cross_venue_comparable"},
    },
)


def create_default_universes_if_missing(
    *,
    repo: PredictionMarketRepository | None = None,
) -> list[MarketUniverseDefinition]:
    if repo is not None:
        return _create_default_universes_if_missing(repo)
    with session_scope() as session:
        return _create_default_universes_if_missing(PredictionMarketRepository(session))


def _create_default_universes_if_missing(
    repo: PredictionMarketRepository,
) -> list[MarketUniverseDefinition]:
    created_at = datetime.now(tz=UTC)
    definitions: list[MarketUniverseDefinition] = []
    for spec in DEFAULT_UNIVERSES:
        name = str(spec["universe_name"])
        version = "v1"
        uid = universe_id(name, version)
        existing = repo.get_market_universe_definition(uid)
        if existing is not None:
            definitions.append(existing)
            continue
        definition = MarketUniverseDefinition(
            universe_id=uid,
            universe_name=name,
            universe_version=version,
            created_at=created_at,
            is_active=True,
            venue_names=_list_spec(spec, "venue_names"),
            categories=_list_spec(spec, "categories"),
            market_statuses=_list_spec(spec, "market_statuses"),
            market_types=_list_spec(spec, "market_types"),
            include_market_ids=_list_spec(spec, "include_market_ids"),
            exclude_market_ids=_list_spec(spec, "exclude_market_ids"),
            title_include_patterns=_list_spec(spec, "title_include_patterns"),
            title_exclude_patterns=_list_spec(spec, "title_exclude_patterns"),
            metadata=_dict_spec(spec, "metadata"),
        )
        definitions.append(repo.save_market_universe_definition(definition))
    return definitions


def build_market_universe(
    universe_id_value: str,
    asof_timestamp: datetime,
    *,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> list[MarketUniverseMember]:
    if repo is not None:
        return _build_market_universe(repo, universe_id_value, asof_timestamp, force=force)
    with session_scope() as session:
        return _build_market_universe(
            PredictionMarketRepository(session),
            universe_id_value,
            asof_timestamp,
            force=force,
        )


def list_universe_members(
    universe_id_value: str,
    *,
    limit: int = 500,
    offset: int = 0,
    repo: PredictionMarketRepository | None = None,
) -> list[MarketUniverseMember]:
    if repo is not None:
        return repo.list_market_universe_members(
            universe_id=universe_id_value, limit=limit, offset=offset
        )
    with session_scope() as session:
        return PredictionMarketRepository(session).list_market_universe_members(
            universe_id=universe_id_value,
            limit=limit,
            offset=offset,
        )


def _build_market_universe(
    repo: PredictionMarketRepository,
    universe_id_value: str,
    asof_timestamp: datetime,
    *,
    force: bool,
) -> list[MarketUniverseMember]:
    definition = repo.get_market_universe_definition(universe_id_value)
    if definition is None:
        raise ValueError("market_universe_not_found")
    members: list[MarketUniverseMember] = []
    for market in repo.list_markets(limit=10000):
        event = repo.get_event(market.event_id)
        venue = repo.get_venue(market.venue_id)
        include, inclusion, exclusion = _evaluate_market(
            repo,
            definition,
            market,
            event,
            venue,
            asof_timestamp,
        )
        if not include:
            continue
        member = MarketUniverseMember(
            universe_member_id=universe_member_id(
                definition.universe_id,
                market.market_id,
                asof_timestamp,
            ),
            universe_id=definition.universe_id,
            market_id=market.market_id,
            venue_id=market.venue_id,
            venue_name=venue.name if venue else None,
            event_id=market.event_id,
            added_at=datetime.now(tz=UTC),
            asof_timestamp=asof_timestamp,
            inclusion_reason_codes=inclusion,
            exclusion_reason_codes=exclusion,
            metadata={"universe_name": definition.universe_name},
        )
        existing = repo.list_market_universe_members(
            universe_id=definition.universe_id,
            market_id=market.market_id,
            asof_timestamp=asof_timestamp,
            limit=1,
        )
        if existing and not force:
            members.append(existing[0])
        else:
            members.append(repo.save_market_universe_member(member))
    return sorted(members, key=lambda item: item.market_id)


def _evaluate_market(
    repo: PredictionMarketRepository,
    definition: MarketUniverseDefinition,
    market: Market,
    event: Event | None,
    venue: Venue | None,
    asof_timestamp: datetime,
) -> tuple[bool, list[str], list[str]]:
    inclusion: list[str] = []
    exclusion: list[str] = []
    if definition.include_market_ids and market.market_id not in definition.include_market_ids:
        exclusion.append("MARKET_NOT_IN_INCLUDE_LIST")
    elif definition.include_market_ids:
        inclusion.append("MARKET_IN_INCLUDE_LIST")
    if market.market_id in definition.exclude_market_ids:
        exclusion.append("MARKET_EXCLUDED")
    if definition.venue_names and not _venue_matches(
        venue, market.venue_id, definition.venue_names
    ):
        exclusion.append("VENUE_NOT_IN_UNIVERSE")
    elif definition.venue_names:
        inclusion.append("VENUE_MATCH")
    if definition.market_statuses and market.status.value not in definition.market_statuses:
        exclusion.append("STATUS_NOT_IN_UNIVERSE")
    elif definition.market_statuses:
        inclusion.append("STATUS_MATCH")
    if definition.market_types and market.market_type.value not in definition.market_types:
        exclusion.append("TYPE_NOT_IN_UNIVERSE")
    elif definition.market_types:
        inclusion.append("TYPE_MATCH")
    category = (event.category if event else None) or ""
    if definition.categories and category not in definition.categories:
        exclusion.append("CATEGORY_NOT_IN_UNIVERSE")
    elif definition.categories:
        inclusion.append("CATEGORY_MATCH")
    title = market.title.casefold()
    if definition.title_include_patterns and not any(
        pattern.casefold() in title for pattern in definition.title_include_patterns
    ):
        exclusion.append("TITLE_INCLUDE_PATTERN_MISSING")
    elif definition.title_include_patterns:
        inclusion.append("TITLE_INCLUDE_PATTERN_MATCH")
    if any(pattern.casefold() in title for pattern in definition.title_exclude_patterns):
        exclusion.append("TITLE_EXCLUDE_PATTERN_MATCH")
    if definition.min_market_data_quality_score is not None:
        quality = repo.get_latest_quality_report_asof(market.market_id, asof_timestamp)
        if quality is None or quality.quality_score < definition.min_market_data_quality_score:
            exclusion.append("QUALITY_BELOW_UNIVERSE_MINIMUM")
        else:
            inclusion.append("QUALITY_MATCH")
    if definition.min_liquidity_depth is not None:
        liquidity = repo.get_latest_liquidity_snapshot_asof(market.market_id, asof_timestamp)
        total_depth = (
            liquidity.total_bid_depth + liquidity.total_ask_depth
            if liquidity is not None
            else Decimal("0")
        )
        if total_depth < definition.min_liquidity_depth:
            exclusion.append("LIQUIDITY_BELOW_UNIVERSE_MINIMUM")
        else:
            inclusion.append("LIQUIDITY_MATCH")
    if not inclusion:
        inclusion.append("DEFAULT_INCLUDE")
    return not exclusion, sorted(set(inclusion)), sorted(set(exclusion))


def _venue_matches(venue: Venue | None, venue_id: str, names: list[str]) -> bool:
    wanted = {name.casefold() for name in names}
    values = {venue_id.casefold()}
    if venue is not None:
        values.add(venue.name.casefold())
        values.add(venue.venue_id.casefold())
    return bool(values & wanted)


def _list_spec(spec: dict[str, Any], key: str) -> list[str]:
    value = spec.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _dict_spec(spec: dict[str, Any], key: str) -> dict[str, Any]:
    value = spec.get(key, {})
    return dict(value) if isinstance(value, dict) else {}
