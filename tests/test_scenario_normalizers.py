from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.scenario.enums import ScenarioArtifactSourceType, ScenarioArtifactType
from prediction_desk.scenario.models import (
    ScenarioArtifact,
    compute_artifact_payload_hash,
)
from prediction_desk.scenario.normalizers import normalize_mirofish_style_artifact
from tests.paper_helpers import MARKET_ID

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_normalizer_maps_valid_scores_to_feature_snapshot() -> None:
    artifact = _artifact(
        {
            "engine": "mirofish_style",
            "summary": "Synthetic fixture.",
            "confidence_score": 62,
            "uncertainty_score": 38,
            "key_scenarios": ["context narrows"],
        }
    )

    feature = normalize_mirofish_style_artifact(artifact)

    assert feature.scenario_confidence_score == 62
    assert feature.scenario_uncertainty_score == 38
    assert feature.key_scenario_labels == ["context narrows"]
    assert "MIROFISH_STYLE_FIXTURE_IMPORTED" in feature.reason_codes


def test_invalid_scores_record_reason_code_without_crashing() -> None:
    artifact = _artifact(
        {
            "engine": "mirofish_style",
            "summary": "Synthetic fixture.",
            "confidence_score": 200,
            "uncertainty_score": 82,
        }
    )

    feature = normalize_mirofish_style_artifact(artifact)

    assert feature.scenario_confidence_score is None
    assert "INVALID_SCENARIO_SCORE" in feature.reason_codes
    assert "SCENARIO_HIGH_UNCERTAINTY" in feature.reason_codes


def _artifact(payload):
    payload_hash = compute_artifact_payload_hash(payload)
    return ScenarioArtifact(
        scenario_artifact_id="scenario_artifact_test",
        market_id=MARKET_ID,
        asof_timestamp=ASOF,
        captured_at=ASOF,
        available_at=ASOF,
        artifact_type=ScenarioArtifactType.MIROFISH_REPORT,
        source_type=ScenarioArtifactSourceType.FIXTURE,
        raw_payload=payload,
        raw_text=None,
        payload_hash=payload_hash,
        schema_version="mirofish_style_fixture_v1",
        is_simulated=True,
        metadata={},
    )
