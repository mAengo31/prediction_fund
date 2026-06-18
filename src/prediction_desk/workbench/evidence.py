"""As-of evidence helpers for desk workbench builders."""

from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.dataops.enums import CoverageScopeType
from prediction_desk.dataops.models import DataCoverageReport, DataGap
from prediction_desk.persistence.repositories import PredictionMarketRepository


def latest_data_gaps_for_market(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
    *,
    limit: int = 100,
) -> list[DataGap]:
    """Return gaps from the latest relevant coverage report only.

    Data gaps are append-only audit rows. A desk review view should not treat stale
    historical gaps as current if a newer coverage report no longer includes that
    market/gap. This helper keeps the lookup point-in-time safe while anchoring
    gap context to the latest coverage batch available as of the workbench timestamp.
    """

    report = _latest_relevant_coverage_report(repo, market_id, asof_timestamp)
    if report is None:
        return []
    return repo.list_data_gaps(
        market_id=market_id,
        coverage_report_id=report.coverage_report_id,
        limit=limit,
    )


def _latest_relevant_coverage_report(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> DataCoverageReport | None:
    asof_utc = _as_utc(asof_timestamp)
    for report in repo.list_data_coverage_reports(limit=250):
        if _as_utc(report.asof_timestamp) > asof_utc:
            continue
        if report.scope_type == CoverageScopeType.MARKET and report.market_id != market_id:
            continue
        return report
    return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
