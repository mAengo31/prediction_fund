"""Build deterministic point-in-time market feature snapshots."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from prediction_desk.integrity.models import (
    MarketFeatureSnapshot,
    compute_feature_input_hash,
)
from prediction_desk.marketdata.models import MarketLiquiditySnapshot, MarketPriceSnapshot

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


def build_market_feature_snapshot(
    market_id: str,
    asof_timestamp: datetime,
    lookback_seconds: int = 3600,
    freshness_threshold_seconds: int = 3600,
    *,
    repo: PredictionMarketRepository,
) -> MarketFeatureSnapshot:
    """Build an as-of-safe feature snapshot from persisted canonical data."""

    del freshness_threshold_seconds
    generated_at = datetime.now(tz=UTC)
    latest_price = repo.get_latest_price_snapshot_asof(market_id, asof_timestamp)
    previous_price = _previous_price_snapshot(
        repo,
        market_id,
        asof_timestamp,
        latest_price,
        lookback_seconds,
    )
    latest_liquidity = repo.get_latest_liquidity_snapshot_asof(market_id, asof_timestamp)
    previous_liquidity = _previous_liquidity_snapshot(
        repo,
        market_id,
        asof_timestamp,
        latest_liquidity,
        lookback_seconds,
    )
    quality_report = repo.get_latest_quality_report_asof(market_id, asof_timestamp)
    rule_snapshot = repo.get_latest_rule_snapshot_asof(market_id, asof_timestamp)
    rule_diff = repo.get_latest_rule_snapshot_diff_asof(market_id, asof_timestamp)
    current_price = _price_value(latest_price)
    previous_price_value = _price_value(previous_price)
    current_mid = latest_price.mid if latest_price else None
    previous_mid = previous_price.mid if previous_price else None
    if current_mid is None and latest_liquidity is not None:
        current_mid = latest_liquidity.mid_price
    if previous_mid is None and previous_liquidity is not None:
        previous_mid = previous_liquidity.mid_price

    total_bid_depth = latest_liquidity.total_bid_depth if latest_liquidity else None
    total_ask_depth = latest_liquidity.total_ask_depth if latest_liquidity else None
    total_depth = _sum_decimal(total_bid_depth, total_ask_depth)
    previous_total_depth = (
        _sum_decimal(previous_liquidity.total_bid_depth, previous_liquidity.total_ask_depth)
        if previous_liquidity is not None
        else None
    )
    freshness_seconds = _freshness_seconds(asof_timestamp, latest_price, latest_liquidity)
    rule_change_age_seconds = (
        _seconds_between(asof_timestamp, rule_diff.created_at) if rule_diff is not None else None
    )
    rule_changed_recently = (
        rule_change_age_seconds is not None
        and 0 <= rule_change_age_seconds <= lookback_seconds
    )

    feature = MarketFeatureSnapshot(
        feature_snapshot_id="pending",
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=generated_at,
        available_at=asof_timestamp,
        latest_price_snapshot_id=latest_price.price_snapshot_id if latest_price else None,
        previous_price_snapshot_id=(
            previous_price.price_snapshot_id if previous_price else None
        ),
        latest_liquidity_snapshot_id=(
            latest_liquidity.liquidity_snapshot_id if latest_liquidity else None
        ),
        previous_liquidity_snapshot_id=(
            previous_liquidity.liquidity_snapshot_id if previous_liquidity else None
        ),
        latest_quality_report_id=(
            quality_report.quality_report_id if quality_report else None
        ),
        latest_rule_snapshot_id=rule_snapshot.rule_snapshot_id if rule_snapshot else None,
        latest_rule_snapshot_hash=rule_snapshot.rule_hash if rule_snapshot else None,
        latest_rule_diff_id=rule_diff.diff_id if rule_diff else None,
        price=current_price,
        bid=latest_price.bid if latest_price else None,
        ask=latest_price.ask if latest_price else None,
        mid=current_mid,
        spread=latest_liquidity.spread if latest_liquidity else None,
        spread_bps=latest_liquidity.spread_bps if latest_liquidity else None,
        total_bid_depth=total_bid_depth,
        total_ask_depth=total_ask_depth,
        total_depth=total_depth,
        book_imbalance=latest_liquidity.book_imbalance if latest_liquidity else None,
        is_empty_book=latest_liquidity.is_empty_book if latest_liquidity else False,
        is_crossed_book=latest_liquidity.is_crossed_book if latest_liquidity else False,
        has_missing_bid_or_ask=(
            latest_liquidity is not None
            and not latest_liquidity.is_empty_book
            and (latest_liquidity.best_bid is None or latest_liquidity.best_ask is None)
        ),
        market_data_quality_score=quality_report.quality_score if quality_report else None,
        market_data_quality_reason_codes=(
            list(quality_report.reason_codes) if quality_report else []
        ),
        freshness_seconds=freshness_seconds,
        price_change_abs=_difference(current_price, previous_price_value),
        price_change_pct=_pct_change(current_price, previous_price_value),
        mid_change_abs=_difference(current_mid, previous_mid),
        spread_change_abs=_difference(
            latest_liquidity.spread if latest_liquidity else None,
            previous_liquidity.spread if previous_liquidity else None,
        ),
        depth_change_pct=_pct_change(total_depth, previous_total_depth),
        rule_changed_recently=rule_changed_recently,
        rule_change_age_seconds=rule_change_age_seconds,
        input_hash="pending",
        metadata={
            "feature_version": "market_feature_snapshot_v1",
            "lookback_seconds": lookback_seconds,
        },
    )
    input_hash = compute_feature_input_hash(feature)
    return feature.model_copy(
        update={
            "feature_snapshot_id": f"feature_{input_hash[:24]}",
            "input_hash": input_hash,
        }
    )


def _previous_price_snapshot(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
    latest: MarketPriceSnapshot | None,
    lookback_seconds: int,
) -> MarketPriceSnapshot | None:
    if latest is None:
        return None
    lookback_asof = asof_timestamp - timedelta(seconds=lookback_seconds)
    lookback_snapshot = repo.get_latest_price_snapshot_asof(market_id, lookback_asof)
    if (
        lookback_snapshot is not None
        and lookback_snapshot.price_snapshot_id != latest.price_snapshot_id
    ):
        return lookback_snapshot
    snapshots = repo.list_price_snapshots(market_id, end_time=asof_timestamp, limit=10000)
    prior = [
        snapshot
        for snapshot in snapshots
        if snapshot.price_snapshot_id != latest.price_snapshot_id
    ]
    return prior[-1] if prior else None


def _previous_liquidity_snapshot(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
    latest: MarketLiquiditySnapshot | None,
    lookback_seconds: int,
) -> MarketLiquiditySnapshot | None:
    if latest is None:
        return None
    lookback_asof = asof_timestamp - timedelta(seconds=lookback_seconds)
    lookback_snapshot = repo.get_latest_liquidity_snapshot_asof(market_id, lookback_asof)
    if (
        lookback_snapshot is not None
        and lookback_snapshot.liquidity_snapshot_id != latest.liquidity_snapshot_id
    ):
        return lookback_snapshot
    snapshots = repo.list_liquidity_snapshots(market_id, end_time=asof_timestamp, limit=10000)
    prior = [
        snapshot
        for snapshot in snapshots
        if snapshot.liquidity_snapshot_id != latest.liquidity_snapshot_id
    ]
    return prior[-1] if prior else None


def _price_value(snapshot: MarketPriceSnapshot | None) -> Decimal | None:
    if snapshot is None:
        return None
    return snapshot.price if snapshot.price is not None else snapshot.mid


def _difference(current: Decimal | None, previous: Decimal | None) -> Decimal | None:
    if current is None or previous is None:
        return None
    return current - previous


def _pct_change(current: Decimal | None, previous: Decimal | None) -> Decimal | None:
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous


def _sum_decimal(first: Decimal | None, second: Decimal | None) -> Decimal | None:
    if first is None and second is None:
        return None
    return (first or Decimal("0")) + (second or Decimal("0"))


def _freshness_seconds(
    asof_timestamp: datetime,
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
) -> int | None:
    candidates = [
        _as_utc(snapshot.available_at)
        for snapshot in (price_snapshot, liquidity_snapshot)
        if snapshot is not None
    ]
    if not candidates:
        return None
    return int((_as_utc(asof_timestamp) - max(candidates)).total_seconds())


def _seconds_between(later: datetime, earlier: datetime) -> int:
    return int((_as_utc(later) - _as_utc(earlier)).total_seconds())


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
