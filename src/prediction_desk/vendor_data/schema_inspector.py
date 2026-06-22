"""Heuristic schema inspection for vendor sample files."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from prediction_desk.vendor_data.mapping_config import (
    validate_vendor_schema_mapping_config,
)
from prediction_desk.vendor_data.models import VendorSchemaInspection, VendorSchemaMappingConfig

MARKET_IDENTIFIER_NAMES = {
    "market_id",
    "condition_id",
    "question_id",
    "gamma_market_id",
    "slug",
    "event_id",
    "market_address",
}
TOKEN_IDENTIFIER_NAMES = {"clob_token_id", "token_id", "asset_id", "yes_token_id", "no_token_id"}
TIMESTAMP_NAMES = {
    "timestamp",
    "timestamp_created_at",
    "timestamp_received",
    "ts",
    "datetime",
    "date_time",
    "unix_timestamp",
    "observed_at",
    "captured_at",
    "available_at",
    "created_at",
    "created_time",
    "updated_at",
    "time",
    "block_timestamp",
}
PRICE_NAMES = {
    "price",
    "mid",
    "bid",
    "ask",
    "bid_price",
    "ask_price",
    "best_bid",
    "best_ask",
    "yes_price",
    "no_price",
}
SIZE_NAMES = {"size", "quantity", "bid_size", "ask_size", "amount", "depth"}
ORDERBOOK_NAMES = {
    "bid_price",
    "bid_size",
    "ask_price",
    "ask_size",
    "best_bid",
    "best_ask",
    "bids",
    "asks",
    "side",
    "level",
    "depth",
}
TRADE_NAMES = {"trade_id", "transaction_hash", "maker", "taker", "trade_price", "price", "size"}
RESOLUTION_NAMES = {"resolved", "outcome", "resolution", "settlement", "resolution_time"}


def inspect_vendor_schema(
    *,
    schema_inspection_id: str,
    sample_file_id: str,
    rows: list[dict[str, Any]],
    inspected_at: datetime | None = None,
    mapping_config: VendorSchemaMappingConfig | None = None,
) -> VendorSchemaInspection:
    columns = sorted({column for row in rows for column in row})
    lowered = {column: _normalize(column) for column in columns}
    warnings: list[str] = []
    if not rows:
        warnings.append("EMPTY_SAMPLE")
    if not columns:
        warnings.append("NO_COLUMNS_DETECTED")

    timestamp_columns = _matching(columns, lowered, TIMESTAMP_NAMES)
    market_identifier_columns = _matching(columns, lowered, MARKET_IDENTIFIER_NAMES)
    token_identifier_columns = _matching(columns, lowered, TOKEN_IDENTIFIER_NAMES)
    price_columns = _matching(columns, lowered, PRICE_NAMES)
    orderbook_columns = _matching(columns, lowered, ORDERBOOK_NAMES)
    trade_columns = _matching(columns, lowered, TRADE_NAMES)
    resolution_columns = _matching(columns, lowered, RESOLUTION_NAMES)
    metadata: dict[str, Any] = {"inspector_version": "vendor_schema_inspector_v1"}

    if mapping_config is not None:
        mapping_warnings = validate_vendor_schema_mapping_config(mapping_config, columns)
        warnings.extend(mapping_warnings)
        timestamp_columns = _merge_columns(
            timestamp_columns,
            mapping_config.timestamp_columns.values(),
            [
                mapping_config.observed_at_column,
                mapping_config.captured_at_column,
                mapping_config.available_at_column,
                mapping_config.market_start_column,
            ],
        )
        market_identifier_columns = _merge_columns(
            market_identifier_columns,
            [
                mapping_config.market_id_column,
                mapping_config.condition_id_column,
                mapping_config.question_id_column,
                mapping_config.gamma_market_id_column,
                mapping_config.slug_column,
            ],
        )
        token_identifier_columns = _merge_columns(
            token_identifier_columns,
            [mapping_config.token_id_column, mapping_config.asset_id_column],
        )
        price_columns = _merge_columns(
            price_columns,
            mapping_config.price_columns.values(),
            mapping_config.quote_columns.values(),
        )
        orderbook_columns = _merge_columns(
            orderbook_columns,
            mapping_config.orderbook_columns.values(),
        )
        trade_columns = _merge_columns(trade_columns, mapping_config.trade_columns.values())
        resolution_columns = _merge_columns(
            resolution_columns,
            mapping_config.resolution_columns.values(),
        )
        metadata["mapping_config"] = {
            "mapping_name": mapping_config.mapping_name,
            "vendor_name": mapping_config.vendor_name,
            "dataset_name": mapping_config.dataset_name,
            "sample_kind": mapping_config.sample_kind.value,
            "quote_columns": mapping_config.quote_columns,
            "feature_columns": mapping_config.feature_columns,
            "warnings": mapping_warnings,
        }

    return VendorSchemaInspection(
        schema_inspection_id=schema_inspection_id,
        sample_file_id=sample_file_id,
        inspected_at=inspected_at or datetime.now(tz=UTC),
        detected_columns=columns,
        detected_types={
            column: _detect_type([row.get(column) for row in rows])
            for column in columns
        },
        timestamp_columns=timestamp_columns,
        market_identifier_columns=market_identifier_columns,
        token_identifier_columns=token_identifier_columns,
        price_columns=price_columns,
        size_columns=_matching(columns, lowered, SIZE_NAMES),
        orderbook_columns=orderbook_columns,
        trade_columns=trade_columns,
        resolution_columns=resolution_columns,
        warnings=list(dict.fromkeys(warnings)),
        metadata=metadata,
    )


def _matching(columns: list[str], lowered: dict[str, str], names: set[str]) -> list[str]:
    values: list[str] = []
    for column in columns:
        normalized = lowered[column]
        if normalized in names or any(normalized.endswith(f"_{name}") for name in names):
            values.append(column)
    return values


def _merge_columns(
    existing: list[str],
    *column_groups: Any,
) -> list[str]:
    merged = list(existing)
    for group in column_groups:
        if group is None:
            continue
        candidates = [group] if isinstance(group, str) else list(group)
        for column in candidates:
            if column and column not in merged:
                merged.append(column)
    return merged


def _normalize(column: str) -> str:
    return column.strip().lower().replace("-", "_").replace(" ", "_")


def _detect_type(values: list[Any]) -> str:
    non_empty = [value for value in values if value not in (None, "")]
    if not non_empty:
        return "empty"
    if all(isinstance(value, bool) for value in non_empty):
        return "bool"
    if all(_is_int_like(value) for value in non_empty):
        return "int"
    if all(_is_decimal_like(value) for value in non_empty):
        return "decimal"
    if all(_is_datetime_like(value) for value in non_empty):
        return "datetime"
    return "string"


def _is_int_like(value: Any) -> bool:
    try:
        int(str(value))
    except (TypeError, ValueError):
        return False
    return "." not in str(value)


def _is_decimal_like(value: Any) -> bool:
    try:
        Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return True


def _is_datetime_like(value: Any) -> bool:
    if isinstance(value, datetime):
        return True
    text = str(value).strip()
    if not text:
        return False
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
