"""Validation checks for vendor sample rows."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from prediction_desk.vendor_data.enums import VendorValidationStatus
from prediction_desk.vendor_data.models import (
    VendorDataValidationReport,
    VendorSchemaInspection,
    VendorSchemaMappingConfig,
)


def validate_vendor_rows(
    *,
    validation_report_id: str,
    sample_file_id: str,
    rows: list[dict[str, Any]],
    inspection: VendorSchemaInspection,
    created_at: datetime,
    mapping_config: VendorSchemaMappingConfig | None = None,
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
    if mapping_config and mapping_config.quote_columns and not inspection.token_identifier_columns:
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
        if mapping_config is not None:
            _validate_mapped_quotes(
                row=row,
                index=index,
                mapping_config=mapping_config,
                price_issues=price_issues,
            )
            _validate_mapped_resolution(
                row=row,
                index=index,
                mapping_config=mapping_config,
                warnings=warnings,
            )
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
        metadata={
            "validator_version": "vendor_data_validator_v1",
            "mapping_config": _mapping_metadata(mapping_config),
        },
    )


def _validate_mapped_quotes(
    *,
    row: dict[str, Any],
    index: int,
    mapping_config: VendorSchemaMappingConfig,
    price_issues: list[str],
) -> None:
    quote_values: dict[str, Decimal] = {}
    for role, column in mapping_config.quote_columns.items():
        value = row.get(column)
        if not _present(value):
            continue
        decimal_value = _parse_decimal(value)
        if decimal_value is None:
            price_issues.append(f"ROW_{index}_{column}_INVALID_PRICE")
            continue
        if decimal_value < Decimal("0") or decimal_value > Decimal("1"):
            price_issues.append(f"ROW_{index}_{column}_PRICE_OUT_OF_RANGE")
        quote_values[role] = decimal_value

    _validate_quote_pair(
        index=index,
        side="YES",
        bid=quote_values.get("yes_bid"),
        ask=quote_values.get("yes_ask"),
        price_issues=price_issues,
    )
    _validate_quote_pair(
        index=index,
        side="NO",
        bid=quote_values.get("no_bid"),
        ask=quote_values.get("no_ask"),
        price_issues=price_issues,
    )


def _validate_quote_pair(
    *,
    index: int,
    side: str,
    bid: Decimal | None,
    ask: Decimal | None,
    price_issues: list[str],
) -> None:
    if bid is not None and ask is not None and bid > ask:
        price_issues.append(f"ROW_{index}_{side}_BID_GT_ASK")


def _validate_mapped_resolution(
    *,
    row: dict[str, Any],
    index: int,
    mapping_config: VendorSchemaMappingConfig,
    warnings: list[str],
) -> None:
    resolved_column = mapping_config.resolution_columns.get("resolved")
    winner_column = mapping_config.resolution_columns.get("winner")
    if not resolved_column:
        return
    resolved_value = row.get(resolved_column)
    if not _present(resolved_value):
        return
    resolved_state = _parse_bool_like(resolved_value)
    if resolved_state is None:
        warnings.append(f"ROW_{index}_{resolved_column}_UNRECOGNIZED_RESOLUTION_FLAG")
        return
    if resolved_state and winner_column and not _present(row.get(winner_column)):
        warnings.append(f"ROW_{index}_{winner_column}_RESOLVED_WITHOUT_WINNER")


def _mapping_metadata(mapping_config: VendorSchemaMappingConfig | None) -> dict[str, Any] | None:
    if mapping_config is None:
        return None
    return {
        "mapping_name": mapping_config.mapping_name,
        "sample_kind": mapping_config.sample_kind.value,
        "quote_columns": mapping_config.quote_columns,
        "resolution_columns": mapping_config.resolution_columns,
    }


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
    if any(name in keys and _present(row.get(keys[name])) for name in ("bids", "data_bids")):
        return True
    if any(name in keys and _present(row.get(keys[name])) for name in ("asks", "data_asks")):
        return True
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
    if epoch_datetime := _parse_epoch_datetime(value):
        return epoch_datetime
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _present(value: Any) -> bool:
    return value not in (None, "")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _parse_epoch_datetime(value: Any) -> datetime | None:
    text = str(value).strip()
    try:
        numeric = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    seconds = numeric
    if Decimal("946684800000") <= numeric <= Decimal("4102444800000"):
        seconds = numeric / Decimal("1000")
    if seconds < 946684800 or seconds > 4102444800:
        return None
    return datetime.fromtimestamp(float(seconds), tz=UTC)


def _parse_bool_like(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "t", "yes", "y", "1", "resolved"}:
        return True
    if text in {"false", "f", "no", "n", "0", "unresolved", "open"}:
        return False
    return None
