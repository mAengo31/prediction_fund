"""Helpers for exposing scenario features to research."""

from __future__ import annotations

from typing import Any

from prediction_desk.scenario.models import ScenarioFeatureSnapshot


def scenario_feature_values(
    feature: ScenarioFeatureSnapshot | None,
) -> dict[str, Any]:
    if feature is None:
        return {
            "scenario_feature_snapshot_id": None,
            "scenario_artifact_id": None,
            "scenario_confidence_score": None,
            "scenario_uncertainty_score": None,
            "sentiment_score": None,
            "consensus_score": None,
            "polarization_score": None,
            "narrative_risk_score": None,
            "shock_risk_score": None,
            "adoption_or_support_score": None,
            "opposition_score": None,
            "key_scenario_labels": [],
            "reason_codes": [],
        }
    return {
        "scenario_feature_snapshot_id": feature.scenario_feature_snapshot_id,
        "scenario_artifact_id": feature.scenario_artifact_id,
        "scenario_engine": feature.scenario_engine,
        "horizon_hours": feature.horizon_hours,
        "scenario_confidence_score": feature.scenario_confidence_score,
        "scenario_uncertainty_score": feature.scenario_uncertainty_score,
        "sentiment_score": feature.sentiment_score,
        "consensus_score": feature.consensus_score,
        "polarization_score": feature.polarization_score,
        "narrative_risk_score": feature.narrative_risk_score,
        "shock_risk_score": feature.shock_risk_score,
        "adoption_or_support_score": feature.adoption_or_support_score,
        "opposition_score": feature.opposition_score,
        "key_scenario_labels": list(feature.key_scenario_labels),
        "reason_codes": list(feature.reason_codes),
        "evidence": dict(feature.evidence),
    }
