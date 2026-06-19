"""Heuristic schema inspection for vendor sample files."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from prediction_desk.vendor_data.models import VendorSchemaInspection

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
    "observed_at",
    "captured_at",
    "available_at",
    "created_at",
    "updated_at",
    "time",
    "block_timestamp",
}
PRICE_NAMES = {"price", "mid", "bid", "ask", "bid_price", "ask_price", "yes_price", "no_price"}
SIZE_NAMES = {"size", "quantity", "bid_size", "ask_size", "amount", "depth"}
ORDERBOOK_NAMES = {"bid_price", "bid_size", "ask_price", "ask_size", "side", "level", "depth"}
TRADE_NAMES = {"trade_id", "transaction_hash", "maker", "taker", "trade_price", "price", "size"}
RESOLUTION_NAMES = {"resolved", "outcome", "resolution", "settlement", "resolution_time"}


def inspect_vendor_schema(
    *,
    schema_inspection_id: str,
    sample_file_id: str,
    rows: list[dict[str, Any]],
    inspected_at: datetime | None = None,
) -> VendorSchemaInspection:
    columns = sorted({column for row in rows for column in row})
    lowered = {column: _normalize(column) for column in columns}
    warnings: list[str] = []
    if not rows:
        warnings.append("EMPTY_SAMPLE")
    if not columns:
        warnings.append("NO_COLUMNS_DETECTED")

    return VendorSchemaInspection(
        schema_inspection_id=schema_inspection_id,
        sample_file_id=sample_file_id,
        inspected_at=inspected_at or datetime.now(tz=UTC),
        detected_columns=columns,
        detected_types={
            column: _detect_type([row.get(column) for row in rows])
            for column in columns
        },
        timestamp_columns=_matching(columns, lowered, TIMESTAMP_NAMES),
        market_identifier_columns=_matching(columns, lowered, MARKET_IDENTIFIER_NAMES),
        token_identifier_columns=_matching(columns, lowered, TOKEN_IDENTIFIER_NAMES),
        price_columns=_matching(columns, lowered, PRICE_NAMES),
        size_columns=_matching(columns, lowered, SIZE_NAMES),
        orderbook_columns=_matching(columns, lowered, ORDERBOOK_NAMES),
        trade_columns=_matching(columns, lowered, TRADE_NAMES),
        resolution_columns=_matching(columns, lowered, RESOLUTION_NAMES),
        warnings=warnings,
        metadata={"inspector_version": "vendor_schema_inspector_v1"},
    )


def _matching(columns: list[str], lowered: dict[str, str], names: set[str]) -> list[str]:
    values: list[str] = []
    for column in columns:
        normalized = lowered[column]
        if normalized in names or any(normalized.endswith(f"_{name}") for name in names):
            values.append(column)
    return values


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
