"""API routes for stored market data and deterministic trust verdicts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import Engine

from prediction_desk.api.auth import require_api_token
from prediction_desk.api.dependencies import get_repository
from prediction_desk.api.schemas import (
    SERVICE_NAME,
    HealthResponse,
    MarketSummary,
    ReadinessResponse,
    VersionResponse,
)
from prediction_desk.config import Settings
from prediction_desk.dataops.models import (
    BackfillJob,
    BackfillJobCreateRequest,
    BackfillJobResult,
    BackfillSegment,
    CollectionPlan,
    CollectionRun,
    CollectionRunResult,
    DataCoverageComputeRequest,
    DataCoverageReport,
    DataGap,
    DataGapDetectRequest,
    DataOpsCollectionRunRequest,
    DataOpsCycleConfig,
    DataOpsCycleRequest,
    DataOpsCycleResult,
    MarketUniverseDefinition,
    MarketUniverseMember,
)
from prediction_desk.dataops.runner import run_dataops_cycle
from prediction_desk.dataops.service import DataOpsService, DataOpsServiceError
from prediction_desk.divergence.enums import DivergenceStatus
from prediction_desk.divergence.models import (
    CrossVenueDivergenceAnalysis,
    CrossVenueDivergenceAssessment,
    CrossVenueDivergenceRun,
    CrossVenueDivergenceRunConfig,
    CrossVenueDivergenceRunRequest,
    CrossVenueDivergenceRunResult,
    CrossVenueDivergenceRunSummary,
    CrossVenueDivergenceSignal,
    CrossVenueDivergenceSnapshot,
    DivergenceAnalyzeRequest,
)
from prediction_desk.divergence.runner import DivergenceRunError, run_divergence_scan
from prediction_desk.divergence.service import DivergenceService, DivergenceServiceError
from prediction_desk.domain.enums import MarketStatus
from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.equivalence.enums import ComparisonPermission, EquivalenceStatus
from prediction_desk.equivalence.models import (
    EquivalenceAssessmentResponse,
    EquivalenceAssessRequest,
    EquivalenceCandidate,
    EquivalenceCandidatesRequest,
    EquivalenceClass,
    EquivalenceRun,
    EquivalenceRunConfig,
    EquivalenceRunRequest,
    EquivalenceRunResult,
    EquivalenceRunSummary,
    MarketEquivalenceAssessment,
    OutcomeEquivalenceMapping,
)
from prediction_desk.equivalence.runner import EquivalenceRunError, run_equivalence_scan
from prediction_desk.equivalence.service import EquivalenceService, EquivalenceServiceError
from prediction_desk.ingestion.models import (
    FixtureIngestionRequest,
    IngestionCursor,
    IngestionError,
    IngestionRun,
    IngestionRunResult,
    PublicSampleIngestionRequest,
    VenueMarketMapping,
)
from prediction_desk.ingestion.scheduler import (
    IngestionRunOnceRequest,
    IngestionRunOnceResult,
    run_ingestion_once,
)
from prediction_desk.ingestion.service import IngestionService, IngestionServiceError
from prediction_desk.integrity.models import (
    IntegrityAnalysis,
    IntegrityAnalyzeRequest,
    IntegrityAssessment,
    IntegrityRun,
    IntegrityRunConfig,
    IntegrityRunResult,
    IntegrityRunSummary,
    IntegritySignal,
    MarketIntegrityAnalyzeRequest,
)
from prediction_desk.integrity.runner import IntegrityRunError, run_integrity_scan
from prediction_desk.integrity.service import IntegrityService, IntegrityServiceError
from prediction_desk.marketdata.models import (
    DataQualityRequest,
    MarketDataDerivationResult,
    MarketDataLatest,
    MarketDataQualityReport,
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
)
from prediction_desk.marketdata.service import MarketDataService, MarketDataServiceError
from prediction_desk.paper.enums import PaperOrderStatus
from prediction_desk.paper.models import (
    PaperExecutionPolicy,
    PaperFill,
    PaperOrder,
    PaperPortfolioSnapshot,
    PaperPositionSnapshot,
    PaperSimulateIntentRequest,
    PaperSimulationResult,
    PaperSimulationRun,
    PaperSimulationRunConfig,
    PaperSimulationRunRequest,
    PaperSimulationRunResult,
    PaperSimulationRunSummary,
    compute_trade_intent_from_request,
)
from prediction_desk.paper.runner import PaperRunError, run_paper_simulation
from prediction_desk.paper.service import PaperExecutionService, PaperServiceError
from prediction_desk.persistence.database import (
    check_database_connection,
    database_appears_migrated,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction
from prediction_desk.pretrade.models import (
    ExposureSnapshot,
    ExposureSnapshotCreate,
    MarketRestrictionRule,
    MarketRestrictionRuleCreate,
    PreTradeCheckMarketRequest,
    PreTradeCheckRequest,
    PreTradeCheckResponse,
    PreTradeDecision,
    PreTradePolicy,
    PreTradeRun,
    PreTradeRunConfig,
    PreTradeRunRequest,
    PreTradeRunResult,
    PreTradeRunSummary,
    TradeIntent,
    compute_trade_intent_id,
)
from prediction_desk.pretrade.runner import PreTradeRunError, run_pretrade_checks
from prediction_desk.pretrade.service import PreTradeService, PreTradeServiceError
from prediction_desk.replay.models import (
    ReplayRun,
    ReplayRunConfig,
    ReplayRunResponse,
    ReplayRunSummary,
    ReplayStep,
)
from prediction_desk.replay.runner import ReplayError
from prediction_desk.replay.service import ReplayService
from prediction_desk.research.models import (
    ResearchAttributionReport,
    ResearchDecisionTrace,
    ResearchFeatureBuildRequest,
    ResearchFeatureSnapshot,
    ResearchIntentProposal,
    ResearchLatestResponse,
    ResearchProposalEvaluateRequest,
    ResearchProposalsGenerateRequest,
    ResearchRun,
    ResearchRunConfig,
    ResearchRunRequest,
    ResearchRunResult,
    ResearchRunSummary,
    ResearchSignal,
    ResearchSignalsGenerateRequest,
    ResearchStrategyDefinition,
)
from prediction_desk.research.runner import ResearchRunError, run_research_simulation
from prediction_desk.research.service import ResearchService, ResearchServiceError
from prediction_desk.resolution.models import ResolutionAnalysis, RuleSnapshotDiff
from prediction_desk.resolution.service import ResolutionCorpusError, ResolutionCorpusService
from prediction_desk.scenario.models import (
    ScenarioArtifact,
    ScenarioFeatureSnapshot,
    ScenarioImportFixturesRequest,
    ScenarioImportManualRequest,
    ScenarioRun,
    ScenarioRunConfig,
    ScenarioRunRequest,
    ScenarioRunResult,
    ScenarioRunSummary,
    ScenarioSeedBuildRequest,
    ScenarioSeedBundle,
    ScenarioSimulationSpec,
    ScenarioSpecCreateRequest,
)
from prediction_desk.scenario.runner import ScenarioRunError, run_scenario_import
from prediction_desk.scenario.service import ScenarioService, ScenarioServiceError
from prediction_desk.scoring.trust_verdict import build_trust_verdict
from prediction_desk.vendor_data.models import (
    VendorDatasetSource,
    VendorDatasetSourceCreate,
    VendorDataValidationReport,
    VendorDryRunImportRequest,
    VendorEvaluateRequest,
    VendorEvaluationReport,
    VendorImportDryRun,
    VendorSampleFile,
    VendorSampleLoadRequest,
    VendorSchemaInspection,
)
from prediction_desk.vendor_data.service import VendorDataService, VendorDataServiceError
from prediction_desk.workbench.enums import ReviewPriorityBucket, ReviewStatus
from prediction_desk.workbench.models import (
    CrossVenueComparisonCard,
    DeskReviewNote,
    DeskReviewNoteCreate,
    DeskWatchlist,
    MarketDecisionCard,
    MarketReviewQueueItem,
    WorkbenchComparisonCardRequest,
    WorkbenchDecisionCardRequest,
    WorkbenchQueueBuildRequest,
    WorkbenchQueueItemStatusUpdateRequest,
    WorkbenchQueueSummary,
    WorkbenchRun,
    WorkbenchRunConfig,
    WorkbenchRunRequest,
    WorkbenchRunResult,
    WorkbenchRunSummary,
    WorkbenchStatusSummary,
)
from prediction_desk.workbench.runner import WorkbenchRunError, run_workbench_build
from prediction_desk.workbench.service import WorkbenchService, WorkbenchServiceError

health_router = APIRouter()
v1_router = APIRouter(prefix="/api/v1")


@health_router.get("/healthz", response_model=HealthResponse)
def healthz(request: Request) -> HealthResponse:
    settings = _settings(request)
    return _health_response(settings)


@health_router.get(
    "/readyz",
    response_model=ReadinessResponse,
    dependencies=[Depends(require_api_token)],
)
def readyz(request: Request) -> ReadinessResponse:
    engine = cast(Engine, request.app.state.engine)
    if not check_database_connection(engine):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unreachable",
        )
    settings = _settings(request)
    return ReadinessResponse(
        status="ok",
        service=SERVICE_NAME,
        version=settings.app_version,
        environment=settings.app_env,
        database="ok",
        migrated=database_appears_migrated(engine),
    )


@health_router.get(
    "/version",
    response_model=VersionResponse,
    dependencies=[Depends(require_api_token)],
)
def version(request: Request) -> VersionResponse:
    settings = _settings(request)
    return VersionResponse(
        service=SERVICE_NAME,
        version=settings.app_version,
        commit=settings.git_commit,
        environment=settings.app_env,
    )


@v1_router.get(
    "/markets",
    response_model=list[MarketSummary],
    dependencies=[Depends(require_api_token)],
)
def list_markets(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    status_filter: Annotated[MarketStatus | None, Query(alias="status")] = None,
    venue_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketSummary]:
    markets = repo.list_markets(
        status=status_filter,
        venue_id=venue_id,
        limit=limit,
        offset=offset,
    )
    return [MarketSummary.from_market(market) for market in markets]


@v1_router.get(
    "/markets/{market_id}",
    response_model=Market,
    dependencies=[Depends(require_api_token)],
)
def get_market(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> Market:
    return _market_or_404(repo, market_id)


@v1_router.get(
    "/markets/{market_id}/rule-snapshots/latest",
    response_model=MarketRuleSnapshot,
    dependencies=[Depends(require_api_token)],
)
def get_latest_rule_snapshot(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketRuleSnapshot:
    _market_or_404(repo, market_id)
    snapshot = repo.get_latest_rule_snapshot(market_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule_snapshot_not_found")
    return snapshot


@v1_router.get(
    "/markets/{market_id}/trust-verdicts/latest",
    response_model=TrustVerdict,
    dependencies=[Depends(require_api_token)],
)
def get_latest_trust_verdict(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> TrustVerdict:
    _market_or_404(repo, market_id)
    verdict = repo.get_latest_trust_verdict(market_id)
    if verdict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="trust_verdict_not_found")
    return verdict


@v1_router.post(
    "/markets/{market_id}/trust-verdicts/recompute",
    response_model=TrustVerdict,
    dependencies=[Depends(require_api_token)],
)
def recompute_trust_verdict(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> TrustVerdict:
    market = _market_or_404(repo, market_id)
    asof_timestamp = datetime.now(tz=UTC)
    rule_snapshot = repo.get_latest_rule_snapshot(market_id)
    ambiguity_assessment = None
    if rule_snapshot is not None:
        try:
            ambiguity_assessment = ResolutionCorpusService(repo).analyze_latest_rule_snapshot(
                market_id
            ).ambiguity_assessment
        except ResolutionCorpusError:
            ambiguity_assessment = repo.get_ambiguity_assessment_for_rule_snapshot(
                rule_snapshot.rule_snapshot_id
            )
    integrity_assessment = repo.get_latest_integrity_assessment_asof(
        market_id,
        asof_timestamp,
    )
    equivalence_assessments = repo.list_latest_equivalence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
    )
    divergence_assessments = repo.list_latest_divergence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
    )
    verdict = build_trust_verdict(
        market=market,
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=repo.get_latest_orderbook_snapshot(market_id),
        asof_timestamp=asof_timestamp,
        ambiguity_assessment=ambiguity_assessment,
        integrity_assessment=integrity_assessment,
        equivalence_assessments=equivalence_assessments,
        divergence_assessments=divergence_assessments,
    )
    return repo.save_trust_verdict(verdict)


@v1_router.post(
    "/markets/{market_id}/resolution/analyze-latest",
    response_model=ResolutionAnalysis,
    dependencies=[Depends(require_api_token)],
)
def analyze_latest_resolution(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResolutionAnalysis:
    try:
        return ResolutionCorpusService(repo).analyze_latest_rule_snapshot(market_id)
    except ResolutionCorpusError as exc:
        raise _resolution_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/resolution/latest",
    response_model=ResolutionAnalysis,
    dependencies=[Depends(require_api_token)],
)
def get_latest_resolution_analysis(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResolutionAnalysis:
    try:
        return ResolutionCorpusService(repo).get_latest_resolution_analysis(market_id)
    except ResolutionCorpusError as exc:
        raise _resolution_http_error(exc) from exc


@v1_router.get(
    "/rule-snapshots/{rule_snapshot_id}/resolution",
    response_model=ResolutionAnalysis,
    dependencies=[Depends(require_api_token)],
)
def get_rule_snapshot_resolution_analysis(
    rule_snapshot_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResolutionAnalysis:
    try:
        return ResolutionCorpusService(repo).get_resolution_analysis_for_rule_snapshot(
            rule_snapshot_id
        )
    except ResolutionCorpusError as exc:
        raise _resolution_http_error(exc) from exc


@v1_router.post(
    "/markets/{market_id}/rule-snapshots/diff-latest",
    response_model=RuleSnapshotDiff,
    dependencies=[Depends(require_api_token)],
)
def diff_latest_rule_snapshots(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> RuleSnapshotDiff:
    try:
        return ResolutionCorpusService(repo).diff_latest_two_rule_snapshots(market_id)
    except ResolutionCorpusError as exc:
        raise _resolution_http_error(exc) from exc


@v1_router.post(
    "/replay/runs",
    response_model=ReplayRunResponse,
    dependencies=[Depends(require_api_token)],
)
def create_replay_run(
    config: ReplayRunConfig,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ReplayRunResponse:
    try:
        result = ReplayService(repo).run(config)
    except ReplayError as exc:
        raise _replay_http_error(exc) from exc
    return ReplayRunResponse(run=result.run, summary=result.summary)


@v1_router.get(
    "/replay/runs/{run_id}",
    response_model=ReplayRun,
    dependencies=[Depends(require_api_token)],
)
def get_replay_run(
    run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ReplayRun:
    try:
        return ReplayService(repo).get_run(run_id)
    except ReplayError as exc:
        raise _replay_http_error(exc) from exc


@v1_router.get(
    "/replay/runs/{run_id}/steps",
    response_model=list[ReplayStep],
    dependencies=[Depends(require_api_token)],
)
def list_replay_steps(
    run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ReplayStep]:
    try:
        return ReplayService(repo).list_steps(run_id, limit=limit, offset=offset)
    except ReplayError as exc:
        raise _replay_http_error(exc) from exc


@v1_router.get(
    "/replay/runs/{run_id}/summary",
    response_model=ReplayRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_replay_summary(
    run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ReplayRunSummary:
    try:
        return ReplayService(repo).get_summary(run_id)
    except ReplayError as exc:
        raise _replay_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/market-data/latest",
    response_model=MarketDataLatest,
    dependencies=[Depends(require_api_token)],
)
def get_latest_market_data(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> MarketDataLatest:
    try:
        return MarketDataService(repo).get_latest_market_data_asof(
            market_id,
            asof_timestamp or datetime.now(tz=UTC),
        )
    except MarketDataServiceError as exc:
        raise _marketdata_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/market-data/prices",
    response_model=list[MarketPriceSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_market_price_snapshots(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketPriceSnapshot]:
    _market_or_404(repo, market_id)
    return MarketDataService(repo).list_price_snapshots(
        market_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/markets/{market_id}/market-data/liquidity",
    response_model=list[MarketLiquiditySnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_market_liquidity_snapshots(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketLiquiditySnapshot]:
    _market_or_404(repo, market_id)
    return MarketDataService(repo).list_liquidity_snapshots(
        market_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/markets/{market_id}/market-data/derive",
    response_model=MarketDataDerivationResult,
    dependencies=[Depends(require_api_token)],
)
def derive_market_data(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    force: bool = False,
) -> MarketDataDerivationResult:
    try:
        return MarketDataService(repo).derive_market_data_for_market(
            market_id,
            force=force,
        )
    except MarketDataServiceError as exc:
        raise _marketdata_http_error(exc) from exc


@v1_router.post(
    "/markets/{market_id}/data-quality/recompute",
    response_model=MarketDataQualityReport,
    dependencies=[Depends(require_api_token)],
)
def recompute_data_quality(
    market_id: str,
    request_body: DataQualityRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketDataQualityReport:
    try:
        return MarketDataService(repo).compute_market_data_quality(
            market_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            freshness_threshold_seconds=request_body.freshness_threshold_seconds,
            wide_spread_threshold=request_body.wide_spread_threshold,
        )
    except MarketDataServiceError as exc:
        raise _marketdata_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/data-quality/latest",
    response_model=MarketDataQualityReport,
    dependencies=[Depends(require_api_token)],
)
def get_latest_data_quality(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> MarketDataQualityReport:
    _market_or_404(repo, market_id)
    report = repo.get_latest_quality_report_asof(
        market_id,
        asof_timestamp or datetime.now(tz=UTC),
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="market_data_quality_report_not_found",
        )
    return report


@v1_router.post(
    "/ingestion/fixtures/{venue_name}",
    response_model=IngestionRunResult,
    dependencies=[Depends(require_api_token)],
)
def ingest_fixture_payloads(
    venue_name: str,
    request_body: FixtureIngestionRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IngestionRunResult:
    try:
        return IngestionService(repo).ingest_fixture_payloads(
            venue_name=venue_name,
            fixture_dir=Path(request_body.fixture_dir) if request_body.fixture_dir else None,
            captured_at=request_body.captured_at,
            analyze_rules=request_body.analyze_rules,
            recompute_verdicts=request_body.recompute_verdicts,
        )
    except IngestionServiceError as exc:
        raise _ingestion_http_error(exc) from exc


@v1_router.post(
    "/ingestion/public-sample/{venue_name}",
    response_model=IngestionRunResult,
    dependencies=[Depends(require_api_token)],
)
def ingest_public_sample(
    venue_name: str,
    request_body: PublicSampleIngestionRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IngestionRunResult:
    try:
        return IngestionService(repo).ingest_public_market_sample(
            venue_name=venue_name,
            limit=request_body.limit,
            allow_network=request_body.allow_network,
            analyze_rules=request_body.analyze_rules,
            recompute_verdicts=request_body.recompute_verdicts,
        )
    except IngestionServiceError as exc:
        raise _ingestion_http_error(exc) from exc


@v1_router.get(
    "/ingestion/runs",
    response_model=list[IngestionRun],
    dependencies=[Depends(require_api_token)],
)
def list_ingestion_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    venue_name: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IngestionRun]:
    return IngestionService(repo).list_runs(
        venue_name=venue_name,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/ingestion/runs/{ingestion_run_id}",
    response_model=IngestionRun,
    dependencies=[Depends(require_api_token)],
)
def get_ingestion_run(
    ingestion_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IngestionRun:
    try:
        return IngestionService(repo).get_run(ingestion_run_id)
    except IngestionServiceError as exc:
        raise _ingestion_http_error(exc) from exc


@v1_router.get(
    "/ingestion/runs/{ingestion_run_id}/errors",
    response_model=list[IngestionError],
    dependencies=[Depends(require_api_token)],
)
def list_ingestion_errors(
    ingestion_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[IngestionError]:
    try:
        return IngestionService(repo).list_errors(ingestion_run_id)
    except IngestionServiceError as exc:
        raise _ingestion_http_error(exc) from exc


@v1_router.get(
    "/venue-mappings",
    response_model=list[VenueMarketMapping],
    dependencies=[Depends(require_api_token)],
)
def list_venue_mappings(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    venue_name: str | None = None,
    canonical_market_id: str | None = None,
    external_market_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[VenueMarketMapping]:
    return repo.list_venue_market_mappings(
        venue_name=venue_name,
        canonical_market_id=canonical_market_id,
        external_market_id=external_market_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/ingestion/cursors",
    response_model=list[IngestionCursor],
    dependencies=[Depends(require_api_token)],
)
def list_ingestion_cursors(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    venue_name: str | None = None,
    canonical_market_id: str | None = None,
    external_market_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IngestionCursor]:
    return repo.list_ingestion_cursors(
        venue_name=venue_name,
        canonical_market_id=canonical_market_id,
        external_market_id=external_market_id,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/ingestion/run-once",
    response_model=IngestionRunOnceResult,
    dependencies=[Depends(require_api_token)],
)
def ingestion_run_once(
    request_body: IngestionRunOnceRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IngestionRunOnceResult:
    try:
        return run_ingestion_once(
            venue_name=request_body.venue_name,
            mode=request_body.mode,
            limit=request_body.limit,
            allow_network=request_body.allow_network,
            analyze_rules=request_body.analyze_rules,
            recompute_verdicts=request_body.recompute_verdicts,
            derive_market_data=request_body.derive_market_data,
            compute_quality=request_body.compute_quality,
            metadata=request_body.metadata,
            repo=repo,
        )
    except IngestionServiceError as exc:
        raise _ingestion_http_error(exc) from exc


@v1_router.post(
    "/integrity/analyze",
    response_model=list[IntegrityAssessment],
    dependencies=[Depends(require_api_token)],
)
def analyze_integrity(
    request_body: IntegrityAnalyzeRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[IntegrityAssessment]:
    service = IntegrityService(repo)
    asof_timestamp = request_body.asof_timestamp or datetime.now(tz=UTC)
    try:
        return service.analyze_integrity_for_all_markets(
            asof_timestamp,
            market_ids=request_body.market_ids,
            limit=100,
            force=request_body.force,
            config=request_body.thresholds,
        )
    except IntegrityServiceError as exc:
        raise _integrity_http_error(exc) from exc


@v1_router.post(
    "/integrity/runs",
    response_model=IntegrityRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_integrity_run(
    config: IntegrityRunConfig,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IntegrityRunResult:
    try:
        return run_integrity_scan(config, repo=repo)
    except IntegrityRunError as exc:
        raise _integrity_run_http_error(exc) from exc


@v1_router.get(
    "/integrity/runs",
    response_model=list[IntegrityRun],
    dependencies=[Depends(require_api_token)],
)
def list_integrity_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IntegrityRun]:
    return repo.list_integrity_runs(limit=limit, offset=offset)


@v1_router.get(
    "/integrity/runs/{integrity_run_id}",
    response_model=IntegrityRun,
    dependencies=[Depends(require_api_token)],
)
def get_integrity_run(
    integrity_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IntegrityRun:
    run = repo.get_integrity_run(integrity_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="integrity_run_not_found")
    return run


@v1_router.get(
    "/integrity/runs/{integrity_run_id}/summary",
    response_model=IntegrityRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_integrity_run_summary(
    integrity_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IntegrityRunSummary:
    summary = repo.get_integrity_run_summary(integrity_run_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="integrity_run_summary_not_found",
        )
    return summary


@v1_router.get(
    "/markets/{market_id}/integrity/latest",
    response_model=IntegrityAssessment,
    dependencies=[Depends(require_api_token)],
)
def get_latest_integrity_assessment(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> IntegrityAssessment:
    try:
        return IntegrityService(repo).get_latest_integrity_assessment(
            market_id,
            asof_timestamp,
        )
    except IntegrityServiceError as exc:
        raise _integrity_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/integrity/signals",
    response_model=list[IntegritySignal],
    dependencies=[Depends(require_api_token)],
)
def list_market_integrity_signals(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IntegritySignal]:
    _market_or_404(repo, market_id)
    return IntegrityService(repo).list_integrity_signals(
        market_id=market_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/markets/{market_id}/integrity/assessments",
    response_model=list[IntegrityAssessment],
    dependencies=[Depends(require_api_token)],
)
def list_market_integrity_assessments(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IntegrityAssessment]:
    _market_or_404(repo, market_id)
    return IntegrityService(repo).list_integrity_assessments(
        market_id=market_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/markets/{market_id}/integrity/analyze",
    response_model=IntegrityAnalysis,
    dependencies=[Depends(require_api_token)],
)
def analyze_market_integrity(
    market_id: str,
    request_body: MarketIntegrityAnalyzeRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> IntegrityAnalysis:
    try:
        return IntegrityService(repo).analyze_market_integrity_details(
            market_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            config=request_body.thresholds,
            force=request_body.force,
        )
    except IntegrityServiceError as exc:
        raise _integrity_http_error(exc) from exc


@v1_router.post(
    "/equivalence/assess",
    response_model=EquivalenceAssessmentResponse,
    dependencies=[Depends(require_api_token)],
)
def assess_equivalence(
    request_body: EquivalenceAssessRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> EquivalenceAssessmentResponse:
    try:
        return EquivalenceService(repo).assess_market_equivalence(
            request_body.left_market_id,
            request_body.right_market_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            force=request_body.force,
            config=request_body.config,
        )
    except EquivalenceServiceError as exc:
        raise _equivalence_http_error(exc) from exc


@v1_router.post(
    "/equivalence/candidates",
    response_model=list[EquivalenceCandidate],
    dependencies=[Depends(require_api_token)],
)
def create_equivalence_candidates(
    request_body: EquivalenceCandidatesRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[EquivalenceCandidate]:
    try:
        return EquivalenceService(repo).generate_candidates(
            request_body.asof_timestamp or datetime.now(tz=UTC),
            market_ids=request_body.market_ids,
            venue_names=request_body.venue_names,
            min_candidate_score=request_body.min_candidate_score,
            max_pairs=request_body.max_pairs,
            force=request_body.force,
        )
    except EquivalenceServiceError as exc:
        raise _equivalence_http_error(exc) from exc


@v1_router.get(
    "/equivalence/candidates",
    response_model=list[EquivalenceCandidate],
    dependencies=[Depends(require_api_token)],
)
def list_equivalence_candidates(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquivalenceCandidate]:
    return EquivalenceService(repo).list_equivalence_candidates(
        market_id=market_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/equivalence/assessments",
    response_model=list[MarketEquivalenceAssessment],
    dependencies=[Depends(require_api_token)],
)
def list_equivalence_assessments(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    status_filter: Annotated[EquivalenceStatus | None, Query(alias="status")] = None,
    permission: ComparisonPermission | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketEquivalenceAssessment]:
    return EquivalenceService(repo).list_equivalence_assessments(
        market_id=market_id,
        status=status_filter,
        permission=permission,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/equivalence/assessments/{equivalence_assessment_id}",
    response_model=MarketEquivalenceAssessment,
    dependencies=[Depends(require_api_token)],
)
def get_equivalence_assessment(
    equivalence_assessment_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketEquivalenceAssessment:
    assessment = repo.get_market_equivalence_assessment(equivalence_assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equivalence_assessment_not_found",
        )
    return assessment


@v1_router.get(
    "/equivalence/assessments/{equivalence_assessment_id}/outcomes",
    response_model=list[OutcomeEquivalenceMapping],
    dependencies=[Depends(require_api_token)],
)
def list_equivalence_assessment_outcomes(
    equivalence_assessment_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[OutcomeEquivalenceMapping]:
    if repo.get_market_equivalence_assessment(equivalence_assessment_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equivalence_assessment_not_found",
        )
    return repo.list_outcome_equivalence_mappings(equivalence_assessment_id)


@v1_router.post(
    "/equivalence/runs",
    response_model=EquivalenceRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_equivalence_run(
    request_body: EquivalenceRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> EquivalenceRunResult:
    config = EquivalenceRunConfig(
        name=request_body.name,
        asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
        market_ids=request_body.market_ids,
        venue_names=request_body.venue_names,
        min_candidate_score=request_body.min_candidate_score,
        max_pairs=request_body.max_pairs,
        build_classes=request_body.build_classes,
        force=request_body.force,
        metadata=request_body.metadata,
    )
    try:
        return run_equivalence_scan(config, repo=repo)
    except EquivalenceRunError as exc:
        raise _equivalence_run_http_error(exc) from exc


@v1_router.get(
    "/equivalence/runs",
    response_model=list[EquivalenceRun],
    dependencies=[Depends(require_api_token)],
)
def list_equivalence_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquivalenceRun]:
    return repo.list_equivalence_runs(limit=limit, offset=offset)


@v1_router.get(
    "/equivalence/runs/{equivalence_run_id}",
    response_model=EquivalenceRun,
    dependencies=[Depends(require_api_token)],
)
def get_equivalence_run(
    equivalence_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> EquivalenceRun:
    run = repo.get_equivalence_run(equivalence_run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equivalence_run_not_found",
        )
    return run


@v1_router.get(
    "/equivalence/runs/{equivalence_run_id}/summary",
    response_model=EquivalenceRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_equivalence_run_summary(
    equivalence_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> EquivalenceRunSummary:
    summary = repo.get_equivalence_run_summary(equivalence_run_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equivalence_run_summary_not_found",
        )
    return summary


@v1_router.get(
    "/equivalence/classes",
    response_model=list[EquivalenceClass],
    dependencies=[Depends(require_api_token)],
)
def list_equivalence_classes(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[EquivalenceClass]:
    return EquivalenceService(repo).list_equivalence_classes(
        asof_timestamp=asof_timestamp,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/markets/{market_id}/equivalence",
    response_model=list[MarketEquivalenceAssessment],
    dependencies=[Depends(require_api_token)],
)
def list_market_equivalence(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
    status_filter: Annotated[EquivalenceStatus | None, Query(alias="status")] = None,
    permission: ComparisonPermission | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketEquivalenceAssessment]:
    _market_or_404(repo, market_id)
    if asof_timestamp is not None:
        assessments = repo.list_latest_equivalence_assessments_for_market_asof(
            market_id,
            asof_timestamp,
            limit=limit,
        )
        filtered = [
            assessment
            for assessment in assessments
            if (status_filter is None or assessment.status == status_filter)
            and (permission is None or assessment.comparison_permission == permission)
        ]
        return filtered[offset : offset + limit]
    return EquivalenceService(repo).list_equivalence_assessments(
        market_id=market_id,
        status=status_filter,
        permission=permission,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/divergence/analyze",
    response_model=list[CrossVenueDivergenceAnalysis],
    dependencies=[Depends(require_api_token)],
)
def analyze_divergence(
    request_body: DivergenceAnalyzeRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[CrossVenueDivergenceAnalysis]:
    if request_body.equivalence_assessment_id is None and request_body.market_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="equivalence_assessment_id_or_market_id_required",
        )
    service = DivergenceService(repo)
    try:
        if request_body.equivalence_assessment_id is not None:
            return [
                service.analyze_equivalence_divergence(
                    request_body.equivalence_assessment_id,
                    asof_timestamp=request_body.asof_timestamp,
                    outcome_mapping_id=request_body.outcome_mapping_id,
                    force=request_body.force,
                    config=request_body.config,
                )
            ]
        return service.analyze_market_divergence(
            request_body.market_id or "",
            asof_timestamp=request_body.asof_timestamp,
            force=request_body.force,
            config=request_body.config,
        )
    except DivergenceServiceError as exc:
        raise _divergence_http_error(exc) from exc


@v1_router.post(
    "/divergence/runs",
    response_model=CrossVenueDivergenceRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_divergence_run(
    request_body: CrossVenueDivergenceRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueDivergenceRunResult:
    config = CrossVenueDivergenceRunConfig(
        name=request_body.name,
        asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
        equivalence_assessment_ids=request_body.equivalence_assessment_ids,
        market_ids=request_body.market_ids,
        max_pairs=request_body.max_pairs,
        force=request_body.force,
        config=request_body.config,
        metadata=request_body.metadata,
    )
    try:
        return run_divergence_scan(config, repo=repo)
    except DivergenceRunError as exc:
        raise _divergence_run_http_error(exc) from exc


@v1_router.get(
    "/divergence/runs",
    response_model=list[CrossVenueDivergenceRun],
    dependencies=[Depends(require_api_token)],
)
def list_divergence_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossVenueDivergenceRun]:
    return repo.list_divergence_runs(limit=limit, offset=offset)


@v1_router.get(
    "/divergence/runs/{divergence_run_id}",
    response_model=CrossVenueDivergenceRun,
    dependencies=[Depends(require_api_token)],
)
def get_divergence_run(
    divergence_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueDivergenceRun:
    run = repo.get_divergence_run(divergence_run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="divergence_run_not_found",
        )
    return run


@v1_router.get(
    "/divergence/runs/{divergence_run_id}/summary",
    response_model=CrossVenueDivergenceRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_divergence_run_summary(
    divergence_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueDivergenceRunSummary:
    summary = repo.get_divergence_run_summary(divergence_run_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="divergence_run_summary_not_found",
        )
    return summary


@v1_router.get(
    "/divergence/snapshots",
    response_model=list[CrossVenueDivergenceSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_divergence_snapshots(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    equivalence_assessment_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossVenueDivergenceSnapshot]:
    return DivergenceService(repo).list_divergence_snapshots(
        market_id=market_id,
        equivalence_assessment_id=equivalence_assessment_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/divergence/signals",
    response_model=list[CrossVenueDivergenceSignal],
    dependencies=[Depends(require_api_token)],
)
def list_divergence_signals(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossVenueDivergenceSignal]:
    return DivergenceService(repo).list_divergence_signals(
        market_id=market_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/divergence/assessments",
    response_model=list[CrossVenueDivergenceAssessment],
    dependencies=[Depends(require_api_token)],
)
def list_divergence_assessments(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    status_filter: Annotated[DivergenceStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossVenueDivergenceAssessment]:
    return DivergenceService(repo).list_divergence_assessments(
        market_id=market_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/divergence/assessments/{divergence_assessment_id}",
    response_model=CrossVenueDivergenceAssessment,
    dependencies=[Depends(require_api_token)],
)
def get_divergence_assessment(
    divergence_assessment_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueDivergenceAssessment:
    assessment = repo.get_divergence_assessment(divergence_assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="divergence_assessment_not_found",
        )
    return assessment


@v1_router.get(
    "/markets/{market_id}/divergence/latest",
    response_model=CrossVenueDivergenceAssessment,
    dependencies=[Depends(require_api_token)],
)
def get_market_latest_divergence(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> CrossVenueDivergenceAssessment:
    _market_or_404(repo, market_id)
    try:
        return DivergenceService(repo).get_latest_market_divergence_assessment(
            market_id,
            asof_timestamp,
        )
    except DivergenceServiceError as exc:
        raise _divergence_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/divergence/assessments",
    response_model=list[CrossVenueDivergenceAssessment],
    dependencies=[Depends(require_api_token)],
)
def list_market_divergence_assessments(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    status_filter: Annotated[DivergenceStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossVenueDivergenceAssessment]:
    _market_or_404(repo, market_id)
    return DivergenceService(repo).list_divergence_assessments(
        market_id=market_id,
        status=status_filter,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/equivalence/assessments/{equivalence_assessment_id}/divergence/latest",
    response_model=CrossVenueDivergenceAssessment,
    dependencies=[Depends(require_api_token)],
)
def get_equivalence_latest_divergence(
    equivalence_assessment_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueDivergenceAssessment:
    equivalence = repo.get_market_equivalence_assessment(equivalence_assessment_id)
    if equivalence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="equivalence_assessment_not_found",
        )
    assessment = repo.get_latest_divergence_assessment_asof(
        equivalence.left_market_id,
        equivalence.right_market_id,
        datetime.now(tz=UTC),
    )
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="divergence_assessment_not_found",
        )
    return assessment


@v1_router.post(
    "/equivalence/assessments/{equivalence_assessment_id}/divergence/analyze",
    response_model=CrossVenueDivergenceAnalysis,
    dependencies=[Depends(require_api_token)],
)
def analyze_equivalence_divergence(
    equivalence_assessment_id: str,
    request_body: DivergenceAnalyzeRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueDivergenceAnalysis:
    try:
        return DivergenceService(repo).analyze_equivalence_divergence(
            equivalence_assessment_id,
            asof_timestamp=request_body.asof_timestamp,
            outcome_mapping_id=request_body.outcome_mapping_id,
            force=request_body.force,
            config=request_body.config,
        )
    except DivergenceServiceError as exc:
        raise _divergence_http_error(exc) from exc


@v1_router.post(
    "/pretrade/check",
    response_model=PreTradeCheckResponse,
    dependencies=[Depends(require_api_token)],
)
def check_pretrade(
    request_body: PreTradeCheckRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradeCheckResponse:
    asof_timestamp = request_body.asof_timestamp or datetime.now(tz=UTC)
    intent = TradeIntent(
        trade_intent_id="pending",
        market_id=request_body.market_id,
        outcome_id=request_body.outcome_id,
        venue_id=request_body.venue_id,
        strategy_context=request_body.strategy_context,
        side=request_body.side,
        intent_type=request_body.intent_type,
        requested_price=request_body.requested_price,
        requested_size_units=request_body.requested_size_units,
        requested_notional_usd=request_body.requested_notional_usd,
        asof_timestamp=asof_timestamp,
        metadata=request_body.metadata,
    )
    intent = intent.model_copy(update={"trade_intent_id": compute_trade_intent_id(intent)})
    try:
        return PreTradeService(repo).check_pretrade_intent(
            intent,
            policy_id=request_body.policy_id,
            force_recompute_context=request_body.force_recompute_context,
        )
    except PreTradeServiceError as exc:
        raise _pretrade_http_error(exc) from exc


@v1_router.post(
    "/pretrade/check-market/{market_id}",
    response_model=PreTradeCheckResponse,
    dependencies=[Depends(require_api_token)],
)
def check_market_pretrade(
    market_id: str,
    request_body: PreTradeCheckMarketRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradeCheckResponse:
    try:
        return PreTradeService(repo).check_market_default_intent(
            market_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            policy_id=request_body.policy_id,
            strategy_context=request_body.strategy_context,
            requested_size_units=request_body.requested_size_units,
        )
    except PreTradeServiceError as exc:
        raise _pretrade_http_error(exc) from exc


@v1_router.get(
    "/pretrade/decisions",
    response_model=list[PreTradeDecision],
    dependencies=[Depends(require_api_token)],
)
def list_pretrade_decisions(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    action: PreTradeAction | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PreTradeDecision]:
    return PreTradeService(repo).list_pretrade_decisions(
        market_id=market_id,
        action=action,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/pretrade/decisions/{pretrade_decision_id}",
    response_model=PreTradeDecision,
    dependencies=[Depends(require_api_token)],
)
def get_pretrade_decision(
    pretrade_decision_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradeDecision:
    try:
        return PreTradeService(repo).get_pretrade_decision(pretrade_decision_id)
    except PreTradeServiceError as exc:
        raise _pretrade_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/pretrade/latest",
    response_model=PreTradeDecision,
    dependencies=[Depends(require_api_token)],
)
def get_latest_pretrade_decision(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> PreTradeDecision:
    try:
        return PreTradeService(repo).get_latest_pretrade_decision_asof(
            market_id,
            asof_timestamp or datetime.now(tz=UTC),
        )
    except PreTradeServiceError as exc:
        raise _pretrade_http_error(exc) from exc


@v1_router.post(
    "/pretrade/runs",
    response_model=PreTradeRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_pretrade_run(
    request_body: PreTradeRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradeRunResult:
    config = PreTradeRunConfig(
        name=request_body.name,
        asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
        policy_id=request_body.policy_id,
        market_ids=request_body.market_ids,
        max_checks=request_body.max_checks,
        default_requested_size_units=request_body.default_requested_size_units,
        strategy_context=request_body.strategy_context,
        intent_type=request_body.intent_type,
        metadata=request_body.metadata,
    )
    try:
        return run_pretrade_checks(config, repo=repo)
    except PreTradeRunError as exc:
        raise _pretrade_run_http_error(exc) from exc


@v1_router.get(
    "/pretrade/runs",
    response_model=list[PreTradeRun],
    dependencies=[Depends(require_api_token)],
)
def list_pretrade_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PreTradeRun]:
    return repo.list_pretrade_runs(limit=limit, offset=offset)


@v1_router.get(
    "/pretrade/runs/{pretrade_run_id}",
    response_model=PreTradeRun,
    dependencies=[Depends(require_api_token)],
)
def get_pretrade_run(
    pretrade_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradeRun:
    run = repo.get_pretrade_run(pretrade_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pretrade_run_not_found")
    return run


@v1_router.get(
    "/pretrade/runs/{pretrade_run_id}/summary",
    response_model=PreTradeRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_pretrade_run_summary(
    pretrade_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradeRunSummary:
    summary = repo.get_pretrade_run_summary(pretrade_run_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="pretrade_run_summary_not_found",
        )
    return summary


@v1_router.post(
    "/pretrade/policies/default",
    response_model=PreTradePolicy,
    dependencies=[Depends(require_api_token)],
)
def create_default_pretrade_policy(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradePolicy:
    return PreTradeService(repo).create_default_pretrade_policy_if_missing()


@v1_router.get(
    "/pretrade/policies",
    response_model=list[PreTradePolicy],
    dependencies=[Depends(require_api_token)],
)
def list_pretrade_policies(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[PreTradePolicy]:
    return PreTradeService(repo).list_policies()


@v1_router.get(
    "/pretrade/policies/{policy_id}",
    response_model=PreTradePolicy,
    dependencies=[Depends(require_api_token)],
)
def get_pretrade_policy(
    policy_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PreTradePolicy:
    try:
        return PreTradeService(repo).get_policy(policy_id)
    except PreTradeServiceError as exc:
        raise _pretrade_http_error(exc) from exc


@v1_router.post(
    "/pretrade/restrictions",
    response_model=MarketRestrictionRule,
    dependencies=[Depends(require_api_token)],
)
def create_pretrade_restriction(
    request_body: MarketRestrictionRuleCreate,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketRestrictionRule:
    return PreTradeService(repo).save_market_restriction_rule(request_body)


@v1_router.get(
    "/pretrade/restrictions",
    response_model=list[MarketRestrictionRule],
    dependencies=[Depends(require_api_token)],
)
def list_pretrade_restrictions(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketRestrictionRule]:
    return PreTradeService(repo).list_market_restriction_rules(
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/pretrade/exposures",
    response_model=ExposureSnapshot,
    dependencies=[Depends(require_api_token)],
)
def create_pretrade_exposure(
    request_body: ExposureSnapshotCreate,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ExposureSnapshot:
    return PreTradeService(repo).save_exposure_snapshot(request_body)


@v1_router.get(
    "/pretrade/exposures",
    response_model=list[ExposureSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_pretrade_exposures(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ExposureSnapshot]:
    return PreTradeService(repo).list_exposure_snapshots(limit=limit, offset=offset)


@v1_router.post(
    "/paper/policies/default",
    response_model=PaperExecutionPolicy,
    dependencies=[Depends(require_api_token)],
)
def create_default_paper_policy(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperExecutionPolicy:
    return PaperExecutionService(repo).create_default_paper_execution_policy_if_missing()


@v1_router.get(
    "/paper/policies",
    response_model=list[PaperExecutionPolicy],
    dependencies=[Depends(require_api_token)],
)
def list_paper_policies(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[PaperExecutionPolicy]:
    return PaperExecutionService(repo).list_paper_policies()


@v1_router.get(
    "/paper/policies/{paper_policy_id}",
    response_model=PaperExecutionPolicy,
    dependencies=[Depends(require_api_token)],
)
def get_paper_policy(
    paper_policy_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperExecutionPolicy:
    try:
        return PaperExecutionService(repo).get_paper_policy(paper_policy_id)
    except PaperServiceError as exc:
        raise _paper_http_error(exc) from exc


@v1_router.post(
    "/paper/simulate-intent",
    response_model=PaperSimulationResult,
    dependencies=[Depends(require_api_token)],
)
def simulate_paper_intent(
    request_body: PaperSimulateIntentRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperSimulationResult:
    asof_timestamp = request_body.asof_timestamp or datetime.now(tz=UTC)
    intent = compute_trade_intent_from_request(request_body, asof_timestamp)
    try:
        return PaperExecutionService(repo).simulate_trade_intent(
            intent,
            paper_policy_id=request_body.paper_policy_id,
            force_recompute_pretrade=request_body.force_recompute_pretrade,
        )
    except PaperServiceError as exc:
        raise _paper_http_error(exc) from exc


@v1_router.get(
    "/paper/orders",
    response_model=list[PaperOrder],
    dependencies=[Depends(require_api_token)],
)
def list_paper_orders(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    status_filter: Annotated[PaperOrderStatus | None, Query(alias="status")] = None,
    simulation_run_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaperOrder]:
    return PaperExecutionService(repo).list_paper_orders(
        market_id=market_id,
        status=status_filter,
        simulation_run_id=simulation_run_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/paper/orders/{paper_order_id}",
    response_model=PaperOrder,
    dependencies=[Depends(require_api_token)],
)
def get_paper_order(
    paper_order_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperOrder:
    try:
        return PaperExecutionService(repo).get_paper_order(paper_order_id)
    except PaperServiceError as exc:
        raise _paper_http_error(exc) from exc


@v1_router.get(
    "/paper/fills",
    response_model=list[PaperFill],
    dependencies=[Depends(require_api_token)],
)
def list_paper_fills(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    simulation_run_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaperFill]:
    return PaperExecutionService(repo).list_paper_fills(
        market_id=market_id,
        simulation_run_id=simulation_run_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/paper/positions",
    response_model=list[PaperPositionSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_paper_positions(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    simulation_run_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaperPositionSnapshot]:
    return PaperExecutionService(repo).list_paper_positions(
        market_id=market_id,
        simulation_run_id=simulation_run_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/markets/{market_id}/paper/position/latest",
    response_model=PaperPositionSnapshot,
    dependencies=[Depends(require_api_token)],
)
def get_latest_paper_position(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    simulation_run_id: str | None = None,
    asof_timestamp: datetime | None = None,
) -> PaperPositionSnapshot:
    try:
        return PaperExecutionService(repo).get_latest_paper_position_asof(
            market_id,
            simulation_run_id=simulation_run_id,
            asof_timestamp=asof_timestamp or datetime.now(tz=UTC),
        )
    except PaperServiceError as exc:
        raise _paper_http_error(exc) from exc


@v1_router.get(
    "/paper/portfolio/latest",
    response_model=PaperPortfolioSnapshot,
    dependencies=[Depends(require_api_token)],
)
def get_latest_paper_portfolio(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    simulation_run_id: str | None = None,
    asof_timestamp: datetime | None = None,
) -> PaperPortfolioSnapshot:
    try:
        return PaperExecutionService(repo).get_latest_paper_portfolio_asof(
            simulation_run_id=simulation_run_id,
            asof_timestamp=asof_timestamp or datetime.now(tz=UTC),
        )
    except PaperServiceError as exc:
        raise _paper_http_error(exc) from exc


@v1_router.get(
    "/paper/portfolio/snapshots",
    response_model=list[PaperPortfolioSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_paper_portfolio_snapshots(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    simulation_run_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaperPortfolioSnapshot]:
    return PaperExecutionService(repo).list_paper_portfolio_snapshots(
        simulation_run_id=simulation_run_id,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/paper/runs",
    response_model=PaperSimulationRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_paper_run(
    request_body: PaperSimulationRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperSimulationRunResult:
    config = PaperSimulationRunConfig(
        name=request_body.name,
        start_time=request_body.start_time,
        end_time=request_body.end_time,
        interval_seconds=request_body.interval_seconds,
        market_ids=request_body.market_ids,
        max_orders=request_body.max_orders,
        initial_cash_simulated=request_body.initial_cash_simulated,
        paper_policy_id=request_body.paper_policy_id,
        trade_plan=request_body.trade_plan,
        default_order_size_units=request_body.default_order_size_units,
        default_intent_type=request_body.default_intent_type,
        default_strategy_context=request_body.default_strategy_context,
        metadata=request_body.metadata,
    )
    try:
        return run_paper_simulation(config, repo=repo)
    except PaperRunError as exc:
        raise _paper_run_http_error(exc) from exc


@v1_router.get(
    "/paper/runs",
    response_model=list[PaperSimulationRun],
    dependencies=[Depends(require_api_token)],
)
def list_paper_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PaperSimulationRun]:
    return repo.list_paper_simulation_runs(limit=limit, offset=offset)


@v1_router.get(
    "/paper/runs/{simulation_run_id}",
    response_model=PaperSimulationRun,
    dependencies=[Depends(require_api_token)],
)
def get_paper_run(
    simulation_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperSimulationRun:
    run = repo.get_paper_simulation_run(simulation_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="paper_run_not_found")
    return run


@v1_router.get(
    "/paper/runs/{simulation_run_id}/summary",
    response_model=PaperSimulationRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_paper_run_summary(
    simulation_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> PaperSimulationRunSummary:
    summary = repo.get_paper_simulation_run_summary(simulation_run_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="paper_run_summary_not_found",
        )
    return summary


@v1_router.post(
    "/scenario/seeds/build",
    response_model=ScenarioSeedBundle,
    dependencies=[Depends(require_api_token)],
)
def build_scenario_seed_endpoint(
    request_body: ScenarioSeedBuildRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ScenarioSeedBundle:
    try:
        return ScenarioService(repo).build_seed_bundle_for_market(
            request_body.market_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            force=request_body.force,
        )
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/scenario/seed/latest",
    response_model=ScenarioSeedBundle | None,
    dependencies=[Depends(require_api_token)],
)
def get_latest_scenario_seed(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> ScenarioSeedBundle | None:
    return repo.get_latest_scenario_seed_bundle_asof(
        market_id,
        asof_timestamp or datetime.now(tz=UTC),
    )


@v1_router.post(
    "/scenario/specs",
    response_model=ScenarioSimulationSpec,
    dependencies=[Depends(require_api_token)],
)
def create_scenario_spec_endpoint(
    request_body: ScenarioSpecCreateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ScenarioSimulationSpec:
    try:
        return ScenarioService(repo).create_scenario_spec(
            request_body.seed_bundle_id,
            request_body.scenario_goal,
            horizon_hours=request_body.horizon_hours,
            variables=request_body.variables,
            constraints=request_body.constraints,
            metadata=request_body.metadata,
        )
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.post(
    "/scenario/import-fixtures",
    response_model=list[ScenarioArtifact],
    dependencies=[Depends(require_api_token)],
)
def import_scenario_fixtures_endpoint(
    request_body: ScenarioImportFixturesRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[ScenarioArtifact]:
    try:
        return ScenarioService(repo).import_fixture_artifacts(
            market_ids=request_body.market_ids,
            asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
            fixture_dir=request_body.fixture_dir,
            force=request_body.force,
        )
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.post(
    "/scenario/import-manual",
    response_model=ScenarioArtifact,
    dependencies=[Depends(require_api_token)],
)
def import_scenario_manual_endpoint(
    request_body: ScenarioImportManualRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ScenarioArtifact:
    try:
        return ScenarioService(repo).import_manual_artifact(
            file_path=request_body.file_path,
            market_id=request_body.market_id,
            asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
            seed_bundle_id=request_body.seed_bundle_id,
            force=request_body.force,
        )
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.post(
    "/scenario/artifacts/{scenario_artifact_id}/normalize",
    response_model=ScenarioFeatureSnapshot,
    dependencies=[Depends(require_api_token)],
)
def normalize_scenario_artifact_endpoint(
    scenario_artifact_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    force: bool = False,
) -> ScenarioFeatureSnapshot:
    try:
        return ScenarioService(repo).normalize_scenario_artifact(
            scenario_artifact_id,
            force=force,
        )
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.get(
    "/scenario/artifacts",
    response_model=list[ScenarioArtifact],
    dependencies=[Depends(require_api_token)],
)
def list_scenario_artifacts(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScenarioArtifact]:
    return ScenarioService(repo).list_scenario_artifacts(
        market_id=market_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/scenario/features",
    response_model=list[ScenarioFeatureSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_scenario_features(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScenarioFeatureSnapshot]:
    return ScenarioService(repo).list_scenario_features(
        market_id=market_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/markets/{market_id}/scenario/latest",
    response_model=ScenarioFeatureSnapshot | None,
    dependencies=[Depends(require_api_token)],
)
def get_latest_scenario_feature(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> ScenarioFeatureSnapshot | None:
    return ScenarioService(repo).get_latest_scenario_feature_asof(
        market_id,
        asof_timestamp or datetime.now(tz=UTC),
    )


@v1_router.post(
    "/scenario/runs",
    response_model=ScenarioRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_scenario_run(
    request_body: ScenarioRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ScenarioRunResult:
    config = ScenarioRunConfig(
        **{
            **request_body.model_dump(),
            "asof_timestamp": request_body.asof_timestamp or datetime.now(tz=UTC),
        }
    )
    try:
        return run_scenario_import(config, repo=repo)
    except ScenarioRunError as exc:
        raise _scenario_run_http_error(exc) from exc


@v1_router.get(
    "/scenario/runs",
    response_model=list[ScenarioRun],
    dependencies=[Depends(require_api_token)],
)
def list_scenario_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ScenarioRun]:
    return ScenarioService(repo).list_scenario_runs(limit=limit, offset=offset)


@v1_router.get(
    "/scenario/runs/{scenario_run_id}",
    response_model=ScenarioRun,
    dependencies=[Depends(require_api_token)],
)
def get_scenario_run(
    scenario_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ScenarioRun:
    try:
        return ScenarioService(repo).get_scenario_run(scenario_run_id)
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.get(
    "/scenario/runs/{scenario_run_id}/summary",
    response_model=ScenarioRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_scenario_run_summary(
    scenario_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ScenarioRunSummary:
    try:
        return ScenarioService(repo).get_scenario_run_summary(scenario_run_id)
    except ScenarioServiceError as exc:
        raise _scenario_http_error(exc) from exc


@v1_router.post(
    "/dataops/defaults",
    response_model=dict[str, list[MarketUniverseDefinition] | list[CollectionPlan]],
    dependencies=[Depends(require_api_token)],
)
def setup_dataops_defaults(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> dict[str, list[MarketUniverseDefinition] | list[CollectionPlan]]:
    return DataOpsService(repo).setup_default_dataops_objects()


@v1_router.get(
    "/dataops/universes",
    response_model=list[MarketUniverseDefinition],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_universes(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketUniverseDefinition]:
    return DataOpsService(repo).list_market_universes(limit=limit, offset=offset)


@v1_router.post(
    "/dataops/universes/{universe_id}/build",
    response_model=list[MarketUniverseMember],
    dependencies=[Depends(require_api_token)],
)
def build_dataops_universe(
    universe_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
    force: bool = False,
) -> list[MarketUniverseMember]:
    try:
        return DataOpsService(repo).build_universe(
            universe_id,
            asof_timestamp or datetime.now(tz=UTC),
            force=force,
        )
    except DataOpsServiceError as exc:
        raise _dataops_http_error(exc) from exc


@v1_router.get(
    "/dataops/universes/{universe_id}/members",
    response_model=list[MarketUniverseMember],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_universe_members(
    universe_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketUniverseMember]:
    return DataOpsService(repo).list_universe_members(
        universe_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/dataops/collection-plans",
    response_model=list[CollectionPlan],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_collection_plans(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CollectionPlan]:
    return DataOpsService(repo).list_collection_plans(limit=limit, offset=offset)


@v1_router.post(
    "/dataops/collection/run-once",
    response_model=CollectionRunResult,
    dependencies=[Depends(require_api_token)],
)
def run_dataops_collection_once(
    request_body: DataOpsCollectionRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CollectionRunResult:
    try:
        return DataOpsService(repo).run_collection_once(
            plan_id=request_body.plan_id,
            universe_id=request_body.universe_id,
            venue_names=request_body.venue_names,
            market_ids=request_body.market_ids,
            endpoint_types=request_body.endpoint_types,
            mode=request_body.mode.value,
            allow_network=request_body.allow_network,
            asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
            max_payloads=request_body.max_payloads,
            metadata=request_body.metadata,
        )
    except DataOpsServiceError as exc:
        raise _dataops_http_error(exc) from exc


@v1_router.get(
    "/dataops/collection-runs",
    response_model=list[CollectionRun],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_collection_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CollectionRun]:
    return DataOpsService(repo).list_collection_runs(limit=limit, offset=offset)


@v1_router.get(
    "/dataops/collection-runs/{collection_run_id}",
    response_model=CollectionRun,
    dependencies=[Depends(require_api_token)],
)
def get_dataops_collection_run(
    collection_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CollectionRun:
    try:
        return DataOpsService(repo).get_collection_run(collection_run_id)
    except DataOpsServiceError as exc:
        raise _dataops_http_error(exc) from exc


@v1_router.post(
    "/dataops/backfill/jobs",
    response_model=BackfillJob,
    dependencies=[Depends(require_api_token)],
)
def create_dataops_backfill_job(
    request_body: BackfillJobCreateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> BackfillJob:
    try:
        return DataOpsService(repo).create_backfill_job(
            venue_name=request_body.venue_name,
            endpoint_types=request_body.endpoint_types,
            start_time=request_body.start_time,
            end_time=request_body.end_time,
            market_ids=request_body.market_ids,
            job_name=request_body.job_name,
            interval_seconds=request_body.interval_seconds,
            allow_network=request_body.allow_network,
            max_segments=request_body.max_segments,
            metadata=request_body.metadata,
        )
    except DataOpsServiceError as exc:
        raise _dataops_http_error(exc) from exc


@v1_router.post(
    "/dataops/backfill/jobs/{backfill_job_id}/run",
    response_model=BackfillJobResult,
    dependencies=[Depends(require_api_token)],
)
def run_dataops_backfill_job(
    backfill_job_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    force: bool = False,
) -> BackfillJobResult:
    try:
        return DataOpsService(repo).run_backfill_job(backfill_job_id, force=force)
    except DataOpsServiceError as exc:
        raise _dataops_http_error(exc) from exc


@v1_router.get(
    "/dataops/backfill/jobs",
    response_model=list[BackfillJob],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_backfill_jobs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BackfillJob]:
    return DataOpsService(repo).list_backfill_jobs(limit=limit, offset=offset)


@v1_router.get(
    "/dataops/backfill/jobs/{backfill_job_id}",
    response_model=BackfillJob,
    dependencies=[Depends(require_api_token)],
)
def get_dataops_backfill_job(
    backfill_job_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> BackfillJob:
    try:
        return DataOpsService(repo).get_backfill_job(backfill_job_id)
    except DataOpsServiceError as exc:
        raise _dataops_http_error(exc) from exc


@v1_router.get(
    "/dataops/backfill/jobs/{backfill_job_id}/segments",
    response_model=list[BackfillSegment],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_backfill_segments(
    backfill_job_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[BackfillSegment]:
    return DataOpsService(repo).list_backfill_segments(
        backfill_job_id=backfill_job_id,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/dataops/coverage/compute",
    response_model=DataCoverageReport,
    dependencies=[Depends(require_api_token)],
)
def compute_dataops_coverage(
    request_body: DataCoverageComputeRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> DataCoverageReport:
    return DataOpsService(repo).compute_coverage_report(
        scope_type=request_body.scope_type,
        universe_id=request_body.universe_id,
        market_id=request_body.market_id,
        venue_name=request_body.venue_name,
        asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
        start_time=request_body.start_time,
        end_time=request_body.end_time,
    )


@v1_router.get(
    "/dataops/coverage",
    response_model=list[DataCoverageReport],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_coverage(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataCoverageReport]:
    return DataOpsService(repo).list_coverage_reports(limit=limit, offset=offset)


@v1_router.post(
    "/dataops/gaps/detect",
    response_model=list[DataGap],
    dependencies=[Depends(require_api_token)],
)
def detect_dataops_gaps(
    request_body: DataGapDetectRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[DataGap]:
    return DataOpsService(repo).detect_gaps(
        scope_type=request_body.scope_type,
        universe_id=request_body.universe_id,
        market_id=request_body.market_id,
        venue_name=request_body.venue_name,
        asof_timestamp=request_body.asof_timestamp or datetime.now(tz=UTC),
        expected_cadence_seconds=request_body.expected_cadence_seconds,
    )


@v1_router.get(
    "/dataops/gaps",
    response_model=list[DataGap],
    dependencies=[Depends(require_api_token)],
)
def list_dataops_gaps(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataGap]:
    return DataOpsService(repo).list_data_gaps(limit=limit, offset=offset)


@v1_router.post(
    "/dataops/cycle",
    response_model=DataOpsCycleResult,
    dependencies=[Depends(require_api_token)],
)
def run_dataops_cycle_endpoint(
    request_body: DataOpsCycleRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> DataOpsCycleResult:
    config = DataOpsCycleConfig(
        **{
            **request_body.model_dump(),
            "asof_timestamp": request_body.asof_timestamp or datetime.now(tz=UTC),
        }
    )
    return run_dataops_cycle(config, repo=repo)


@v1_router.post(
    "/research/strategies/default",
    response_model=list[ResearchStrategyDefinition],
    dependencies=[Depends(require_api_token)],
)
def create_default_research_strategies(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[ResearchStrategyDefinition]:
    return ResearchService(repo).create_default_research_strategies_if_missing()


@v1_router.get(
    "/research/strategies",
    response_model=list[ResearchStrategyDefinition],
    dependencies=[Depends(require_api_token)],
)
def list_research_strategies(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchStrategyDefinition]:
    return ResearchService(repo).list_research_strategies(limit=limit, offset=offset)


@v1_router.get(
    "/research/strategies/{strategy_id}",
    response_model=ResearchStrategyDefinition,
    dependencies=[Depends(require_api_token)],
)
def get_research_strategy(
    strategy_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResearchStrategyDefinition:
    try:
        return ResearchService(repo).get_research_strategy(strategy_id)
    except ResearchServiceError as exc:
        raise _research_http_error(exc) from exc


@v1_router.post(
    "/research/features/build",
    response_model=list[ResearchFeatureSnapshot],
    dependencies=[Depends(require_api_token)],
)
def build_research_features_endpoint(
    request_body: ResearchFeatureBuildRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[ResearchFeatureSnapshot]:
    return ResearchService(repo).build_features_for_market(
        request_body.market_id,
        request_body.asof_timestamp or datetime.now(tz=UTC),
        include_sources=request_body.include_sources,
        force=request_body.force,
    )


@v1_router.get(
    "/research/features",
    response_model=list[ResearchFeatureSnapshot],
    dependencies=[Depends(require_api_token)],
)
def list_research_features(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    feature_source: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchFeatureSnapshot]:
    return repo.list_research_feature_snapshots(
        market_id=market_id,
        feature_source=feature_source,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/research/signals/generate",
    response_model=list[ResearchSignal],
    dependencies=[Depends(require_api_token)],
)
def generate_research_signals_endpoint(
    request_body: ResearchSignalsGenerateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[ResearchSignal]:
    return ResearchService(repo).generate_research_signals(
        request_body.market_id,
        request_body.asof_timestamp or datetime.now(tz=UTC),
        strategy_ids=request_body.strategy_ids,
        force=request_body.force,
    )


@v1_router.get(
    "/research/signals",
    response_model=list[ResearchSignal],
    dependencies=[Depends(require_api_token)],
)
def list_research_signals(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    strategy_id: str | None = None,
    signal_type: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchSignal]:
    return ResearchService(repo).list_research_signals(
        market_id=market_id,
        strategy_id=strategy_id,
        signal_type=signal_type,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/research/proposals/generate",
    response_model=list[ResearchIntentProposal],
    dependencies=[Depends(require_api_token)],
)
def generate_research_proposals_endpoint(
    request_body: ResearchProposalsGenerateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[ResearchIntentProposal]:
    return ResearchService(repo).generate_research_proposals(
        request_body.market_id,
        request_body.asof_timestamp or datetime.now(tz=UTC),
        strategy_ids=request_body.strategy_ids,
        force=request_body.force,
    )


@v1_router.get(
    "/research/proposals",
    response_model=list[ResearchIntentProposal],
    dependencies=[Depends(require_api_token)],
)
def list_research_proposals(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    strategy_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchIntentProposal]:
    return ResearchService(repo).list_research_proposals(
        market_id=market_id,
        strategy_id=strategy_id,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/research/proposals/{proposal_id}/evaluate",
    response_model=ResearchDecisionTrace,
    dependencies=[Depends(require_api_token)],
)
def evaluate_research_proposal_endpoint(
    proposal_id: str,
    request_body: ResearchProposalEvaluateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResearchDecisionTrace:
    try:
        return ResearchService(repo).evaluate_research_proposal(
            proposal_id,
            enable_paper_simulation=request_body.enable_paper_simulation,
            paper_policy_id=request_body.paper_policy_id,
        )
    except ResearchServiceError as exc:
        raise _research_http_error(exc) from exc


@v1_router.get(
    "/research/traces",
    response_model=list[ResearchDecisionTrace],
    dependencies=[Depends(require_api_token)],
)
def list_research_traces(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    strategy_id: str | None = None,
    research_run_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchDecisionTrace]:
    return ResearchService(repo).list_research_traces(
        market_id=market_id,
        strategy_id=strategy_id,
        research_run_id=research_run_id,
        limit=limit,
        offset=offset,
    )


@v1_router.post(
    "/research/runs",
    response_model=ResearchRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_research_run(
    request_body: ResearchRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResearchRunResult:
    config = ResearchRunConfig(**request_body.model_dump())
    try:
        return run_research_simulation(config, repo=repo)
    except ResearchRunError as exc:
        raise _research_run_http_error(exc) from exc


@v1_router.get(
    "/research/runs",
    response_model=list[ResearchRun],
    dependencies=[Depends(require_api_token)],
)
def list_research_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ResearchRun]:
    return repo.list_research_runs(limit=limit, offset=offset)


@v1_router.get(
    "/research/runs/{research_run_id}",
    response_model=ResearchRun,
    dependencies=[Depends(require_api_token)],
)
def get_research_run(
    research_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResearchRun:
    try:
        return ResearchService(repo).get_research_run(research_run_id)
    except ResearchServiceError as exc:
        raise _research_http_error(exc) from exc


@v1_router.get(
    "/research/runs/{research_run_id}/summary",
    response_model=ResearchRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_research_run_summary(
    research_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResearchRunSummary:
    try:
        return ResearchService(repo).get_research_run_summary(research_run_id)
    except ResearchServiceError as exc:
        raise _research_http_error(exc) from exc


@v1_router.get(
    "/research/runs/{research_run_id}/attribution",
    response_model=ResearchAttributionReport,
    dependencies=[Depends(require_api_token)],
)
def get_research_run_attribution(
    research_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> ResearchAttributionReport:
    try:
        return ResearchService(repo).get_research_attribution_report(research_run_id)
    except ResearchServiceError as exc:
        raise _research_http_error(exc) from exc


@v1_router.get(
    "/markets/{market_id}/research/latest",
    response_model=ResearchLatestResponse,
    dependencies=[Depends(require_api_token)],
)
def get_latest_market_research(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    asof_timestamp: datetime | None = None,
) -> ResearchLatestResponse:
    asof = asof_timestamp or datetime.now(tz=UTC)
    return ResearchLatestResponse(
        signals=repo.list_research_signals(
            market_id=market_id,
            asof_timestamp=asof,
            limit=50,
        ),
        proposals=repo.list_research_intent_proposals(
            market_id=market_id,
            asof_timestamp=asof,
            limit=50,
        ),
        traces=repo.list_research_decision_traces(
            market_id=market_id,
            asof_timestamp=asof,
            limit=50,
        ),
    )


@v1_router.post(
    "/workbench/runs",
    response_model=WorkbenchRunResult,
    dependencies=[Depends(require_api_token)],
)
def create_workbench_run(
    request_body: WorkbenchRunRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> WorkbenchRunResult:
    config = WorkbenchRunConfig(
        **{
            **request_body.model_dump(),
            "asof_timestamp": request_body.asof_timestamp or datetime.now(tz=UTC),
        }
    )
    try:
        return run_workbench_build(config, repo=repo)
    except WorkbenchRunError as exc:
        raise _workbench_run_http_error(exc) from exc


@v1_router.get(
    "/workbench/runs",
    response_model=list[WorkbenchRun],
    dependencies=[Depends(require_api_token)],
)
def list_workbench_runs(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[WorkbenchRun]:
    return WorkbenchService(repo).list_runs(limit=limit, offset=offset)


@v1_router.get(
    "/workbench/runs/{workbench_run_id}",
    response_model=WorkbenchRun,
    dependencies=[Depends(require_api_token)],
)
def get_workbench_run(
    workbench_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> WorkbenchRun:
    try:
        return WorkbenchService(repo).get_run(workbench_run_id)
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.get(
    "/workbench/runs/{workbench_run_id}/summary",
    response_model=WorkbenchRunSummary,
    dependencies=[Depends(require_api_token)],
)
def get_workbench_run_summary(
    workbench_run_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> WorkbenchRunSummary:
    try:
        return WorkbenchService(repo).get_run_summary(workbench_run_id)
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.post(
    "/workbench/watchlists/default",
    response_model=list[DeskWatchlist],
    dependencies=[Depends(require_api_token)],
)
def create_workbench_default_watchlists(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[DeskWatchlist]:
    return WorkbenchService(repo).create_default_watchlists_if_missing()


@v1_router.post(
    "/workbench/queues/build",
    response_model=list[MarketReviewQueueItem],
    dependencies=[Depends(require_api_token)],
)
def build_workbench_queue(
    request_body: WorkbenchQueueBuildRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> list[MarketReviewQueueItem]:
    return WorkbenchService(repo).build_queue(
        request_body.asof_timestamp or datetime.now(tz=UTC),
        market_ids=request_body.market_ids,
        queue_name=request_body.queue_name,
        limit=request_body.limit,
        force=request_body.force,
    )


@v1_router.get(
    "/workbench/queues/items",
    response_model=list[MarketReviewQueueItem],
    dependencies=[Depends(require_api_token)],
)
def list_workbench_queue_items(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    queue_name: str | None = None,
    priority_bucket: ReviewPriorityBucket | None = None,
    review_status: ReviewStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketReviewQueueItem]:
    return WorkbenchService(repo).list_queue_items(
        market_id=market_id,
        queue_name=queue_name,
        priority_bucket=priority_bucket,
        review_status=review_status,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/workbench/queues/latest",
    response_model=list[MarketReviewQueueItem],
    dependencies=[Depends(require_api_token)],
)
def list_latest_workbench_queue_items(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    queue_name: str | None = None,
    priority_bucket: ReviewPriorityBucket | None = None,
    review_status: ReviewStatus | None = None,
    include_resolved: bool = False,
    include_dismissed: bool = False,
    asof_timestamp: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketReviewQueueItem]:
    return WorkbenchService(repo).list_latest_queue_items(
        market_id=market_id,
        queue_name=queue_name,
        priority_bucket=priority_bucket,
        review_status=review_status,
        include_resolved=include_resolved,
        include_dismissed=include_dismissed,
        asof_timestamp=asof_timestamp,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/workbench/queues/summary",
    response_model=WorkbenchQueueSummary,
    dependencies=[Depends(require_api_token)],
)
def summarize_workbench_queue(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    queue_name: str | None = None,
    latest_only: bool = True,
    include_resolved: bool = False,
    include_dismissed: bool = False,
    asof_timestamp: datetime | None = None,
) -> WorkbenchQueueSummary:
    return WorkbenchService(repo).summarize_queue(
        queue_name=queue_name,
        latest_only=latest_only,
        include_resolved=include_resolved,
        include_dismissed=include_dismissed,
        asof_timestamp=asof_timestamp,
    )


@v1_router.post(
    "/workbench/queues/items/{queue_item_id}/status",
    response_model=MarketReviewQueueItem,
    dependencies=[Depends(require_api_token)],
)
def update_workbench_queue_item_status(
    queue_item_id: str,
    request_body: WorkbenchQueueItemStatusUpdateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketReviewQueueItem:
    try:
        return WorkbenchService(repo).update_queue_item_status(queue_item_id, request_body)
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.get(
    "/workbench/status",
    response_model=WorkbenchStatusSummary,
    dependencies=[Depends(require_api_token)],
)
def get_workbench_status(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    queue_name: str | None = None,
    asof_timestamp: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
) -> WorkbenchStatusSummary:
    return WorkbenchService(repo).get_status(
        queue_name=queue_name,
        asof_timestamp=asof_timestamp,
        limit=limit,
    )


@v1_router.post(
    "/workbench/markets/{market_id}/decision-card",
    response_model=MarketDecisionCard,
    dependencies=[Depends(require_api_token)],
)
def build_workbench_decision_card(
    market_id: str,
    request_body: WorkbenchDecisionCardRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketDecisionCard:
    try:
        return WorkbenchService(repo).build_decision_card(
            market_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            force=request_body.force,
        )
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.get(
    "/workbench/markets/{market_id}/decision-card/latest",
    response_model=MarketDecisionCard,
    dependencies=[Depends(require_api_token)],
)
def get_latest_workbench_decision_card(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketDecisionCard:
    try:
        return WorkbenchService(repo).get_latest_decision_card(market_id)
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.post(
    "/workbench/equivalence/{equivalence_assessment_id}/comparison-card",
    response_model=CrossVenueComparisonCard,
    dependencies=[Depends(require_api_token)],
)
def build_workbench_comparison_card(
    equivalence_assessment_id: str,
    request_body: WorkbenchComparisonCardRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> CrossVenueComparisonCard:
    try:
        return WorkbenchService(repo).build_comparison_card(
            equivalence_assessment_id,
            request_body.asof_timestamp or datetime.now(tz=UTC),
            force=request_body.force,
        )
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.get(
    "/workbench/comparison-cards",
    response_model=list[CrossVenueComparisonCard],
    dependencies=[Depends(require_api_token)],
)
def list_workbench_comparison_cards(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[CrossVenueComparisonCard]:
    return WorkbenchService(repo).list_comparison_cards(limit=limit, offset=offset)


@v1_router.post(
    "/workbench/notes",
    response_model=DeskReviewNote,
    dependencies=[Depends(require_api_token)],
)
def create_workbench_note(
    request_body: DeskReviewNoteCreate,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> DeskReviewNote:
    return WorkbenchService(repo).create_note(request_body)


@v1_router.get(
    "/workbench/notes",
    response_model=list[DeskReviewNote],
    dependencies=[Depends(require_api_token)],
)
def list_workbench_notes(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    market_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DeskReviewNote]:
    return WorkbenchService(repo).list_notes(
        market_id=market_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/workbench/notes/{note_id}",
    response_model=DeskReviewNote,
    dependencies=[Depends(require_api_token)],
)
def get_workbench_note(
    note_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> DeskReviewNote:
    try:
        return WorkbenchService(repo).get_note(note_id)
    except WorkbenchServiceError as exc:
        raise _workbench_http_error(exc) from exc


@v1_router.post(
    "/vendor-data/sources",
    response_model=VendorDatasetSource,
    dependencies=[Depends(require_api_token)],
)
def create_vendor_dataset_source(
    request_body: VendorDatasetSourceCreate,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorDatasetSource:
    return VendorDataService(repo).register_source(request_body)


@v1_router.get(
    "/vendor-data/sources",
    response_model=list[VendorDatasetSource],
    dependencies=[Depends(require_api_token)],
)
def list_vendor_dataset_sources(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[VendorDatasetSource]:
    return VendorDataService(repo).list_sources(limit=limit, offset=offset)


@v1_router.get(
    "/vendor-data/sources/{vendor_source_id}",
    response_model=VendorDatasetSource,
    dependencies=[Depends(require_api_token)],
)
def get_vendor_dataset_source(
    vendor_source_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorDatasetSource:
    try:
        return VendorDataService(repo).get_source(vendor_source_id)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.post(
    "/vendor-data/samples/load",
    response_model=VendorSampleFile,
    dependencies=[Depends(require_api_token)],
)
def load_vendor_sample(
    request_body: VendorSampleLoadRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorSampleFile:
    try:
        return VendorDataService(repo).load_sample(request_body)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.get(
    "/vendor-data/samples",
    response_model=list[VendorSampleFile],
    dependencies=[Depends(require_api_token)],
)
def list_vendor_samples(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    vendor_source_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[VendorSampleFile]:
    return VendorDataService(repo).list_samples(
        vendor_source_id=vendor_source_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/vendor-data/samples/{sample_file_id}",
    response_model=VendorSampleFile,
    dependencies=[Depends(require_api_token)],
)
def get_vendor_sample(
    sample_file_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorSampleFile:
    try:
        return VendorDataService(repo).get_sample(sample_file_id)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.post(
    "/vendor-data/samples/{sample_file_id}/inspect",
    response_model=VendorSchemaInspection,
    dependencies=[Depends(require_api_token)],
)
def inspect_vendor_sample(
    sample_file_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorSchemaInspection:
    try:
        return VendorDataService(repo).inspect_sample(sample_file_id)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.post(
    "/vendor-data/samples/{sample_file_id}/validate",
    response_model=VendorDataValidationReport,
    dependencies=[Depends(require_api_token)],
)
def validate_vendor_sample(
    sample_file_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorDataValidationReport:
    try:
        return VendorDataService(repo).validate_sample(sample_file_id)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.post(
    "/vendor-data/samples/{sample_file_id}/dry-run-import",
    response_model=VendorImportDryRun,
    dependencies=[Depends(require_api_token)],
)
def dry_run_vendor_sample_import(
    sample_file_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    request_body: VendorDryRunImportRequest | None = None,
) -> VendorImportDryRun:
    try:
        return VendorDataService(repo).dry_run_import(
            sample_file_id,
            request_body or VendorDryRunImportRequest(),
        )
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.post(
    "/vendor-data/evaluate",
    response_model=VendorEvaluationReport,
    dependencies=[Depends(require_api_token)],
)
def evaluate_vendor_samples(
    request_body: VendorEvaluateRequest,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorEvaluationReport:
    try:
        return VendorDataService(repo).evaluate(request_body)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


@v1_router.get(
    "/vendor-data/reports",
    response_model=list[VendorEvaluationReport],
    dependencies=[Depends(require_api_token)],
)
def list_vendor_evaluation_reports(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    vendor_source_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[VendorEvaluationReport]:
    return VendorDataService(repo).list_reports(
        vendor_source_id=vendor_source_id,
        limit=limit,
        offset=offset,
    )


@v1_router.get(
    "/vendor-data/reports/{evaluation_report_id}",
    response_model=VendorEvaluationReport,
    dependencies=[Depends(require_api_token)],
)
def get_vendor_evaluation_report(
    evaluation_report_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> VendorEvaluationReport:
    try:
        return VendorDataService(repo).get_report(evaluation_report_id)
    except VendorDataServiceError as exc:
        raise _vendor_data_http_error(exc) from exc


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _health_response(settings: Settings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=settings.app_version,
        environment=settings.app_env,
    )


def _market_or_404(repo: PredictionMarketRepository, market_id: str) -> Market:
    market = repo.get_market(market_id)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    return market


def _resolution_http_error(exc: ResolutionCorpusError) -> HTTPException:
    status_code = status.HTTP_404_NOT_FOUND
    return HTTPException(status_code=status_code, detail=exc.code)


def _replay_http_error(exc: ReplayError) -> HTTPException:
    if exc.code in {"too_many_steps", "unknown_policy"}:
        status_code = status.HTTP_400_BAD_REQUEST
    elif exc.code in {"replay_run_not_found", "replay_summary_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _ingestion_http_error(exc: IngestionServiceError) -> HTTPException:
    if exc.code in {"public_network_disabled", "unsupported_venue", "unsupported_ingestion_mode"}:
        status_code = status.HTTP_400_BAD_REQUEST
    elif exc.code == "ingestion_run_not_found":
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _marketdata_http_error(exc: MarketDataServiceError) -> HTTPException:
    if exc.code in {"market_not_found", "orderbook_snapshot_not_found", "raw_payload_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _integrity_http_error(exc: IntegrityServiceError) -> HTTPException:
    if exc.code in {"market_not_found", "integrity_assessment_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _integrity_run_http_error(exc: IntegrityRunError) -> HTTPException:
    if exc.code in {"too_many_integrity_steps", "invalid_integrity_scan"}:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _equivalence_http_error(exc: EquivalenceServiceError) -> HTTPException:
    if exc.code in {
        "equivalence_assessment_not_found",
        "equivalence_candidate_not_found",
        "market_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code == "same_market_pair":
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _equivalence_run_http_error(exc: EquivalenceRunError) -> HTTPException:
    if exc.code in {"too_many_equivalence_pairs"}:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _divergence_http_error(exc: DivergenceServiceError) -> HTTPException:
    if exc.code in {
        "divergence_assessment_not_found",
        "equivalence_assessment_not_found",
        "equivalence_run_not_found",
        "market_not_found",
        "outcome_mapping_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code == "equivalence_assessment_not_available_asof":
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _divergence_run_http_error(exc: DivergenceRunError) -> HTTPException:
    if exc.code in {"too_many_divergence_pairs"}:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _pretrade_http_error(exc: PreTradeServiceError) -> HTTPException:
    if exc.code in {
        "market_not_found",
        "pretrade_decision_not_found",
        "pretrade_policy_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _pretrade_run_http_error(exc: PreTradeRunError) -> HTTPException:
    if exc.code in {"too_many_pretrade_checks"}:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _paper_http_error(exc: PaperServiceError) -> HTTPException:
    if exc.code in {
        "paper_order_not_found",
        "paper_policy_not_found",
        "paper_position_not_found",
        "paper_portfolio_not_found",
    } or exc.code in {"market_not_found"}:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _paper_run_http_error(exc: PaperRunError) -> HTTPException:
    if exc.code in {
        "invalid_paper_time_range",
        "too_many_paper_orders",
        "paper_policy_not_found",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _research_http_error(exc: ResearchServiceError) -> HTTPException:
    if exc.code in {
        "research_strategy_not_found",
        "research_proposal_not_found",
        "research_run_not_found",
        "research_run_summary_not_found",
        "research_attribution_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code == "invalid_research_proposal":
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _research_run_http_error(exc: ResearchRunError) -> HTTPException:
    if exc.code in {"too_many_research_steps", "too_many_research_proposals"}:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _scenario_http_error(exc: ScenarioServiceError) -> HTTPException:
    if exc.code in {
        "scenario_seed_bundle_not_found",
        "scenario_artifact_not_found",
        "scenario_run_not_found",
        "scenario_run_summary_not_found",
        "scenario_seed_market_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code.startswith("scenario_artifact_") or exc.code in {
        "scenario_file_path_must_be_local",
        "scenario_fixture_dir_not_found",
        "scenario_artifact_must_be_json",
        "scenario_artifact_market_id_required",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _scenario_run_http_error(exc: ScenarioRunError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=exc.code,
    )


def _dataops_http_error(exc: DataOpsServiceError) -> HTTPException:
    if exc.code in {
        "backfill_job_not_found",
        "collection_plan_not_found",
        "collection_run_not_found",
        "market_universe_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {
        "invalid_backfill_time_range",
        "missing_backfill_endpoint_types",
        "public_network_disabled",
        "unsupported_venue",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _workbench_http_error(exc: WorkbenchServiceError) -> HTTPException:
    if exc.code in {
        "decision_card_not_found",
        "desk_review_note_not_found",
        "equivalence_assessment_not_found",
        "market_not_found",
        "workbench_run_not_found",
        "workbench_run_summary_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _vendor_data_http_error(exc: VendorDataServiceError) -> HTTPException:
    if exc.code in {
        "vendor_source_not_found",
        "vendor_sample_file_not_found",
        "vendor_evaluation_report_not_found",
    }:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {
        "vendor_file_path_must_be_local",
        "vendor_sample_file_too_large",
        "vendor_file_type_unsupported",
        "vendor_parquet_unsupported",
        "vendor_json_shape_unsupported",
        "vendor_row_shape_unsupported",
        "vendor_evaluation_requires_samples",
        "vendor_sample_source_mismatch",
    }:
        status_code = status.HTTP_400_BAD_REQUEST
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return HTTPException(status_code=status_code, detail=exc.code)


def _workbench_run_http_error(exc: WorkbenchRunError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=exc.code,
    )
