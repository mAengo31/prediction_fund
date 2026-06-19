"""Local vendor sample file loading utilities."""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from prediction_desk.vendor_data.enums import VendorFileType

DEFAULT_MAX_SIZE_MB = 100


class VendorFileLoaderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def reject_url_path(path: str) -> None:
    parsed = urlparse(path)
    if parsed.scheme or "://" in path:
        raise VendorFileLoaderError("vendor_file_path_must_be_local")


def detect_file_type(path: Path) -> VendorFileType:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return VendorFileType.CSV
    if suffix == ".json":
        return VendorFileType.JSON
    if suffix in {".jsonl", ".ndjson"}:
        return VendorFileType.JSONL
    if suffix == ".parquet":
        return VendorFileType.PARQUET
    return VendorFileType.UNKNOWN


def compute_file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_local_file(path_value: str, *, max_size_mb: int = DEFAULT_MAX_SIZE_MB) -> Path:
    reject_url_path(path_value)
    path = Path(path_value).expanduser()
    if not path.exists() or not path.is_file():
        raise VendorFileLoaderError("vendor_sample_file_not_found")
    file_size = path.stat().st_size
    if file_size > max_size_mb * 1024 * 1024:
        raise VendorFileLoaderError("vendor_sample_file_too_large")
    return path.resolve()


def load_rows(path_value: str, *, max_size_mb: int = DEFAULT_MAX_SIZE_MB) -> list[dict[str, Any]]:
    path = validate_local_file(path_value, max_size_mb=max_size_mb)
    file_type = detect_file_type(path)
    if file_type == VendorFileType.CSV:
        return _load_csv(path)
    if file_type == VendorFileType.JSON:
        return _load_json(path)
    if file_type == VendorFileType.JSONL:
        return _load_jsonl(path)
    if file_type == VendorFileType.PARQUET:
        return _load_parquet(path)
    raise VendorFileLoaderError("vendor_file_type_unsupported")


def schema_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns: set[str] = set()
    non_null_counts: dict[str, int] = {}
    for row in rows:
        for key, value in row.items():
            columns.add(key)
            if value not in (None, ""):
                non_null_counts[key] = non_null_counts.get(key, 0) + 1
    return {
        "columns": sorted(columns),
        "non_null_counts": dict(sorted(non_null_counts.items())),
        "sample_rows": min(len(rows), 5),
    }


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [_clean_row(row) for row in reader]


def _load_json(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, list):
        return [_coerce_row(row) for row in payload]
    if isinstance(payload, dict):
        for key in ("rows", "data", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return [_coerce_row(row) for row in value]
        return [_coerce_row(payload)]
    raise VendorFileLoaderError("vendor_json_shape_unsupported")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rows.append(_coerce_row(json.loads(line)))
    return rows


def _load_parquet(path: Path) -> list[dict[str, Any]]:
    try:
        pd = importlib.import_module("pandas")
    except ImportError as exc:
        raise VendorFileLoaderError("vendor_parquet_unsupported") from exc
    dataframe = pd.read_parquet(path)
    return [_clean_row(row) for row in dataframe.to_dict(orient="records")]


def _coerce_row(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VendorFileLoaderError("vendor_row_shape_unsupported")
    return _clean_row(value.items())


def _clean_row(row: Iterable[tuple[str, Any]] | dict[str, Any]) -> dict[str, Any]:
    items = row.items() if isinstance(row, dict) else row
    return {str(key): value for key, value in items}
