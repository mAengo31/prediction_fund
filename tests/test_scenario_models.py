from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from prediction_desk.scenario.enums import ScenarioArtifactSourceType, ScenarioArtifactType
from prediction_desk.scenario.models import (
    ScenarioArtifact,
    ScenarioFeatureSnapshot,
    compute_artifact_payload_hash,
)
from tests.paper_helpers import MARKET_ID

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_artifact_payload_hash_is_deterministic() -> None:
    payload = {"b": 2, "a": 1}

    assert compute_artifact_payload_hash(payload) == compute_artifact_payload_hash(
        {"a": 1, "b": 2}
    )


def test_scenario_feature_score_bounds_are_enforced() -> None:
    artifact = ScenarioArtifact(
        scenario_artifact_id="artifact_test",
        market_id=MARKET_ID,
        asof_timestamp=ASOF,
        captured_at=ASOF,
        available_at=ASOF,
        artifact_type=ScenarioArtifactType.MIROFISH_REPORT,
        source_type=ScenarioArtifactSourceType.FIXTURE,
        raw_payload={},
        raw_text=None,
        payload_hash="hash",
        schema_version="v1",
        is_simulated=True,
        metadata={},
    )
    with pytest.raises(ValidationError):
        ScenarioFeatureSnapshot(
            scenario_feature_snapshot_id="feature_test",
            scenario_artifact_id=artifact.scenario_artifact_id,
            market_id=MARKET_ID,
            asof_timestamp=ASOF,
            generated_at=ASOF,
            available_at=ASOF,
            scenario_engine="MIROFISH_STYLE",
            scenario_confidence_score=101,
            key_scenario_labels=[],
            reason_codes=[],
            evidence={},
            source_ref_ids=[],
            input_hash="input",
            output_hash="output",
            metadata={},
        )
