from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from prediction_desk.scenario.adapters import (
    FixtureMiroFishArtifactAdapter,
    ScenarioAdapterError,
    load_manual_artifact,
)

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_fixture_adapter_loads_local_json_only() -> None:
    artifacts = FixtureMiroFishArtifactAdapter().load_artifacts(asof_timestamp=ASOF)

    assert len(artifacts) >= 2
    assert {artifact.market_id for artifact in artifacts} >= {
        "mkt_sfo_rain_2026_09_01",
        "mkt_candidate_announcement_vague_2026",
    }


def test_fixture_adapter_rejects_urls() -> None:
    with pytest.raises(ScenarioAdapterError):
        FixtureMiroFishArtifactAdapter().load_artifacts(
            asof_timestamp=ASOF,
            file_paths=["https://example.invalid/report.json"],
        )


def test_manual_import_rejects_non_json(tmp_path: Path) -> None:
    path = tmp_path / "report.txt"
    path.write_text("{}", encoding="utf-8")

    with pytest.raises(ScenarioAdapterError):
        load_manual_artifact(file_path=str(path), asof_timestamp=ASOF)


def test_manual_import_rejects_oversized_file(tmp_path: Path) -> None:
    path = tmp_path / "report.json"
    path.write_text(" " * (5 * 1024 * 1024 + 1), encoding="utf-8")

    with pytest.raises(ScenarioAdapterError):
        load_manual_artifact(file_path=str(path), asof_timestamp=ASOF)
