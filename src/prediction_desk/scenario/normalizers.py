"""Normalize imported scenario artifacts into slow-lane feature snapshots."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from prediction_desk.scenario.models import (
    ScenarioArtifact,
    ScenarioFeatureSnapshot,
    ScenarioSeedBundle,
    compute_feature_input_hash,
    compute_feature_output_hash,
    scenario_object_id,
)


def normalize_mirofish_style_artifact(
    artifact: ScenarioArtifact,
    seed_bundle: ScenarioSeedBundle | None = None,
) -> ScenarioFeatureSnapshot:
    payload = dict(artifact.raw_payload)
    market_id = artifact.market_id or (seed_bundle.market_id if seed_bundle else None)
    if market_id is None:
        raise ValueError("scenario_artifact_market_id_required")
    reason_codes = _reason_codes(payload, artifact)
    scores = {
        "scenario_confidence_score": _score(payload.get("confidence_score"), reason_codes),
        "scenario_uncertainty_score": _score(
            payload.get("uncertainty_score"),
            reason_codes,
        ),
        "sentiment_score": _score(payload.get("sentiment_score"), reason_codes),
        "consensus_score": _score(payload.get("consensus_score"), reason_codes),
        "polarization_score": _score(payload.get("polarization_score"), reason_codes),
        "narrative_risk_score": _score(
            payload.get("narrative_risk_score"),
            reason_codes,
        ),
        "shock_risk_score": _score(payload.get("shock_risk_score"), reason_codes),
        "adoption_or_support_score": _score(
            payload.get("adoption_or_support_score"),
            reason_codes,
        ),
        "opposition_score": _score(payload.get("opposition_score"), reason_codes),
    }
    _score_reason_codes(scores, reason_codes)
    labels = _labels(payload)
    evidence = {
        "summary": payload.get("summary"),
        "predicted_outcome_label": payload.get("predicted_outcome_label"),
        "risk_factors": payload.get("risk_factors") or [],
        "agent_groups": payload.get("agent_groups") or [],
        "evidence": payload.get("evidence") or {},
        "notes": payload.get("notes"),
    }
    refs = [
        value
        for value in [
            artifact.scenario_artifact_id,
            seed_bundle.seed_bundle_id if seed_bundle else artifact.seed_bundle_id,
        ]
        if value
    ]
    provisional = ScenarioFeatureSnapshot(
        scenario_feature_snapshot_id="pending",
        scenario_artifact_id=artifact.scenario_artifact_id,
        seed_bundle_id=seed_bundle.seed_bundle_id if seed_bundle else artifact.seed_bundle_id,
        market_id=market_id,
        asof_timestamp=artifact.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=artifact.available_at,
        scenario_engine=str(payload.get("engine") or "unknown").upper(),
        horizon_hours=_int_or_none(payload.get("horizon_hours")),
        key_scenario_labels=labels,
        reason_codes=sorted(set(reason_codes)),
        evidence=evidence,
        source_ref_ids=sorted(refs),
        input_hash="pending",
        output_hash="pending",
        metadata={"normalizer_version": "mirofish_style_fixture_normalizer_v1"},
        **scores,
    )
    input_hash = compute_feature_input_hash(provisional)
    feature = provisional.model_copy(
        update={
            "scenario_feature_snapshot_id": scenario_object_id(
                "scenario_feature",
                {"input_hash": input_hash},
            ),
            "input_hash": input_hash,
        }
    )
    return feature.model_copy(update={"output_hash": compute_feature_output_hash(feature)})


def _reason_codes(payload: dict[str, Any], artifact: ScenarioArtifact) -> list[str]:
    reason_codes = ["MIROFISH_STYLE_FIXTURE_IMPORTED"]
    if artifact.source_type.value == "FIXTURE":
        reason_codes.append("SCENARIO_SYNTHETIC_FIXTURE")
    if artifact.source_type.value == "MANUAL_IMPORT":
        reason_codes.append("SCENARIO_MANUAL_IMPORT")
    if not payload.get("summary"):
        reason_codes.append("MISSING_SCENARIO_SUMMARY")
    return reason_codes


def _score(value: Any, reason_codes: list[str]) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        reason_codes.append("INVALID_SCENARIO_SCORE")
        return None
    try:
        score = int(value)
    except (TypeError, ValueError):
        reason_codes.append("INVALID_SCENARIO_SCORE")
        return None
    if score < 0 or score > 100:
        reason_codes.append("INVALID_SCENARIO_SCORE")
        return None
    return score


def _score_reason_codes(scores: dict[str, int | None], reason_codes: list[str]) -> None:
    confidence = scores["scenario_confidence_score"]
    uncertainty = scores["scenario_uncertainty_score"]
    polarization = scores["polarization_score"]
    narrative = scores["narrative_risk_score"]
    shock = scores["shock_risk_score"]
    if confidence is not None and confidence < 40:
        reason_codes.append("SCENARIO_LOW_CONFIDENCE")
    if uncertainty is not None and uncertainty >= 70:
        reason_codes.append("SCENARIO_HIGH_UNCERTAINTY")
    if polarization is not None and polarization >= 70:
        reason_codes.append("SCENARIO_HIGH_POLARIZATION")
    if narrative is not None and narrative >= 70:
        reason_codes.append("SCENARIO_HIGH_NARRATIVE_RISK")
    if shock is not None and shock >= 70:
        reason_codes.append("SCENARIO_HIGH_NARRATIVE_RISK")


def _labels(payload: dict[str, Any]) -> list[str]:
    labels = payload.get("key_scenarios") or []
    if not isinstance(labels, list):
        return []
    return sorted({str(label).strip() for label in labels if str(label).strip()})


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
