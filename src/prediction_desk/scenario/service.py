"""Service layer for local scenario artifact import and normalization."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scenario.adapters import (
    FixtureMiroFishArtifactAdapter,
    ScenarioAdapterError,
    ScenarioArtifactInput,
    load_manual_artifact,
)
from prediction_desk.scenario.enums import (
    ScenarioArtifactSourceType,
    ScenarioEngine,
    ScenarioRunMode,
)
from prediction_desk.scenario.models import (
    ScenarioArtifact,
    ScenarioFeatureSnapshot,
    ScenarioRun,
    ScenarioRunSummary,
    ScenarioSeedBundle,
    ScenarioSimulationSpec,
    compute_artifact_id,
    compute_artifact_payload_hash,
    compute_spec_id,
)
from prediction_desk.scenario.normalizers import normalize_mirofish_style_artifact
from prediction_desk.scenario.seeds import build_scenario_seed_bundle


class ScenarioServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class ScenarioService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def build_seed_bundle_for_market(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        force: bool = False,
    ) -> ScenarioSeedBundle:
        try:
            return build_scenario_seed_bundle(
                market_id,
                asof_timestamp,
                force=force,
                repo=self.repo,
            )
        except ValueError as exc:
            raise ScenarioServiceError(str(exc)) from exc

    def create_scenario_spec(
        self,
        seed_bundle_id: str,
        scenario_goal: str,
        *,
        horizon_hours: int | None = None,
        variables: dict[str, Any] | None = None,
        constraints: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ScenarioSimulationSpec:
        seed = self.repo.get_scenario_seed_bundle(seed_bundle_id)
        if seed is None:
            raise ScenarioServiceError("scenario_seed_bundle_not_found")
        spec = ScenarioSimulationSpec(
            scenario_spec_id=compute_spec_id(seed_bundle_id, scenario_goal, horizon_hours),
            seed_bundle_id=seed_bundle_id,
            market_id=seed.market_id,
            asof_timestamp=seed.asof_timestamp,
            created_at=datetime.now(tz=UTC),
            scenario_engine=ScenarioEngine.MIROFISH_STYLE,
            scenario_goal=scenario_goal,
            horizon_hours=horizon_hours,
            variables=dict(variables or {}),
            constraints=dict(constraints or {}),
            metadata=dict(metadata or {}),
        )
        return self.repo.save_scenario_simulation_spec(spec)

    def import_fixture_artifacts(
        self,
        *,
        market_ids: list[str] | None = None,
        asof_timestamp: datetime | None = None,
        fixture_dir: str | None = None,
        force: bool = False,
    ) -> list[ScenarioArtifact]:
        asof = asof_timestamp or datetime.now(tz=UTC)
        try:
            inputs = FixtureMiroFishArtifactAdapter().load_artifacts(
                asof_timestamp=asof,
                market_ids=market_ids,
                fixture_dir=fixture_dir,
            )
        except ScenarioAdapterError as exc:
            raise ScenarioServiceError(exc.code, exc.message) from exc
        return [self._save_artifact_input(item, force=force) for item in inputs]

    def import_manual_artifact(
        self,
        *,
        file_path: str,
        market_id: str | None = None,
        asof_timestamp: datetime | None = None,
        seed_bundle_id: str | None = None,
        force: bool = False,
    ) -> ScenarioArtifact:
        asof = asof_timestamp or datetime.now(tz=UTC)
        try:
            item = load_manual_artifact(
                file_path=file_path,
                asof_timestamp=asof,
                market_id=market_id,
            )
        except ScenarioAdapterError as exc:
            raise ScenarioServiceError(exc.code, exc.message) from exc
        artifact = self._artifact_from_input(item, seed_bundle_id=seed_bundle_id)
        existing = self.repo.find_scenario_artifact_by_hash(artifact.payload_hash)
        if existing is not None and not force:
            return existing
        return self.repo.save_scenario_artifact(artifact)

    def normalize_scenario_artifact(
        self,
        scenario_artifact_id: str,
        *,
        force: bool = False,
    ) -> ScenarioFeatureSnapshot:
        artifact = self.repo.get_scenario_artifact(scenario_artifact_id)
        if artifact is None:
            raise ScenarioServiceError("scenario_artifact_not_found")
        seed = (
            self.repo.get_scenario_seed_bundle(artifact.seed_bundle_id)
            if artifact.seed_bundle_id
            else None
        )
        try:
            feature = normalize_mirofish_style_artifact(artifact, seed)
        except ValueError as exc:
            raise ScenarioServiceError(str(exc)) from exc
        existing = self.repo.find_scenario_feature_snapshot_by_hash(feature.input_hash)
        if existing is not None and not force:
            return existing
        return self.repo.save_scenario_feature_snapshot(feature)

    def normalize_scenario_artifacts_for_market(
        self,
        market_id: str,
        *,
        asof_timestamp: datetime | None = None,
        force: bool = False,
    ) -> list[ScenarioFeatureSnapshot]:
        artifacts = self.repo.list_scenario_artifacts(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            limit=1000,
        )
        return [
            self.normalize_scenario_artifact(
                artifact.scenario_artifact_id,
                force=force,
            )
            for artifact in artifacts
        ]

    def get_latest_scenario_feature_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
    ) -> ScenarioFeatureSnapshot | None:
        return self.repo.get_latest_scenario_feature_asof(market_id, asof_timestamp)

    def list_scenario_features(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ScenarioFeatureSnapshot]:
        return self.repo.list_scenario_features(
            market_id=market_id,
            limit=limit,
            offset=offset,
        )

    def list_scenario_artifacts(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ScenarioArtifact]:
        return self.repo.list_scenario_artifacts(
            market_id=market_id,
            limit=limit,
            offset=offset,
        )

    def list_scenario_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ScenarioRun]:
        return self.repo.list_scenario_runs(limit=limit, offset=offset)

    def get_scenario_run(self, scenario_run_id: str) -> ScenarioRun:
        run = self.repo.get_scenario_run(scenario_run_id)
        if run is None:
            raise ScenarioServiceError("scenario_run_not_found")
        return run

    def get_scenario_run_summary(self, scenario_run_id: str) -> ScenarioRunSummary:
        summary = self.repo.get_scenario_run_summary(scenario_run_id)
        if summary is None:
            raise ScenarioServiceError("scenario_run_summary_not_found")
        return summary

    def _save_artifact_input(
        self,
        item: ScenarioArtifactInput,
        *,
        force: bool,
    ) -> ScenarioArtifact:
        seed = (
            self.build_seed_bundle_for_market(
                item.market_id,
                item.asof_timestamp,
                force=force,
            )
            if item.market_id
            else None
        )
        artifact = self._artifact_from_input(
            item,
            seed_bundle_id=seed.seed_bundle_id if seed else None,
        )
        existing = self.repo.find_scenario_artifact_by_hash(artifact.payload_hash)
        if existing is not None and not force:
            return existing
        return self.repo.save_scenario_artifact(artifact)

    def _artifact_from_input(
        self,
        item: ScenarioArtifactInput,
        *,
        seed_bundle_id: str | None,
    ) -> ScenarioArtifact:
        payload_hash = compute_artifact_payload_hash(item.raw_payload, item.raw_text)
        source_path = str(Path(item.source_path).resolve()) if item.source_path else None
        return ScenarioArtifact(
            scenario_artifact_id=compute_artifact_id(
                payload_hash=payload_hash,
                source_type=item.source_type,
                market_id=item.market_id,
                asof_timestamp=item.asof_timestamp,
            ),
            seed_bundle_id=seed_bundle_id,
            market_id=item.market_id,
            asof_timestamp=item.asof_timestamp,
            captured_at=item.asof_timestamp,
            available_at=item.asof_timestamp,
            artifact_type=item.artifact_type,
            source_type=item.source_type,
            source_path=source_path,
            raw_payload=item.raw_payload,
            raw_text=item.raw_text,
            payload_hash=payload_hash,
            schema_version=item.schema_version,
            is_simulated=True
            if item.source_type
            in {
                ScenarioArtifactSourceType.FIXTURE,
                ScenarioArtifactSourceType.MANUAL_IMPORT,
            }
            else True,
            metadata={"adapter": "fixture_mirofish_style_v1"},
        )


def build_seed_bundle_for_market(
    market_id: str,
    asof_timestamp: datetime,
    *,
    database_url: str | None = None,
    force: bool = False,
) -> ScenarioSeedBundle:
    with session_scope(database_url) as session:
        return ScenarioService(
            PredictionMarketRepository(session)
        ).build_seed_bundle_for_market(market_id, asof_timestamp, force=force)


def mode_from_string(value: str) -> ScenarioRunMode:
    return ScenarioRunMode(str(value).upper())
