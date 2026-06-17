"""Pydantic models for slow-lane scenario features."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from prediction_desk.scenario.enums import (
    ScenarioArtifactSourceType,
    ScenarioArtifactType,
    ScenarioEngine,
    ScenarioRunMode,
    ScenarioRunStatus,
    ScenarioSeedSource,
)

SCENARIO_SEED_VERSION = "scenario_seed_bundle_v1"
SCENARIO_SPEC_VERSION = "scenario_simulation_spec_v1"
SCENARIO_ARTIFACT_VERSION = "scenario_artifact_v1"
SCENARIO_FEATURE_VERSION = "scenario_feature_snapshot_v1"
SCENARIO_RUNNER_VERSION = "scenario_runner_v1"


class ScenarioModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScenarioSeedBundle(ScenarioModel):
    seed_bundle_id: str
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    seed_source: ScenarioSeedSource
    market_title: str | None = None
    market_description: str | None = None
    rule_snapshot_id: str | None = None
    rule_snapshot_hash: str | None = None
    resolution_predicate_id: str | None = None
    ambiguity_assessment_id: str | None = None
    market_data_quality_report_id: str | None = None
    integrity_assessment_id: str | None = None
    equivalence_assessment_ids: list[str] = Field(default_factory=list)
    divergence_assessment_ids: list[str] = Field(default_factory=list)
    trust_verdict_id: str | None = None
    source_ref_ids: list[str] = Field(default_factory=list)
    seed_text: str
    structured_context: dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioSimulationSpec(ScenarioModel):
    scenario_spec_id: str
    seed_bundle_id: str
    market_id: str
    asof_timestamp: datetime
    created_at: datetime
    scenario_engine: ScenarioEngine
    scenario_goal: str
    horizon_hours: int | None = Field(default=None, ge=0)
    requested_agent_count: int | None = Field(default=None, ge=0)
    requested_rounds: int | None = Field(default=None, ge=0)
    variables: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioArtifact(ScenarioModel):
    scenario_artifact_id: str
    scenario_spec_id: str | None = None
    seed_bundle_id: str | None = None
    market_id: str | None = None
    asof_timestamp: datetime
    captured_at: datetime
    available_at: datetime
    artifact_type: ScenarioArtifactType
    source_type: ScenarioArtifactSourceType
    source_path: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    raw_text: str | None = None
    payload_hash: str
    schema_version: str
    is_simulated: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioFeatureSnapshot(ScenarioModel):
    scenario_feature_snapshot_id: str
    scenario_artifact_id: str
    seed_bundle_id: str | None = None
    market_id: str
    asof_timestamp: datetime
    generated_at: datetime
    available_at: datetime
    scenario_engine: str
    horizon_hours: int | None = None
    scenario_confidence_score: int | None = Field(default=None, ge=0, le=100)
    scenario_uncertainty_score: int | None = Field(default=None, ge=0, le=100)
    sentiment_score: int | None = Field(default=None, ge=0, le=100)
    consensus_score: int | None = Field(default=None, ge=0, le=100)
    polarization_score: int | None = Field(default=None, ge=0, le=100)
    narrative_risk_score: int | None = Field(default=None, ge=0, le=100)
    shock_risk_score: int | None = Field(default=None, ge=0, le=100)
    adoption_or_support_score: int | None = Field(default=None, ge=0, le=100)
    opposition_score: int | None = Field(default=None, ge=0, le=100)
    key_scenario_labels: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_ref_ids: list[str] = Field(default_factory=list)
    input_hash: str
    output_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioRun(ScenarioModel):
    scenario_run_id: str
    name: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    status: ScenarioRunStatus
    asof_timestamp: datetime
    market_ids: list[str] = Field(default_factory=list)
    mode: ScenarioRunMode
    max_items: int
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    seed_bundles_created: int = 0
    specs_created: int = 0
    artifacts_imported: int = 0
    features_created: int = 0
    errors_count: int = 0


class ScenarioRunSummary(ScenarioModel):
    summary_id: str
    scenario_run_id: str
    created_at: datetime
    total_seed_bundles: int
    total_artifacts: int
    total_features: int
    average_scores: dict[str, Decimal] = Field(default_factory=dict)
    reason_code_counts: dict[str, int] = Field(default_factory=dict)
    markets_processed: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioRunConfig(ScenarioModel):
    name: str | None = None
    asof_timestamp: datetime
    market_ids: list[str] | None = None
    mode: ScenarioRunMode = ScenarioRunMode.IMPORT_FIXTURES
    max_items: int = Field(default=100, gt=0)
    fixture_dir: str | None = None
    manual_file_paths: list[str] | None = None
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioRunRequest(ScenarioModel):
    name: str | None = None
    asof_timestamp: datetime | None = None
    market_ids: list[str] | None = None
    mode: ScenarioRunMode = ScenarioRunMode.IMPORT_FIXTURES
    max_items: int = Field(default=100, gt=0)
    fixture_dir: str | None = None
    manual_file_paths: list[str] | None = None
    force: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioRunResult(ScenarioModel):
    run: ScenarioRun
    seed_bundles: list[ScenarioSeedBundle] = Field(default_factory=list)
    artifacts: list[ScenarioArtifact] = Field(default_factory=list)
    features: list[ScenarioFeatureSnapshot] = Field(default_factory=list)
    summary: ScenarioRunSummary


class ScenarioSeedBuildRequest(ScenarioModel):
    market_id: str
    asof_timestamp: datetime | None = None
    force: bool = False


class ScenarioSpecCreateRequest(ScenarioModel):
    seed_bundle_id: str
    scenario_goal: str
    horizon_hours: int | None = Field(default=72, ge=0)
    variables: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScenarioImportFixturesRequest(ScenarioModel):
    market_ids: list[str] | None = None
    asof_timestamp: datetime | None = None
    force: bool = False
    fixture_dir: str | None = None


class ScenarioImportManualRequest(ScenarioModel):
    file_path: str
    market_id: str | None = None
    asof_timestamp: datetime | None = None
    seed_bundle_id: str | None = None
    force: bool = False

    @field_validator("file_path")
    @classmethod
    def _reject_url(cls, value: str) -> str:
        lowered = value.casefold()
        if "://" in lowered or lowered.startswith(("http:", "https:")):
            raise ValueError("file_path must be local")
        return value


def compute_seed_input_hash(bundle: ScenarioSeedBundle) -> str:
    return hash_payload(
        {
            "version": SCENARIO_SEED_VERSION,
            "market_id": bundle.market_id,
            "asof_timestamp": bundle.asof_timestamp,
            "seed_source": bundle.seed_source.value,
            "source_ref_ids": sorted(bundle.source_ref_ids),
            "structured_context": bundle.structured_context,
        }
    )


def compute_seed_output_hash(bundle: ScenarioSeedBundle) -> str:
    return hash_payload(
        {
            "version": SCENARIO_SEED_VERSION,
            "seed_text": bundle.seed_text,
            "structured_context": bundle.structured_context,
            "source_ref_ids": sorted(bundle.source_ref_ids),
        }
    )


def compute_spec_id(seed_bundle_id: str, scenario_goal: str, horizon_hours: int | None) -> str:
    return scenario_object_id(
        "scenario_spec",
        {
            "version": SCENARIO_SPEC_VERSION,
            "seed_bundle_id": seed_bundle_id,
            "scenario_goal": scenario_goal,
            "horizon_hours": horizon_hours,
        },
    )


def compute_artifact_payload_hash(
    raw_payload: dict[str, Any],
    raw_text: str | None = None,
) -> str:
    return hash_payload(
        {
            "version": SCENARIO_ARTIFACT_VERSION,
            "raw_payload": raw_payload,
            "raw_text": raw_text,
        }
    )


def compute_artifact_id(
    *,
    payload_hash: str,
    source_type: ScenarioArtifactSourceType,
    market_id: str | None,
    asof_timestamp: datetime,
) -> str:
    return scenario_object_id(
        "scenario_artifact",
        {
            "payload_hash": payload_hash,
            "source_type": source_type.value,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp,
        },
    )


def compute_feature_input_hash(feature: ScenarioFeatureSnapshot) -> str:
    return hash_payload(
        {
            "version": SCENARIO_FEATURE_VERSION,
            "scenario_artifact_id": feature.scenario_artifact_id,
            "seed_bundle_id": feature.seed_bundle_id,
            "market_id": feature.market_id,
            "asof_timestamp": feature.asof_timestamp,
            "scenario_engine": feature.scenario_engine,
            "source_ref_ids": sorted(feature.source_ref_ids),
        }
    )


def compute_feature_output_hash(feature: ScenarioFeatureSnapshot) -> str:
    return hash_payload(
        {
            "version": SCENARIO_FEATURE_VERSION,
            "scores": {
                "confidence": feature.scenario_confidence_score,
                "uncertainty": feature.scenario_uncertainty_score,
                "sentiment": feature.sentiment_score,
                "consensus": feature.consensus_score,
                "polarization": feature.polarization_score,
                "narrative_risk": feature.narrative_risk_score,
                "shock_risk": feature.shock_risk_score,
                "adoption_or_support": feature.adoption_or_support_score,
                "opposition": feature.opposition_score,
            },
            "key_scenario_labels": sorted(feature.key_scenario_labels),
            "reason_codes": sorted(feature.reason_codes),
            "evidence": feature.evidence,
        }
    )


def scenario_object_id(prefix: str, payload: dict[str, Any]) -> str:
    return f"{prefix}_{hash_payload(payload)[:24]}"


def hash_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
