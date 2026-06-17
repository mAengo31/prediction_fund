"""Synchronous scenario import runner."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scenario.enums import ScenarioRunMode, ScenarioRunStatus
from prediction_desk.scenario.models import (
    SCENARIO_RUNNER_VERSION,
    ScenarioArtifact,
    ScenarioFeatureSnapshot,
    ScenarioRun,
    ScenarioRunConfig,
    ScenarioRunResult,
    ScenarioRunSummary,
    ScenarioSeedBundle,
    scenario_object_id,
)
from prediction_desk.scenario.service import ScenarioService, ScenarioServiceError


class ScenarioRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_scenario_import(
    config: ScenarioRunConfig,
    *,
    repo: PredictionMarketRepository | None = None,
) -> ScenarioRunResult:
    if repo is not None:
        return _run_scenario_import(repo, config)
    with session_scope() as session:
        return _run_scenario_import(PredictionMarketRepository(session), config)


def _run_scenario_import(
    repo: PredictionMarketRepository,
    config: ScenarioRunConfig,
) -> ScenarioRunResult:
    created_at = datetime.now(tz=UTC)
    run = ScenarioRun(
        scenario_run_id=scenario_object_id(
            "scenario_run",
            {
                "created_at": created_at,
                "mode": config.mode.value,
                "asof_timestamp": config.asof_timestamp,
            },
        ),
        name=config.name,
        created_at=created_at,
        started_at=created_at,
        status=ScenarioRunStatus.RUNNING,
        asof_timestamp=config.asof_timestamp,
        market_ids=list(config.market_ids or []),
        mode=config.mode,
        max_items=config.max_items,
        config=config.model_dump(mode="json"),
        metadata={**config.metadata, "runner_version": SCENARIO_RUNNER_VERSION},
    )
    repo.save_scenario_run(run)
    service = ScenarioService(repo)
    seeds: list[ScenarioSeedBundle] = []
    artifacts: list[ScenarioArtifact] = []
    features: list[ScenarioFeatureSnapshot] = []
    errors: list[dict[str, str]] = []
    try:
        if config.mode == ScenarioRunMode.BUILD_SEEDS_ONLY:
            for market_id in _limited(config.market_ids or [], config.max_items):
                try:
                    seeds.append(
                        service.build_seed_bundle_for_market(
                            market_id,
                            config.asof_timestamp,
                            force=config.force,
                        )
                    )
                except ScenarioServiceError as exc:
                    errors.append({"market_id": market_id, "code": exc.code})
        elif config.mode == ScenarioRunMode.IMPORT_FIXTURES:
            artifacts = service.import_fixture_artifacts(
                market_ids=config.market_ids,
                asof_timestamp=config.asof_timestamp,
                fixture_dir=config.fixture_dir,
                force=config.force,
            )[: config.max_items]
            for artifact in artifacts:
                try:
                    features.append(
                        service.normalize_scenario_artifact(
                            artifact.scenario_artifact_id,
                            force=config.force,
                        )
                    )
                except ScenarioServiceError as exc:
                    errors.append(
                        {"artifact_id": artifact.scenario_artifact_id, "code": exc.code}
                    )
        elif config.mode == ScenarioRunMode.IMPORT_MANUAL_ARTIFACTS:
            for path in _limited(config.manual_file_paths or [], config.max_items):
                try:
                    artifact = service.import_manual_artifact(
                        file_path=path,
                        asof_timestamp=config.asof_timestamp,
                        force=config.force,
                    )
                    artifacts.append(artifact)
                    features.append(
                        service.normalize_scenario_artifact(
                            artifact.scenario_artifact_id,
                            force=config.force,
                        )
                    )
                except ScenarioServiceError as exc:
                    errors.append({"file_path": path, "code": exc.code})
        elif config.mode == ScenarioRunMode.NORMALIZE_EXISTING_ARTIFACTS:
            market_filter = config.market_ids[0] if config.market_ids else None
            existing = repo.list_scenario_artifacts(
                market_id=market_filter,
                asof_timestamp=config.asof_timestamp,
                limit=config.max_items,
            )
            artifacts = list(existing)
            for artifact in existing:
                try:
                    features.append(
                        service.normalize_scenario_artifact(
                            artifact.scenario_artifact_id,
                            force=config.force,
                        )
                    )
                except ScenarioServiceError as exc:
                    errors.append(
                        {"artifact_id": artifact.scenario_artifact_id, "code": exc.code}
                    )
        summary = _summary(run.scenario_run_id, seeds, artifacts, features)
        repo.save_scenario_run_summary(summary)
        status = ScenarioRunStatus.COMPLETED if not errors else ScenarioRunStatus.PARTIAL
        completed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": status,
                "seed_bundles_created": len(seeds),
                "artifacts_imported": len(artifacts),
                "features_created": len(features),
                "errors_count": len(errors),
                "metadata": {**run.metadata, "errors": errors},
            }
        )
        repo.update_scenario_run(completed)
        return ScenarioRunResult(
            run=completed,
            seed_bundles=seeds,
            artifacts=artifacts,
            features=features,
            summary=summary,
        )
    except Exception as exc:
        failed = run.model_copy(
            update={
                "completed_at": datetime.now(tz=UTC),
                "status": ScenarioRunStatus.FAILED,
                "errors_count": len(errors) + 1,
                "metadata": {**run.metadata, "errors": errors, "error": str(exc)},
            }
        )
        repo.update_scenario_run(failed)
        raise


def _summary(
    run_id: str,
    seeds: list[ScenarioSeedBundle],
    artifacts: list[ScenarioArtifact],
    features: list[ScenarioFeatureSnapshot],
) -> ScenarioRunSummary:
    score_names = [
        "scenario_confidence_score",
        "scenario_uncertainty_score",
        "sentiment_score",
        "consensus_score",
        "polarization_score",
        "narrative_risk_score",
        "shock_risk_score",
    ]
    averages: dict[str, Decimal] = {}
    for name in score_names:
        values = [getattr(feature, name) for feature in features]
        present = [Decimal(value) for value in values if value is not None]
        if present:
            averages[name] = sum(present, Decimal("0")) / Decimal(len(present))
    reason_counts: dict[str, int] = {}
    markets = set()
    for feature in features:
        markets.add(feature.market_id)
        for code in feature.reason_codes:
            reason_counts[code] = reason_counts.get(code, 0) + 1
    for artifact in artifacts:
        if artifact.market_id:
            markets.add(artifact.market_id)
    return ScenarioRunSummary(
        summary_id=scenario_object_id(
            "scenario_run_summary",
            {"run_id": run_id, "features": [feature.output_hash for feature in features]},
        ),
        scenario_run_id=run_id,
        created_at=datetime.now(tz=UTC),
        total_seed_bundles=len(seeds),
        total_artifacts=len(artifacts),
        total_features=len(features),
        average_scores=averages,
        reason_code_counts=dict(sorted(reason_counts.items())),
        markets_processed=len(markets),
        metadata={"summary_version": "scenario_run_summary_v1"},
    )


def _limited(values: list[str], limit: int) -> list[str]:
    return list(values)[:limit]
