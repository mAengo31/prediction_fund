"""Validation checks for vendor sample rows."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from prediction_desk.vendor_data.enums import VendorValidationStatus
from prediction_desk.vendor_data.models import VendorDataValidationReport, VendorSchemaInspection


def validate_vendor_rows(
    *,
    validation_report_id: str,
    sample_file_id: str,
    rows: list[dict[str, Any]],
    inspection: VendorSchemaInspection,
    created_at: datetime,
) -> VendorDataValidationReport:
    missing_required_columns: list[str] = []
    token_mapping_issues: list[str] = []
    timestamp_issues: list[str] = []
    price_issues: list[str] = []
    duplicate_issues: list[str] = []
    point_in_time_issues: list[str] = []
    warnings: list[str] = []

    if not rows:
        missing_required_columns.append("NO_ROWS")
    if not inspection.timestamp_columns:
        timestamp_issues.append("NO_TIMESTAMP_COLUMN")
    if not inspection.market_identifier_columns:
        token_mapping_issues.append("NO_MARKET_IDENTIFIER_COLUMN")
    if _looks_token_level(inspection) and not inspection.token_identifier_columns:
        token_mapping_issues.append("NO_TOKEN_IDENTIFIER_COLUMN")
    if not _has_point_in_time_columns(inspection.detected_columns):
        point_in_time_issues.append("MISSING_OBSERVED_CAPTURED_AVAILABLE_COLUMNS")

    timestamp_columns = inspection.timestamp_columns
    price_columns = inspection.price_columns
    size_columns = inspection.size_columns
    token_columns = inspection.token_identifier_columns

    for index, row in enumerate(rows, start=1):
        if token_columns and not any(_present(row.get(column)) for column in token_columns):
            token_mapping_issues.append(f"ROW_{index}_MISSING_TOKEN_ID")
        for column in timestamp_columns:
            value = row.get(column)
            if _present(value) and _parse_datetime(value) is None:
                timestamp_issues.append(f"ROW_{index}_{column}_UNPARSEABLE_TIMESTAMP")
            elif _present(value) and _parse_datetime(value).tzinfo is None:  # type: ignore[union-attr]
                warnings.append(f"ROW_{index}_{column}_TIMEZONE_INFERRED")
        for column in price_columns:
            value = row.get(column)
            if not _present(value):
                continue
            decimal_value = _parse_decimal(value)
            if decimal_value is None:
                price_issues.append(f"ROW_{index}_{column}_INVALID_PRICE")
            elif decimal_value < Decimal("0") or decimal_value > Decimal("1"):
                price_issues.append(f"ROW_{index}_{column}_PRICE_OUT_OF_RANGE")
        for column in size_columns:
            value = row.get(column)
            if not _present(value):
                continue
            decimal_value = _parse_decimal(value)
            if decimal_value is None:
                warnings.append(f"ROW_{index}_{column}_INVALID_SIZE")
            elif decimal_value < Decimal("0"):
                warnings.append(f"ROW_{index}_{column}_NEGATIVE_SIZE")
        if inspection.orderbook_columns and not _has_orderbook_shape(row, inspection):
            warnings.append(f"ROW_{index}_ORDERBOOK_SHAPE_INCOMPLETE")

    duplicate_count = _duplicate_count(rows, inspection)
    if duplicate_count:
        duplicate_issues.append(f"DUPLICATE_LIKELY_KEYS_{duplicate_count}")

    status = VendorValidationStatus.PASS
    if (
        missing_required_columns
        or price_issues
        or any(issue.endswith("UNPARSEABLE_TIMESTAMP") for issue in timestamp_issues)
    ):
        status = VendorValidationStatus.FAIL
    elif (
        token_mapping_issues
        or timestamp_issues
        or duplicate_issues
        or point_in_time_issues
        or warnings
    ):
        status = VendorValidationStatus.WARNING

    return VendorDataValidationReport(
        validation_report_id=validation_report_id,
        sample_file_id=sample_file_id,
        created_at=created_at,
        validation_status=status,
        row_count=len(rows),
        missing_required_columns=missing_required_columns,
        token_mapping_issues=_dedupe(token_mapping_issues),
        timestamp_issues=_dedupe(timestamp_issues),
        price_issues=_dedupe(price_issues),
        duplicate_issues=_dedupe(duplicate_issues),
        point_in_time_issues=_dedupe(point_in_time_issues),
        warnings=_dedupe(warnings),
        metadata={"validator_version": "vendor_data_validator_v1"},
    )


def _looks_token_level(inspection: VendorSchemaInspection) -> bool:
    columns = {column.lower() for column in inspection.detected_columns}
    return bool(
        inspection.orderbook_columns
        or inspection.trade_columns
        or {"asset_id", "token_id", "clob_token_id"} & columns
    )


def _has_point_in_time_columns(columns: list[str]) -> bool:
    normalized = {column.lower() for column in columns}
    return bool({"observed_at", "captured_at", "available_at", "timestamp"} & normalized)


def _has_orderbook_shape(row: dict[str, Any], inspection: VendorSchemaInspection) -> bool:
    keys = {key.lower(): key for key in row}
    has_split_book = all(
        _present(row.get(keys[name]))
        for name in ("bid_price", "bid_size", "ask_price", "ask_size")
        if name in keys
    )
    has_side_book = (
        "side" in keys
        and any(
            name in keys and _present(row.get(keys[name]))
            for name in ("price", "bid_price", "ask_price")
        )
        and any(
            name in keys and _present(row.get(keys[name]))
            for name in ("size", "quantity", "bid_size", "ask_size")
        )
    )
    return has_split_book or has_side_book or not inspection.orderbook_columns


def _duplicate_count(rows: list[dict[str, Any]], inspection: VendorSchemaInspection) -> int:
    key_columns = (
        inspection.timestamp_columns[:1]
        + inspection.market_identifier_columns[:1]
        + inspection.token_identifier_columns[:1]
        + inspection.price_columns[:1]
    )
    if len(key_columns) < 2:
        return 0
    keys = [
        tuple(str(row.get(column, "")) for column in key_columns)
        for row in rows
        if any(_present(row.get(column)) for column in key_columns)
    ]
    counts = Counter(keys)
    return sum(count - 1 for count in counts.values() if count > 1)


def _parse_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _present(value: Any) -> bool:
    return value not in (None, "")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
