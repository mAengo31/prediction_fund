"""Data coverage report computation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.dataops.enums import CoverageScopeType
from prediction_desk.dataops.models import DataCoverageReport, dataops_object_id
from prediction_desk.domain.models import Market
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


def compute_market_coverage(
    market_id: str,
    asof_timestamp: datetime,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    repo: PredictionMarketRepository | None = None,
) -> DataCoverageReport:
    if repo is not None:
        return _compute_coverage(
            repo,
            CoverageScopeType.MARKET,
            asof_timestamp,
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
        )
    with session_scope() as session:
        return _compute_coverage(
            PredictionMarketRepository(session),
            CoverageScopeType.MARKET,
            asof_timestamp,
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
        )


def compute_universe_coverage(
    universe_id: str,
    asof_timestamp: datetime,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    repo: PredictionMarketRepository | None = None,
) -> DataCoverageReport:
    if repo is not None:
        return _compute_coverage(
            repo,
            CoverageScopeType.UNIVERSE,
            asof_timestamp,
            universe_id=universe_id,
            start_time=start_time,
            end_time=end_time,
        )
    with session_scope() as session:
        return _compute_coverage(
            PredictionMarketRepository(session),
            CoverageScopeType.UNIVERSE,
            asof_timestamp,
            universe_id=universe_id,
            start_time=start_time,
            end_time=end_time,
        )


def compute_global_coverage(
    asof_timestamp: datetime,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    repo: PredictionMarketRepository | None = None,
) -> DataCoverageReport:
    if repo is not None:
        return _compute_coverage(
            repo,
            CoverageScopeType.GLOBAL,
            asof_timestamp,
            start_time=start_time,
            end_time=end_time,
        )
    with session_scope() as session:
        return _compute_coverage(
            PredictionMarketRepository(session),
            CoverageScopeType.GLOBAL,
            asof_timestamp,
            start_time=start_time,
            end_time=end_time,
        )


def compute_venue_coverage(
    venue_name: str,
    asof_timestamp: datetime,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    repo: PredictionMarketRepository,
) -> DataCoverageReport:
    return _compute_coverage(
        repo,
        CoverageScopeType.VENUE,
        asof_timestamp,
        venue_name=venue_name,
        start_time=start_time,
        end_time=end_time,
    )


def _compute_coverage(
    repo: PredictionMarketRepository,
    scope_type: CoverageScopeType,
    asof_timestamp: datetime,
    *,
    universe_id: str | None = None,
    market_id: str | None = None,
    venue_name: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> DataCoverageReport:
    markets = _markets_for_scope(
        repo,
        scope_type,
        asof_timestamp,
        universe_id=universe_id,
        market_id=market_id,
        venue_name=venue_name,
    )
    total = len(markets)
    rule_count = 0
    orderbook_count = 0
    price_count = 0
    liquidity_count = 0
    quality_count = 0
    stale_count = 0
    quality_scores: list[Decimal] = []
    for market in markets:
        if repo.get_latest_rule_snapshot_asof(market.market_id, asof_timestamp) is not None:
            rule_count += 1
        if repo.get_latest_orderbook_snapshot_asof(market.market_id, asof_timestamp) is not None:
            orderbook_count += 1
        price = repo.get_latest_price_snapshot_asof(market.market_id, asof_timestamp)
        if price is not None:
            price_count += 1
            if (_as_utc(asof_timestamp) - _as_utc(price.available_at)).total_seconds() > 3600:
                stale_count += 1
        if repo.get_latest_liquidity_snapshot_asof(market.market_id, asof_timestamp) is not None:
            liquidity_count += 1
        quality = repo.get_latest_quality_report_asof(market.market_id, asof_timestamp)
        if quality is not None:
            quality_count += 1
            quality_scores.append(Decimal(quality.quality_score))
    missing_rule = total - rule_count
    missing_price = total - price_count
    missing_liquidity = total - liquidity_count
    coverage_score = _coverage_score(
        total,
        rule_count,
        orderbook_count,
        price_count,
        liquidity_count,
        quality_count,
    )
    reason_codes = _coverage_reason_codes(
        total,
        missing_rule,
        missing_price,
        missing_liquidity,
        total - quality_count,
        stale_count,
    )
    report = DataCoverageReport(
        coverage_report_id=dataops_object_id(
            "coverage_report",
            {
                "scope_type": scope_type.value,
                "universe_id": universe_id,
                "market_id": market_id,
                "venue_name": venue_name,
                "asof_timestamp": asof_timestamp,
                "start_time": start_time,
                "end_time": end_time,
                "markets": [market.market_id for market in markets],
            },
        ),
        asof_timestamp=asof_timestamp,
        created_at=datetime.now(tz=UTC),
        scope_type=scope_type,
        universe_id=universe_id,
        market_id=market_id,
        venue_name=venue_name,
        start_time=start_time,
        end_time=end_time,
        total_markets=total,
        markets_with_rules=rule_count,
        markets_with_orderbooks=orderbook_count,
        markets_with_price_snapshots=price_count,
        markets_with_liquidity_snapshots=liquidity_count,
        markets_with_quality_reports=quality_count,
        stale_markets=stale_count,
        missing_rule_markets=missing_rule,
        missing_price_markets=missing_price,
        missing_liquidity_markets=missing_liquidity,
        average_quality_score=(
            sum(quality_scores, Decimal("0")) / Decimal(len(quality_scores))
            if quality_scores
            else None
        ),
        coverage_score=coverage_score,
        reason_codes=reason_codes,
        metadata={"coverage_version": "data_coverage_v1"},
    )
    return repo.save_data_coverage_report(report)


def _markets_for_scope(
    repo: PredictionMarketRepository,
    scope_type: CoverageScopeType,
    asof_timestamp: datetime,
    *,
    universe_id: str | None,
    market_id: str | None,
    venue_name: str | None,
) -> list[Market]:
    if scope_type == CoverageScopeType.MARKET:
        market = repo.get_market(market_id or "")
        return [market] if market is not None else []
    if scope_type == CoverageScopeType.UNIVERSE and universe_id:
        members = repo.list_market_universe_members(
            universe_id=universe_id,
            asof_timestamp=asof_timestamp,
            limit=10000,
        )
        return [market for member in members if (market := repo.get_market(member.market_id))]
    if scope_type == CoverageScopeType.VENUE and venue_name:
        wanted = venue_name.casefold()
        return [
            market
            for market in repo.list_markets(limit=10000)
            if _market_venue_matches(repo, market, wanted)
        ]
    return repo.list_markets(limit=10000)


def _market_venue_matches(
    repo: PredictionMarketRepository,
    market: Market,
    wanted: str,
) -> bool:
    venue = repo.get_venue(market.venue_id)
    values = {market.venue_id.casefold()}
    if venue is not None:
        values.add(venue.name.casefold())
        values.add(venue.venue_id.casefold())
    return wanted in values


def _coverage_score(
    total: int,
    rule_count: int,
    orderbook_count: int,
    price_count: int,
    liquidity_count: int,
    quality_count: int,
) -> int:
    if total == 0:
        return 0
    available = rule_count + orderbook_count + price_count + liquidity_count + quality_count
    expected = total * 5
    return int((Decimal(available) / Decimal(expected) * Decimal(100)).quantize(Decimal("1")))


def _coverage_reason_codes(
    total: int,
    missing_rule: int,
    missing_price: int,
    missing_liquidity: int,
    missing_quality: int,
    stale_count: int,
) -> list[str]:
    if total == 0:
        return ["NO_MARKETS_IN_SCOPE"]
    codes: list[str] = []
    if missing_rule:
        codes.append("MISSING_RULE_SNAPSHOTS")
    if missing_price:
        codes.append("MISSING_PRICE_SNAPSHOTS")
    if missing_liquidity:
        codes.append("MISSING_LIQUIDITY_SNAPSHOTS")
    if missing_quality:
        codes.append("MISSING_QUALITY_REPORTS")
    if stale_count:
        codes.append("STALE_MARKET_DATA")
    if not codes:
        codes.append("COVERAGE_COMPLETE")
    return codes


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
