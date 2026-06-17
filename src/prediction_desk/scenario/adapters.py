"""Local-only scenario artifact adapters."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from prediction_desk.scenario.enums import (
    ScenarioArtifactSourceType,
    ScenarioArtifactType,
)

DEFAULT_FIXTURE_DIR = Path("sample_data") / "scenario_artifacts" / "mirofish_style"
MAX_ARTIFACT_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class ScenarioArtifactInput:
    raw_payload: dict[str, Any]
    raw_text: str
    source_path: str | None
    source_type: ScenarioArtifactSourceType
    artifact_type: ScenarioArtifactType
    schema_version: str
    market_id: str | None
    asof_timestamp: datetime


class ScenarioArtifactAdapter(Protocol):
    adapter_name: str

    def load_artifacts(
        self,
        *,
        asof_timestamp: datetime,
        market_ids: list[str] | None = None,
        fixture_dir: str | None = None,
        file_paths: list[str] | None = None,
    ) -> list[ScenarioArtifactInput]:
        """Loads local scenario artifact payloads."""


class ScenarioAdapterError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class FixtureMiroFishArtifactAdapter:
    adapter_name = "fixture_mirofish_style_v1"

    def load_artifacts(
        self,
        *,
        asof_timestamp: datetime,
        market_ids: list[str] | None = None,
        fixture_dir: str | None = None,
        file_paths: list[str] | None = None,
    ) -> list[ScenarioArtifactInput]:
        paths = (
            [_safe_json_path(path) for path in file_paths]
            if file_paths
            else _fixture_paths(fixture_dir)
        )
        allowed_markets = set(market_ids or [])
        artifacts: list[ScenarioArtifactInput] = []
        for path in paths:
            payload, raw_text = _load_json_payload(path)
            market_id = _optional_str(payload.get("market_id"))
            if allowed_markets and market_id not in allowed_markets:
                continue
            artifacts.append(
                ScenarioArtifactInput(
                    raw_payload=payload,
                    raw_text=raw_text,
                    source_path=str(path),
                    source_type=(
                        ScenarioArtifactSourceType.MANUAL_IMPORT
                        if file_paths
                        else ScenarioArtifactSourceType.FIXTURE
                    ),
                    artifact_type=_artifact_type(payload, bool(file_paths)),
                    schema_version=str(payload.get("schema_version") or "unknown"),
                    market_id=market_id,
                    asof_timestamp=asof_timestamp,
                )
            )
        return artifacts


def load_manual_artifact(
    *,
    file_path: str,
    asof_timestamp: datetime,
    market_id: str | None = None,
) -> ScenarioArtifactInput:
    path = _safe_json_path(file_path)
    payload, raw_text = _load_json_payload(path)
    payload_market_id = _optional_str(payload.get("market_id"))
    return ScenarioArtifactInput(
        raw_payload=payload,
        raw_text=raw_text,
        source_path=str(path),
        source_type=ScenarioArtifactSourceType.MANUAL_IMPORT,
        artifact_type=_artifact_type(payload, manual=True),
        schema_version=str(payload.get("schema_version") or "unknown"),
        market_id=market_id or payload_market_id,
        asof_timestamp=asof_timestamp,
    )


def _fixture_paths(fixture_dir: str | None) -> list[Path]:
    base = _safe_directory(fixture_dir) if fixture_dir else _default_fixture_dir()
    if not base.exists():
        raise ScenarioAdapterError("scenario_fixture_dir_not_found", str(base))
    return sorted(path for path in base.iterdir() if path.suffix.casefold() == ".json")


def _default_fixture_dir() -> Path:
    cwd_fixture_dir = Path.cwd() / DEFAULT_FIXTURE_DIR
    if cwd_fixture_dir.exists():
        return cwd_fixture_dir
    source_fixture_dir = Path(__file__).resolve().parents[3] / DEFAULT_FIXTURE_DIR
    if source_fixture_dir.exists():
        return source_fixture_dir
    return cwd_fixture_dir


def _safe_directory(value: str) -> Path:
    if _looks_like_url(value):
        raise ScenarioAdapterError("scenario_file_path_must_be_local")
    path = Path(value).expanduser()
    if not path.exists() or not path.is_dir():
        raise ScenarioAdapterError("scenario_fixture_dir_not_found", str(path))
    return path


def _safe_json_path(value: str | Path) -> Path:
    text = str(value)
    if _looks_like_url(text):
        raise ScenarioAdapterError("scenario_file_path_must_be_local")
    path = Path(text).expanduser()
    if path.suffix.casefold() != ".json":
        raise ScenarioAdapterError("scenario_artifact_must_be_json", str(path))
    if not path.exists() or not path.is_file():
        raise ScenarioAdapterError("scenario_artifact_not_found", str(path))
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ScenarioAdapterError("scenario_artifact_too_large", str(path))
    return path


def _load_json_payload(path: Path) -> tuple[dict[str, Any], str]:
    raw_text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ScenarioAdapterError("scenario_artifact_invalid_json", str(path)) from exc
    if not isinstance(payload, dict):
        raise ScenarioAdapterError("scenario_artifact_payload_must_be_object", str(path))
    return payload, raw_text


def _artifact_type(payload: dict[str, Any], manual: bool) -> ScenarioArtifactType:
    engine = str(payload.get("engine") or "").casefold()
    if engine == "mirofish_style":
        return ScenarioArtifactType.MIROFISH_REPORT
    return ScenarioArtifactType.MANUAL_NOTE if manual else ScenarioArtifactType.FIXTURE_REPORT


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _looks_like_url(value: str) -> bool:
    lowered = value.casefold()
    return "://" in lowered or lowered.startswith(("http:", "https:"))
