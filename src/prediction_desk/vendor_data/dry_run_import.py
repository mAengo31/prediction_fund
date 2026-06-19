"""Dry-run canonical import estimation for vendor rows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from prediction_desk.vendor_data.enums import VendorImportDryRunStatus, VendorSampleKind
from prediction_desk.vendor_data.models import VendorImportDryRun, VendorSchemaInspection


def dry_run_vendor_import(
    *,
    dry_run_id: str,
    sample_file_id: str,
    rows: list[dict[str, Any]],
    inspection: VendorSchemaInspection,
    created_at: datetime,
    sample_kind: VendorSampleKind | None = None,
) -> VendorImportDryRun:
    markets: set[str] = set()
    price_snapshots = 0
    orderbooks = 0
    trades = 0
    resolutions = 0
    would_skip_counts: dict[str, int] = {}
    errors: list[str] = []
    warnings: list[str] = []

    market_columns = inspection.market_identifier_columns
    token_columns = inspection.token_identifier_columns
    timestamp_columns = inspection.timestamp_columns
    price_columns = inspection.price_columns
    size_columns = inspection.size_columns

    for row in rows:
        market_id = _first_value(row, market_columns)
        token_id = _first_value(row, token_columns)
        timestamp = _first_value(row, timestamp_columns)
        price = _first_value(row, price_columns)
        size = _first_value(row, size_columns)

        if market_id:
            markets.add(str(market_id))
        if not market_id and not token_id:
            _inc(would_skip_counts, "missing_market_or_token_identifier")
            continue
        if timestamp and _parse_datetime(timestamp) is None:
            _inc(would_skip_counts, "invalid_timestamp")
            continue
        if price and not _valid_probability(price):
            _inc(would_skip_counts, "invalid_price")
            continue

        if _should_count_price(sample_kind, inspection) and price and timestamp:
            price_snapshots += 1
        if _should_count_orderbook(sample_kind, inspection) and _has_orderbook_row(row, inspection):
            if token_id or market_id:
                orderbooks += 1
            else:
                _inc(would_skip_counts, "orderbook_missing_identifier")
        if (
            _should_count_trade(sample_kind, inspection)
            and inspection.trade_columns
            and price
            and size
        ):
            trades += 1
        if _should_count_resolution(sample_kind, inspection) and inspection.resolution_columns:
            resolutions += 1

    if not rows:
        errors.append("NO_ROWS")
    token_required_kind = sample_kind in {
        VendorSampleKind.ORDERBOOK,
        VendorSampleKind.TRADES,
    }
    if not token_columns and (orderbooks or token_required_kind):
        warnings.append("TOKEN_MAPPING_NOT_DETECTED")

    status = VendorImportDryRunStatus.PASS
    if errors:
        status = VendorImportDryRunStatus.FAIL
    elif warnings or would_skip_counts:
        status = VendorImportDryRunStatus.WARNING

    would_create_counts = {
        "markets": len(markets),
        "token_mappings": _count_distinct(rows, token_columns),
        "price_snapshots": price_snapshots,
        "orderbook_snapshots": orderbooks,
        "trade_prints": trades,
        "resolution_events": resolutions,
    }
    return VendorImportDryRun(
        dry_run_id=dry_run_id,
        sample_file_id=sample_file_id,
        created_at=created_at,
        status=status,
        rows_examined=len(rows),
        canonical_markets_detected=len(markets),
        canonical_orderbooks_detected=orderbooks,
        canonical_price_snapshots_detected=price_snapshots,
        canonical_trade_prints_detected=trades,
        canonical_resolution_events_detected=resolutions,
        would_create_counts=would_create_counts,
        would_skip_counts=would_skip_counts,
        errors=errors,
        warnings=warnings,
        metadata={
            "dry_run_version": "vendor_dry_run_import_v1",
            "sample_kind": sample_kind.value if sample_kind else None,
            "persisted_canonical_data": False,
        },
    )


def _should_count_price(
    sample_kind: VendorSampleKind | None,
    inspection: VendorSchemaInspection,
) -> bool:
    return sample_kind in {
        None,
        VendorSampleKind.MIXED,
        VendorSampleKind.MARKET_DATA,
        VendorSampleKind.PRICE_HISTORY,
    } or bool(inspection.price_columns)


def _should_count_orderbook(
    sample_kind: VendorSampleKind | None,
    inspection: VendorSchemaInspection,
) -> bool:
    return sample_kind in {
        None,
        VendorSampleKind.MIXED,
        VendorSampleKind.ORDERBOOK,
    } or bool(inspection.orderbook_columns)


def _should_count_trade(
    sample_kind: VendorSampleKind | None,
    inspection: VendorSchemaInspection,
) -> bool:
    return sample_kind in {
        None,
        VendorSampleKind.MIXED,
        VendorSampleKind.TRADES,
    } or bool(inspection.trade_columns)


def _should_count_resolution(
    sample_kind: VendorSampleKind | None,
    inspection: VendorSchemaInspection,
) -> bool:
    return sample_kind in {None, VendorSampleKind.MIXED} and bool(inspection.resolution_columns)


def _has_orderbook_row(row: dict[str, Any], inspection: VendorSchemaInspection) -> bool:
    lowered = {key.lower(): key for key in row}
    split_book = any(name in lowered for name in ("bid_price", "bid_size", "ask_price", "ask_size"))
    side_book = "side" in lowered and any(
        name in lowered for name in ("price", "bid_price", "ask_price")
    )
    return bool(inspection.orderbook_columns and (split_book or side_book))


def _first_value(row: dict[str, Any], columns: list[str]) -> Any | None:
    for column in columns:
        value = row.get(column)
        if value not in (None, ""):
            return value
    return None


def _count_distinct(rows: list[dict[str, Any]], columns: list[str]) -> int:
    values = {
        str(value)
        for row in rows
        for column in columns
        if (value := row.get(column)) not in (None, "")
    }
    return len(values)


def _valid_probability(value: Any) -> bool:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return Decimal("0") <= parsed <= Decimal("1")


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _inc(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1
