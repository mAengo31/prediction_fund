"""Local vendor schema mapping config loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from prediction_desk.vendor_data.file_loader import VendorFileLoaderError, reject_url_path
from prediction_desk.vendor_data.models import VendorSchemaMappingConfig

MAX_MAPPING_CONFIG_BYTES = 1024 * 1024
SECRET_KEYWORDS = {
    "api_key",
    "apikey",
    "credential",
    "password",
    "private_key",
    "secret",
    "wallet",
}


class VendorSchemaMappingConfigError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def load_vendor_schema_mapping_config(path_value: str) -> VendorSchemaMappingConfig:
    try:
        reject_url_path(path_value)
    except VendorFileLoaderError as exc:
        raise VendorSchemaMappingConfigError(exc.code) from exc
    path = Path(path_value).expanduser()
    if not path.exists() or not path.is_file():
        raise VendorSchemaMappingConfigError("vendor_mapping_config_not_found")
    if path.stat().st_size > MAX_MAPPING_CONFIG_BYTES:
        raise VendorSchemaMappingConfigError("vendor_mapping_config_too_large")
    if path.suffix.lower() != ".json":
        raise VendorSchemaMappingConfigError("vendor_mapping_config_type_unsupported")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise VendorSchemaMappingConfigError("vendor_mapping_config_invalid_json") from exc
    if not isinstance(payload, dict):
        raise VendorSchemaMappingConfigError("vendor_mapping_config_shape_unsupported")
    if _contains_secret_like_key(payload):
        raise VendorSchemaMappingConfigError("vendor_mapping_config_contains_secret")
    try:
        return VendorSchemaMappingConfig.model_validate(payload)
    except ValidationError as exc:
        raise VendorSchemaMappingConfigError("vendor_mapping_config_invalid") from exc


def validate_vendor_schema_mapping_config(
    config: VendorSchemaMappingConfig,
    sample_columns: list[str],
) -> list[str]:
    sample_column_set = set(sample_columns)
    warnings: list[str] = []
    for column in _referenced_columns(config):
        if column not in sample_column_set:
            warnings.append(f"MAPPING_COLUMN_NOT_FOUND:{column}")
    if not (config.market_id_column or config.slug_column):
        warnings.append("MAPPING_MARKET_IDENTIFIER_NOT_CONFIGURED")
    if not (config.token_id_column or config.asset_id_column):
        warnings.append("MAPPING_TOKEN_IDENTIFIER_NOT_CONFIGURED")
    return list(dict.fromkeys(warnings))


def referenced_mapping_columns(config: VendorSchemaMappingConfig) -> list[str]:
    return sorted(_referenced_columns(config))


def _referenced_columns(config: VendorSchemaMappingConfig) -> set[str]:
    scalar_columns = {
        config.market_id_column,
        config.condition_id_column,
        config.question_id_column,
        config.gamma_market_id_column,
        config.slug_column,
        config.token_id_column,
        config.asset_id_column,
        config.observed_at_column,
        config.captured_at_column,
        config.available_at_column,
        config.market_start_column,
        config.elapsed_seconds_column,
    }
    mapping_columns = (
        list(config.timestamp_columns.values())
        + list(config.price_columns.values())
        + list(config.quote_columns.values())
        + list(config.orderbook_columns.values())
        + list(config.trade_columns.values())
        + list(config.resolution_columns.values())
        + list(config.feature_columns.values())
    )
    return {column for column in [*scalar_columns, *mapping_columns] if column}


def _contains_secret_like_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).strip().lower().replace("-", "_").replace(" ", "_")
            if any(keyword in normalized for keyword in SECRET_KEYWORDS):
                return True
            if _contains_secret_like_key(nested):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_like_key(item) for item in value)
    return False
