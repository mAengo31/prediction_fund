"""Dry-run canonical import estimation for vendor rows."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from prediction_desk.vendor_data.enums import VendorImportDryRunStatus, VendorSampleKind
from prediction_desk.vendor_data.models import VendorImportDryRun, VendorSchemaInspection

STRONG_TRADE_COLUMNS = {
    "trade_id",
    "transaction_hash",
    "tx_hash",
    "maker",
    "taker",
    "maker_order_id",
    "taker_order_id",
    "trade_event_type",
    "event_type",
    "fill",
    "fill_id",
}
EXECUTION_TIMESTAMP_COLUMNS = {
    "execution_timestamp",
    "executed_at",
    "filled_at",
    "fill_timestamp",
    "trade_timestamp",
}
SPLIT_BOOK_COLUMNS = {"bid_price", "bid_size", "ask_price", "ask_size"}
BOOK_DEPTH_COLUMNS = {"level", "depth", "book_timestamp", "orderbook_timestamp"}


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

        has_trade_evidence = _has_trade_evidence(row)
        has_book_evidence = _has_orderbook_evidence(row, inspection, sample_kind)
        has_price_size = _has_price_size(row, inspection)

        _record_suppression_warnings(
            warnings=warnings,
            sample_kind=sample_kind,
            row=row,
            inspection=inspection,
            has_trade_evidence=has_trade_evidence,
            has_book_evidence=has_book_evidence,
            has_price_size=has_price_size,
        )

        if _should_count_price(sample_kind, row, inspection, has_trade_evidence, has_book_evidence):
            price_snapshots += 1
        if _should_count_orderbook(sample_kind, inspection) and has_book_evidence:
            if token_id or market_id:
                orderbooks += 1
            else:
                _inc(would_skip_counts, "orderbook_missing_identifier")
        if _should_count_trade(sample_kind, inspection) and has_trade_evidence and price and size:
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
    warnings.extend(
        _sample_kind_mismatch_warnings(
            sample_kind=sample_kind,
            inspection=inspection,
            price_snapshots=price_snapshots,
            orderbooks=orderbooks,
            trades=trades,
        )
    )
    warnings = _dedupe(warnings)

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
    row: dict[str, Any],
    inspection: VendorSchemaInspection,
    has_trade_evidence: bool,
    has_book_evidence: bool,
) -> bool:
    if not _first_value(row, inspection.price_columns) or not _first_value(
        row, inspection.timestamp_columns
    ):
        return False
    if sample_kind in {VendorSampleKind.PRICE_HISTORY, VendorSampleKind.MARKET_DATA}:
        return True
    if sample_kind is VendorSampleKind.ORDERBOOK:
        return has_book_evidence
    if sample_kind is VendorSampleKind.TRADES:
        return has_trade_evidence
    return (
        has_book_evidence
        or has_trade_evidence
        or _has_price_history_evidence(row, inspection)
    )


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
    return sample_kind in {None, VendorSampleKind.MIXED, VendorSampleKind.TRADES} or bool(
        inspection.trade_columns
    )


def _should_count_resolution(
    sample_kind: VendorSampleKind | None,
    inspection: VendorSchemaInspection,
) -> bool:
    return sample_kind in {None, VendorSampleKind.MIXED} and bool(inspection.resolution_columns)


def _has_trade_evidence(row: dict[str, Any]) -> bool:
    normalized = _normalized_present_keys(row)
    if normalized & STRONG_TRADE_COLUMNS:
        return True
    return "side" in normalized and bool(normalized & EXECUTION_TIMESTAMP_COLUMNS)


def _has_orderbook_evidence(
    row: dict[str, Any],
    inspection: VendorSchemaInspection,
    sample_kind: VendorSampleKind | None,
) -> bool:
    normalized = _normalized_present_keys(row)
    split_book_count = len(normalized & SPLIT_BOOK_COLUMNS)
    if split_book_count >= 2:
        return True
    if normalized & BOOK_DEPTH_COLUMNS and _has_price_size(row, inspection):
        return True
    return (
        sample_kind is VendorSampleKind.ORDERBOOK
        and bool(normalized & {"token_id", "asset_id", "clob_token_id"})
        and "side" in normalized
        and _has_price_size(row, inspection)
    )


def _has_price_history_evidence(
    row: dict[str, Any],
    inspection: VendorSchemaInspection,
) -> bool:
    normalized = _normalized_present_keys(row)
    if normalized & {"mid", "bid", "ask", "interval"}:
        return True
    return bool(_first_value(row, inspection.price_columns)) and not _has_price_size(
        row, inspection
    )


def _record_suppression_warnings(
    *,
    warnings: list[str],
    sample_kind: VendorSampleKind | None,
    row: dict[str, Any],
    inspection: VendorSchemaInspection,
    has_trade_evidence: bool,
    has_book_evidence: bool,
    has_price_size: bool,
) -> None:
    if has_price_size and inspection.trade_columns and not has_trade_evidence:
        warnings.append("SUPPRESSED_TRADE_COUNT_MISSING_TRADE_EVIDENCE")
    if (
        has_price_size
        and _has_side_price_size(row, inspection)
        and inspection.orderbook_columns
        and not has_book_evidence
    ):
        warnings.append("SUPPRESSED_ORDERBOOK_COUNT_MISSING_BOOK_EVIDENCE")
    if (
        has_price_size
        and not has_trade_evidence
        and not has_book_evidence
        and sample_kind in {None, VendorSampleKind.MIXED}
    ):
        warnings.append("AMBIGUOUS_PRICE_SIZE_ROWS")


def _sample_kind_mismatch_warnings(
    *,
    sample_kind: VendorSampleKind | None,
    inspection: VendorSchemaInspection,
    price_snapshots: int,
    orderbooks: int,
    trades: int,
) -> list[str]:
    if sample_kind is None:
        return []
    mismatches: list[str] = []
    if sample_kind in {VendorSampleKind.PRICE_HISTORY, VendorSampleKind.MARKET_DATA}:
        if not inspection.price_columns or not price_snapshots:
            mismatches.append("SAMPLE_KIND_SCHEMA_MISMATCH")
    elif sample_kind is VendorSampleKind.ORDERBOOK:
        if not orderbooks:
            mismatches.append("SAMPLE_KIND_SCHEMA_MISMATCH")
    elif sample_kind is VendorSampleKind.TRADES:
        if not trades:
            mismatches.append("SAMPLE_KIND_SCHEMA_MISMATCH")
    elif sample_kind is VendorSampleKind.MIXED:
        detected_types = sum(1 for count in (price_snapshots, orderbooks, trades) if count)
        if detected_types < 2:
            mismatches.append("SAMPLE_KIND_SCHEMA_MISMATCH")
    return mismatches


def _has_price_size(row: dict[str, Any], inspection: VendorSchemaInspection) -> bool:
    return bool(_first_value(row, inspection.price_columns)) and bool(
        _first_value(row, inspection.size_columns)
    )


def _has_side_price_size(row: dict[str, Any], inspection: VendorSchemaInspection) -> bool:
    return "side" in _normalized_present_keys(row) and _has_price_size(row, inspection)


def _normalized_present_keys(row: dict[str, Any]) -> set[str]:
    return {
        key.strip().lower().replace("-", "_").replace(" ", "_")
        for key, value in row.items()
        if value not in (None, "")
    }


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


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
