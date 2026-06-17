"""Data gap detection from coverage and as-of market state."""

from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.dataops.coverage import _markets_for_scope
from prediction_desk.dataops.enums import CoverageScopeType, DataGapSeverity, DataGapType
from prediction_desk.dataops.models import DataCoverageReport, DataGap, dataops_object_id
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


def detect_data_gaps(
    scope: CoverageScopeType | str,
    asof_timestamp: datetime,
    *,
    universe_id: str | None = None,
    market_id: str | None = None,
    venue_name: str | None = None,
    expected_cadence_seconds: int | None = None,
    coverage_report: DataCoverageReport | None = None,
    repo: PredictionMarketRepository | None = None,
) -> list[DataGap]:
    scope_type = scope if isinstance(scope, CoverageScopeType) else CoverageScopeType(str(scope))
    if repo is not None:
        return _detect_data_gaps(
            repo,
            scope_type,
            asof_timestamp,
            universe_id=universe_id,
            market_id=market_id,
            venue_name=venue_name,
            expected_cadence_seconds=expected_cadence_seconds,
            coverage_report=coverage_report,
        )
    with session_scope() as session:
        return _detect_data_gaps(
            PredictionMarketRepository(session),
            scope_type,
            asof_timestamp,
            universe_id=universe_id,
            market_id=market_id,
            venue_name=venue_name,
            expected_cadence_seconds=expected_cadence_seconds,
            coverage_report=coverage_report,
        )


def _detect_data_gaps(
    repo: PredictionMarketRepository,
    scope_type: CoverageScopeType,
    asof_timestamp: datetime,
    *,
    universe_id: str | None,
    market_id: str | None,
    venue_name: str | None,
    expected_cadence_seconds: int | None,
    coverage_report: DataCoverageReport | None,
) -> list[DataGap]:
    markets = _markets_for_scope(
        repo,
        scope_type,
        asof_timestamp,
        universe_id=universe_id,
        market_id=market_id,
        venue_name=venue_name,
    )
    gaps: list[DataGap] = []
    for market in markets:
        venue = repo.get_venue(market.venue_id)
        market_venue_name = venue.name if venue else market.venue_id
        if repo.get_latest_rule_snapshot_asof(market.market_id, asof_timestamp) is None:
            gaps.append(
                _gap(
                    coverage_report,
                    market.market_id,
                    market_venue_name,
                    DataGapType.MISSING_RULE_SNAPSHOT,
                    DataGapSeverity.ERROR,
                    asof_timestamp,
                    expected_cadence_seconds,
                    "MISSING_RULE_SNAPSHOT",
                )
            )
        if repo.get_latest_orderbook_snapshot_asof(market.market_id, asof_timestamp) is None:
            gaps.append(
                _gap(
                    coverage_report,
                    market.market_id,
                    market_venue_name,
                    DataGapType.MISSING_ORDERBOOK,
                    DataGapSeverity.WARNING,
                    asof_timestamp,
                    expected_cadence_seconds,
                    "MISSING_ORDERBOOK",
                )
            )
        price = repo.get_latest_price_snapshot_asof(market.market_id, asof_timestamp)
        if price is None:
            gaps.append(
                _gap(
                    coverage_report,
                    market.market_id,
                    market_venue_name,
                    DataGapType.MISSING_PRICE_SNAPSHOT,
                    DataGapSeverity.WARNING,
                    asof_timestamp,
                    expected_cadence_seconds,
                    "MISSING_PRICE_SNAPSHOT",
                )
            )
        elif (
            expected_cadence_seconds is not None
            and (
                _as_utc(asof_timestamp) - _as_utc(price.available_at)
            ).total_seconds()
            > expected_cadence_seconds
        ):
            gaps.append(
                _gap(
                    coverage_report,
                    market.market_id,
                    market_venue_name,
                    DataGapType.STALE_MARKET_DATA,
                    DataGapSeverity.WARNING,
                    asof_timestamp,
                    expected_cadence_seconds,
                    "STALE_MARKET_DATA",
                    start_time=price.available_at,
                    observed_count=1,
                )
            )
        if repo.get_latest_liquidity_snapshot_asof(market.market_id, asof_timestamp) is None:
            gaps.append(
                _gap(
                    coverage_report,
                    market.market_id,
                    market_venue_name,
                    DataGapType.MISSING_LIQUIDITY_SNAPSHOT,
                    DataGapSeverity.WARNING,
                    asof_timestamp,
                    expected_cadence_seconds,
                    "MISSING_LIQUIDITY_SNAPSHOT",
                )
            )
        if repo.get_latest_quality_report_asof(market.market_id, asof_timestamp) is None:
            gaps.append(
                _gap(
                    coverage_report,
                    market.market_id,
                    market_venue_name,
                    DataGapType.MISSING_QUALITY_REPORT,
                    DataGapSeverity.INFO,
                    asof_timestamp,
                    expected_cadence_seconds,
                    "MISSING_QUALITY_REPORT",
                )
            )
    return [repo.save_data_gap(gap) for gap in gaps]


def _gap(
    coverage_report: DataCoverageReport | None,
    market_id: str,
    venue_name: str | None,
    gap_type: DataGapType,
    severity: DataGapSeverity,
    asof_timestamp: datetime,
    expected_cadence_seconds: int | None,
    reason_code: str,
    *,
    start_time: datetime | None = None,
    observed_count: int = 0,
) -> DataGap:
    return DataGap(
        data_gap_id=dataops_object_id(
            "data_gap",
            {
                "coverage_report_id": (
                    coverage_report.coverage_report_id if coverage_report else None
                ),
                "market_id": market_id,
                "gap_type": gap_type.value,
                "asof_timestamp": asof_timestamp,
                "reason_code": reason_code,
                "start_time": start_time,
            },
        ),
        coverage_report_id=coverage_report.coverage_report_id if coverage_report else None,
        market_id=market_id,
        venue_name=venue_name,
        gap_type=gap_type,
        severity=severity,
        start_time=start_time,
        end_time=asof_timestamp,
        detected_at=datetime.now(tz=UTC),
        expected_cadence_seconds=expected_cadence_seconds,
        observed_count=observed_count,
        expected_count=1,
        reason_code=reason_code,
        description=reason_code.lower(),
        metadata={"detector_version": "data_gap_detector_v1"},
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
