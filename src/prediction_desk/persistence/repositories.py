"""Repository methods for canonical market research objects."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from prediction_desk.dataops.enums import (
    BackfillJobStatus,
    BackfillSegmentStatus,
    CollectionRunMode,
    CollectionRunStatus,
    CoverageScopeType,
    DataGapSeverity,
    DataGapType,
)
from prediction_desk.dataops.models import (
    BackfillJob,
    BackfillSegment,
    CollectionPlan,
    CollectionRun,
    DataCoverageReport,
    DataGap,
    DataRetentionPolicy,
    MarketUniverseDefinition,
    MarketUniverseMember,
)
from prediction_desk.divergence.enums import (
    DivergenceActionHint,
    DivergenceRunStatus,
    DivergenceSignalCategory,
    DivergenceSignalSeverity,
    DivergenceStatus,
)
from prediction_desk.divergence.models import (
    CrossVenueDivergenceAssessment,
    CrossVenueDivergenceRun,
    CrossVenueDivergenceRunSummary,
    CrossVenueDivergenceSignal,
    CrossVenueDivergenceSnapshot,
)
from prediction_desk.domain.enums import (
    MarketStatus,
    MarketType,
    TradeSide,
    VenueType,
    VerdictAction,
)
from prediction_desk.domain.models import (
    Event,
    Market,
    MarketRuleSnapshot,
    OrderBookSnapshot,
    Outcome,
    PriceLevel,
    ResolutionEvent,
    TradePrint,
    Venue,
)
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.equivalence.enums import (
    ComparisonPermission,
    EquivalenceClassStatus,
    EquivalenceRunStatus,
    EquivalenceStatus,
    OutcomeRelation,
)
from prediction_desk.equivalence.models import (
    EquivalenceCandidate,
    EquivalenceClass,
    EquivalenceRun,
    EquivalenceRunSummary,
    MarketEquivalenceAssessment,
    OutcomeEquivalenceMapping,
)
from prediction_desk.ingestion.enums import (
    IngestionCursorStatus,
    IngestionMode,
    IngestionRunStatus,
    IngestionSource,
    VenueEndpointType,
    VenueMappingStatus,
    VenueOutcomeTokenSide,
    VenueOutcomeTokenStatus,
)
from prediction_desk.ingestion.models import (
    IngestionCursor,
    IngestionError,
    IngestionRun,
    RawVenuePayload,
    VenueMarketMapping,
    VenueOutcomeTokenMapping,
)
from prediction_desk.integrity.enums import (
    IntegrityActionHint,
    IntegrityRunStatus,
    SignalCategory,
    SignalSeverity,
)
from prediction_desk.integrity.models import (
    IntegrityAssessment,
    IntegrityRun,
    IntegrityRunSummary,
    IntegritySignal,
    MarketFeatureSnapshot,
)
from prediction_desk.marketdata.enums import MarketDataQualitySeverity, MarketPriceSource
from prediction_desk.marketdata.models import (
    MarketDataQualityReport,
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
)
from prediction_desk.paper.enums import (
    FillModel,
    LiquiditySource,
    PaperLedgerEntryType,
    PaperOrderStatus,
    PaperSimulationRunStatus,
)
from prediction_desk.paper.models import (
    PaperExecutionPolicy,
    PaperFill,
    PaperLedgerEntry,
    PaperOrder,
    PaperPortfolioSnapshot,
    PaperPositionSnapshot,
    PaperSimulationRun,
    PaperSimulationRunSummary,
)
from prediction_desk.persistence.orm import (
    AmbiguityAssessmentRecord,
    BackfillJobRecord,
    BackfillSegmentRecord,
    CollectionPlanRecord,
    CollectionRunRecord,
    CrossVenueComparisonCardRecord,
    CrossVenueDivergenceAssessmentRecord,
    CrossVenueDivergenceRunRecord,
    CrossVenueDivergenceRunSummaryRecord,
    CrossVenueDivergenceSignalRecord,
    CrossVenueDivergenceSnapshotRecord,
    DataCoverageReportRecord,
    DataGapRecord,
    DataRetentionPolicyRecord,
    DeskReviewNoteRecord,
    DeskWatchlistRecord,
    EquivalenceCandidateRecord,
    EquivalenceClassRecord,
    EquivalenceRunRecord,
    EquivalenceRunSummaryRecord,
    EventRecord,
    ExposureSnapshotRecord,
    IngestionCursorRecord,
    IngestionErrorRecord,
    IngestionRunRecord,
    IntegrityAssessmentRecord,
    IntegrityRunRecord,
    IntegrityRunSummaryRecord,
    IntegritySignalRecord,
    MarketDataQualityReportRecord,
    MarketDecisionCardRecord,
    MarketEquivalenceAssessmentRecord,
    MarketFeatureSnapshotRecord,
    MarketLiquiditySnapshotRecord,
    MarketPriceSnapshotRecord,
    MarketRecord,
    MarketRestrictionRuleRecord,
    MarketReviewQueueItemRecord,
    MarketRuleSnapshotRecord,
    MarketUniverseDefinitionRecord,
    MarketUniverseMemberRecord,
    OrderBookSnapshotRecord,
    OutcomeEquivalenceMappingRecord,
    OutcomeRecord,
    PaperExecutionPolicyRecord,
    PaperFillRecord,
    PaperLedgerEntryRecord,
    PaperOrderRecord,
    PaperPortfolioSnapshotRecord,
    PaperPositionSnapshotRecord,
    PaperSimulationRunRecord,
    PaperSimulationRunSummaryRecord,
    PreTradeDecisionRecord,
    PreTradeInputSnapshotRecord,
    PreTradePolicyRecord,
    PreTradeRunRecord,
    PreTradeRunSummaryRecord,
    RawVenuePayloadRecord,
    ReplayRunRecord,
    ReplayRunSummaryRecord,
    ReplayStepRecord,
    ResearchAttributionReportRecord,
    ResearchDecisionTraceRecord,
    ResearchFeatureSnapshotRecord,
    ResearchIntentProposalRecord,
    ResearchRunRecord,
    ResearchRunSummaryRecord,
    ResearchSignalRecord,
    ResearchStrategyDefinitionRecord,
    ResolutionEventRecord,
    ResolutionPredicateRecord,
    ResolutionSourceRecord,
    RuleSnapshotDiffRecord,
    ScenarioArtifactRecord,
    ScenarioFeatureSnapshotRecord,
    ScenarioRunRecord,
    ScenarioRunSummaryRecord,
    ScenarioSeedBundleRecord,
    ScenarioSimulationSpecRecord,
    TradeIntentRecord,
    TradePrintRecord,
    TrustVerdictRecord,
    VenueMarketMappingRecord,
    VenueOutcomeTokenMappingRecord,
    VenueRecord,
    WorkbenchRunRecord,
    WorkbenchRunSummaryRecord,
)
from prediction_desk.pretrade.enums import (
    ExposureSource,
    PreTradeAction,
    PreTradeRunStatus,
    RestrictionScopeType,
    RestrictionType,
    StrategyContext,
    TradeIntentType,
)
from prediction_desk.pretrade.enums import (
    TradeSide as PreTradeSide,
)
from prediction_desk.pretrade.models import (
    ExposureSnapshot,
    MarketRestrictionRule,
    PreTradeDecision,
    PreTradeInputSnapshot,
    PreTradePolicy,
    PreTradeRun,
    PreTradeRunSummary,
    TradeIntent,
)
from prediction_desk.replay.enums import ReplayRunStatus
from prediction_desk.replay.models import ReplayRun, ReplayRunSummary, ReplayStep
from prediction_desk.research.enums import (
    ResearchActionBias,
    ResearchFeatureFamily,
    ResearchFeatureSource,
    ResearchRunStatus,
    ResearchSignalType,
    ResearchStrategyFamily,
)
from prediction_desk.research.models import (
    ResearchAttributionReport,
    ResearchDecisionTrace,
    ResearchFeatureSnapshot,
    ResearchIntentProposal,
    ResearchRun,
    ResearchRunSummary,
    ResearchSignal,
    ResearchStrategyDefinition,
)
from prediction_desk.resolution.enums import (
    Comparator,
    ParseStatus,
    PredicateType,
    ResolutionSourceType,
)
from prediction_desk.resolution.models import (
    AmbiguityAssessment,
    EvidenceSpan,
    ResolutionAnalysis,
    ResolutionPredicate,
    ResolutionSource,
    RuleSnapshotDiff,
)
from prediction_desk.scenario.enums import (
    ScenarioArtifactSourceType,
    ScenarioArtifactType,
    ScenarioEngine,
    ScenarioRunMode,
    ScenarioRunStatus,
    ScenarioSeedSource,
)
from prediction_desk.scenario.models import (
    ScenarioArtifact,
    ScenarioFeatureSnapshot,
    ScenarioRun,
    ScenarioRunSummary,
    ScenarioSeedBundle,
    ScenarioSimulationSpec,
)
from prediction_desk.workbench.enums import (
    DeskReviewNoteType,
    RecommendedReviewAction,
    ReviewPriorityBucket,
    ReviewStatus,
    WorkbenchRunStatus,
)
from prediction_desk.workbench.models import (
    CrossVenueComparisonCard,
    DeskReviewNote,
    DeskWatchlist,
    MarketDecisionCard,
    MarketReviewQueueItem,
    WorkbenchRun,
    WorkbenchRunSummary,
)


class PredictionMarketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_venue(self, venue: Venue) -> Venue:
        self.session.merge(_venue_to_record(venue))
        self.session.flush()
        return venue

    def upsert_venue(self, venue: Venue) -> Venue:
        return self.save_venue(venue)

    def get_venue(self, venue_id: str) -> Venue | None:
        record = self.session.get(VenueRecord, venue_id)
        return _venue_from_record(record) if record else None

    def save_event(self, event: Event) -> Event:
        self.session.merge(_event_to_record(event))
        self.session.flush()
        return event

    def upsert_event(self, event: Event) -> Event:
        return self.save_event(event)

    def get_event(self, event_id: str) -> Event | None:
        record = self.session.get(EventRecord, event_id)
        return _event_from_record(record) if record else None

    def create_market(self, market: Market) -> Market:
        self.session.merge(_market_to_record(market))
        self.session.flush()
        return market

    def upsert_market(self, market: Market) -> Market:
        return self.create_market(market)

    def list_markets(
        self,
        *,
        status: MarketStatus | None = None,
        venue_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Market]:
        stmt = select(MarketRecord).order_by(MarketRecord.market_id).limit(limit).offset(offset)
        if status is not None:
            stmt = stmt.where(MarketRecord.status == status.value)
        if venue_id is not None:
            stmt = stmt.where(MarketRecord.venue_id == venue_id)
        return [_market_from_record(record) for record in self.session.scalars(stmt)]

    def get_market(self, market_id: str) -> Market | None:
        record = self.session.get(MarketRecord, market_id)
        return _market_from_record(record) if record else None

    def save_outcome(self, outcome: Outcome) -> Outcome:
        self.session.merge(_outcome_to_record(outcome))
        self.session.flush()
        return outcome

    def upsert_outcome(self, outcome: Outcome) -> Outcome:
        return self.save_outcome(outcome)

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        record = self.session.get(OutcomeRecord, outcome_id)
        return _outcome_from_record(record) if record else None

    def list_outcomes(self, market_id: str) -> list[Outcome]:
        stmt = (
            select(OutcomeRecord)
            .where(OutcomeRecord.market_id == market_id)
            .order_by(OutcomeRecord.outcome_id)
        )
        return [_outcome_from_record(record) for record in self.session.scalars(stmt)]

    def save_rule_snapshot(self, snapshot: MarketRuleSnapshot) -> MarketRuleSnapshot:
        self.session.merge(_rule_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def get_rule_snapshot(self, rule_snapshot_id: str) -> MarketRuleSnapshot | None:
        record = self.session.get(MarketRuleSnapshotRecord, rule_snapshot_id)
        return _rule_snapshot_from_record(record) if record else None

    def get_latest_rule_snapshot(self, market_id: str) -> MarketRuleSnapshot | None:
        stmt = (
            select(MarketRuleSnapshotRecord)
            .where(MarketRuleSnapshotRecord.market_id == market_id)
            .order_by(
                desc(MarketRuleSnapshotRecord.captured_at),
                desc(MarketRuleSnapshotRecord.rule_snapshot_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _rule_snapshot_from_record(record) if record else None

    def get_latest_rule_snapshot_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> MarketRuleSnapshot | None:
        stmt = (
            select(MarketRuleSnapshotRecord)
            .where(MarketRuleSnapshotRecord.market_id == market_id)
            .where(MarketRuleSnapshotRecord.captured_at <= asof_timestamp)
            .order_by(
                desc(MarketRuleSnapshotRecord.captured_at),
                desc(MarketRuleSnapshotRecord.rule_snapshot_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _rule_snapshot_from_record(record) if record else None

    def get_latest_rule_snapshots(
        self, market_id: str, *, limit: int = 2
    ) -> list[MarketRuleSnapshot]:
        stmt = (
            select(MarketRuleSnapshotRecord)
            .where(MarketRuleSnapshotRecord.market_id == market_id)
            .order_by(
                desc(MarketRuleSnapshotRecord.captured_at),
                desc(MarketRuleSnapshotRecord.rule_snapshot_id),
            )
            .limit(limit)
        )
        return [_rule_snapshot_from_record(record) for record in self.session.scalars(stmt)]

    def save_orderbook_snapshot(self, snapshot: OrderBookSnapshot) -> OrderBookSnapshot:
        self.session.merge(_orderbook_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def get_orderbook_snapshot(self, snapshot_id: str) -> OrderBookSnapshot | None:
        record = self.session.get(OrderBookSnapshotRecord, snapshot_id)
        return _orderbook_snapshot_from_record(record) if record else None

    def get_latest_orderbook_snapshot(self, market_id: str) -> OrderBookSnapshot | None:
        stmt = (
            select(OrderBookSnapshotRecord)
            .where(OrderBookSnapshotRecord.market_id == market_id)
            .order_by(
                desc(OrderBookSnapshotRecord.captured_at),
                desc(OrderBookSnapshotRecord.snapshot_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _orderbook_snapshot_from_record(record) if record else None

    def get_latest_orderbook_snapshot_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> OrderBookSnapshot | None:
        stmt = (
            select(OrderBookSnapshotRecord)
            .where(OrderBookSnapshotRecord.market_id == market_id)
            .where(OrderBookSnapshotRecord.captured_at <= asof_timestamp)
            .order_by(
                desc(OrderBookSnapshotRecord.captured_at),
                desc(OrderBookSnapshotRecord.snapshot_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _orderbook_snapshot_from_record(record) if record else None

    def list_orderbook_snapshots(
        self,
        market_id: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[OrderBookSnapshot]:
        stmt = (
            select(OrderBookSnapshotRecord)
            .where(OrderBookSnapshotRecord.market_id == market_id)
            .order_by(OrderBookSnapshotRecord.captured_at, OrderBookSnapshotRecord.snapshot_id)
            .limit(limit)
            .offset(offset)
        )
        if start_time is not None:
            stmt = stmt.where(OrderBookSnapshotRecord.captured_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(OrderBookSnapshotRecord.captured_at <= end_time)
        return [_orderbook_snapshot_from_record(record) for record in self.session.scalars(stmt)]

    def save_trade_print(self, trade_print: TradePrint) -> TradePrint:
        self.session.merge(_trade_print_to_record(trade_print))
        self.session.flush()
        return trade_print

    def save_resolution_event(self, resolution_event: ResolutionEvent) -> ResolutionEvent:
        self.session.merge(_resolution_event_to_record(resolution_event))
        self.session.flush()
        return resolution_event

    def save_trust_verdict(self, verdict: TrustVerdict) -> TrustVerdict:
        self.session.merge(_trust_verdict_to_record(verdict))
        self.session.flush()
        return verdict

    def get_latest_trust_verdict(self, market_id: str) -> TrustVerdict | None:
        stmt = (
            select(TrustVerdictRecord)
            .where(TrustVerdictRecord.market_id == market_id)
            .order_by(
                desc(TrustVerdictRecord.asof_timestamp),
                desc(TrustVerdictRecord.verdict_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _trust_verdict_from_record(record) if record else None

    def get_latest_trust_verdict_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> TrustVerdict | None:
        stmt = (
            select(TrustVerdictRecord)
            .where(TrustVerdictRecord.market_id == market_id)
            .where(TrustVerdictRecord.asof_timestamp <= asof_timestamp)
            .order_by(
                desc(TrustVerdictRecord.asof_timestamp),
                desc(TrustVerdictRecord.verdict_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _trust_verdict_from_record(record) if record else None

    def save_resolution_source(self, source: ResolutionSource) -> ResolutionSource:
        self.session.merge(_resolution_source_to_record(source))
        self.session.flush()
        return source

    def list_resolution_sources(self) -> list[ResolutionSource]:
        stmt = select(ResolutionSourceRecord).order_by(ResolutionSourceRecord.canonical_name)
        return [_resolution_source_from_record(record) for record in self.session.scalars(stmt)]

    def save_resolution_predicate(self, predicate: ResolutionPredicate) -> ResolutionPredicate:
        self.session.merge(_resolution_predicate_to_record(predicate))
        self.session.flush()
        return predicate

    def get_resolution_predicate_for_rule_snapshot(
        self, rule_snapshot_id: str
    ) -> ResolutionPredicate | None:
        stmt = (
            select(ResolutionPredicateRecord)
            .where(ResolutionPredicateRecord.rule_snapshot_id == rule_snapshot_id)
            .order_by(
                desc(ResolutionPredicateRecord.captured_at),
                desc(ResolutionPredicateRecord.predicate_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _resolution_predicate_from_record(record) if record else None

    def get_latest_resolution_predicate(self, market_id: str) -> ResolutionPredicate | None:
        stmt = (
            select(ResolutionPredicateRecord)
            .where(ResolutionPredicateRecord.market_id == market_id)
            .order_by(
                desc(ResolutionPredicateRecord.captured_at),
                desc(ResolutionPredicateRecord.predicate_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _resolution_predicate_from_record(record) if record else None

    def get_latest_resolution_analysis_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> ResolutionAnalysis | None:
        predicate_stmt = (
            select(ResolutionPredicateRecord)
            .where(ResolutionPredicateRecord.market_id == market_id)
            .where(ResolutionPredicateRecord.captured_at <= asof_timestamp)
            .order_by(
                desc(ResolutionPredicateRecord.captured_at),
                desc(ResolutionPredicateRecord.predicate_id),
            )
            .limit(1)
        )
        predicate_record = self.session.scalar(predicate_stmt)
        if predicate_record is None:
            return None

        assessment_stmt = (
            select(AmbiguityAssessmentRecord)
            .where(AmbiguityAssessmentRecord.rule_snapshot_id == predicate_record.rule_snapshot_id)
            .where(AmbiguityAssessmentRecord.captured_at <= asof_timestamp)
            .order_by(
                desc(AmbiguityAssessmentRecord.captured_at),
                desc(AmbiguityAssessmentRecord.assessment_id),
            )
            .limit(1)
        )
        assessment_record = self.session.scalar(assessment_stmt)
        snapshot_record = self.session.get(
            MarketRuleSnapshotRecord, predicate_record.rule_snapshot_id
        )
        market_record = self.session.get(MarketRecord, market_id)
        if assessment_record is None or snapshot_record is None or market_record is None:
            return None
        return ResolutionAnalysis(
            market=_market_from_record(market_record),
            rule_snapshot=_rule_snapshot_from_record(snapshot_record),
            predicate=_resolution_predicate_from_record(predicate_record),
            ambiguity_assessment=_ambiguity_assessment_from_record(assessment_record),
        )

    def save_ambiguity_assessment(
        self, assessment: AmbiguityAssessment
    ) -> AmbiguityAssessment:
        self.session.merge(_ambiguity_assessment_to_record(assessment))
        self.session.flush()
        return assessment

    def get_ambiguity_assessment_for_rule_snapshot(
        self, rule_snapshot_id: str
    ) -> AmbiguityAssessment | None:
        stmt = (
            select(AmbiguityAssessmentRecord)
            .where(AmbiguityAssessmentRecord.rule_snapshot_id == rule_snapshot_id)
            .order_by(
                desc(AmbiguityAssessmentRecord.captured_at),
                desc(AmbiguityAssessmentRecord.assessment_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _ambiguity_assessment_from_record(record) if record else None

    def save_rule_snapshot_diff(self, diff: RuleSnapshotDiff) -> RuleSnapshotDiff:
        self.session.merge(_rule_snapshot_diff_to_record(diff))
        self.session.flush()
        return diff

    def get_rule_snapshot_diff(
        self, from_rule_snapshot_id: str, to_rule_snapshot_id: str
    ) -> RuleSnapshotDiff | None:
        stmt = (
            select(RuleSnapshotDiffRecord)
            .where(RuleSnapshotDiffRecord.from_rule_snapshot_id == from_rule_snapshot_id)
            .where(RuleSnapshotDiffRecord.to_rule_snapshot_id == to_rule_snapshot_id)
            .order_by(desc(RuleSnapshotDiffRecord.created_at), desc(RuleSnapshotDiffRecord.diff_id))
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _rule_snapshot_diff_from_record(record) if record else None

    def get_latest_rule_snapshot_diff_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> RuleSnapshotDiff | None:
        stmt = (
            select(RuleSnapshotDiffRecord)
            .where(RuleSnapshotDiffRecord.market_id == market_id)
            .where(RuleSnapshotDiffRecord.created_at <= asof_timestamp)
            .order_by(
                desc(RuleSnapshotDiffRecord.created_at),
                desc(RuleSnapshotDiffRecord.diff_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _rule_snapshot_diff_from_record(record) if record else None

    def list_markets_for_replay(
        self,
        *,
        market_ids: list[str] | None,
        start_time: datetime,
        end_time: datetime,
    ) -> list[Market]:
        stmt = select(MarketRecord).order_by(MarketRecord.market_id)
        if market_ids:
            stmt = stmt.where(MarketRecord.market_id.in_(market_ids))
        stmt = stmt.where(
            or_(MarketRecord.created_time.is_(None), MarketRecord.created_time <= end_time)
        ).where(or_(MarketRecord.close_time.is_(None), MarketRecord.close_time >= start_time))
        return [_market_from_record(record) for record in self.session.scalars(stmt)]

    def save_replay_run(self, run: ReplayRun) -> ReplayRun:
        self.session.merge(_replay_run_to_record(run))
        self.session.flush()
        return run

    def update_replay_run_status(
        self,
        run_id: str,
        status: ReplayRunStatus,
        *,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> ReplayRun | None:
        record = self.session.get(ReplayRunRecord, run_id)
        if record is None:
            return None
        record.status = status.value
        if started_at is not None:
            record.started_at = started_at
        if completed_at is not None:
            record.completed_at = completed_at
        self.session.flush()
        return _replay_run_from_record(record)

    def save_replay_step(self, step: ReplayStep) -> ReplayStep:
        self.session.merge(_replay_step_to_record(step))
        self.session.flush()
        return step

    def save_replay_summary(self, summary: ReplayRunSummary) -> ReplayRunSummary:
        self.session.merge(_replay_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_replay_run(self, run_id: str) -> ReplayRun | None:
        record = self.session.get(ReplayRunRecord, run_id)
        return _replay_run_from_record(record) if record else None

    def list_replay_steps(
        self, run_id: str, *, limit: int = 500, offset: int = 0
    ) -> list[ReplayStep]:
        stmt = (
            select(ReplayStepRecord)
            .where(ReplayStepRecord.run_id == run_id)
            .order_by(
                ReplayStepRecord.asof_timestamp,
                ReplayStepRecord.market_id,
                ReplayStepRecord.step_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [_replay_step_from_record(record) for record in self.session.scalars(stmt)]

    def get_replay_summary(self, run_id: str) -> ReplayRunSummary | None:
        stmt = (
            select(ReplayRunSummaryRecord)
            .where(ReplayRunSummaryRecord.run_id == run_id)
            .order_by(
                desc(ReplayRunSummaryRecord.created_at),
                desc(ReplayRunSummaryRecord.summary_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _replay_summary_from_record(record) if record else None

    def save_raw_venue_payload(self, payload: RawVenuePayload) -> RawVenuePayload:
        self.session.merge(_raw_venue_payload_to_record(payload))
        self.session.flush()
        return payload

    def get_raw_venue_payload(self, payload_id: str) -> RawVenuePayload | None:
        record = self.session.get(RawVenuePayloadRecord, payload_id)
        return _raw_venue_payload_from_record(record) if record else None

    def list_raw_venue_payloads(
        self,
        *,
        venue_name: str | None = None,
        endpoint_type: VenueEndpointType | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RawVenuePayload]:
        stmt = (
            select(RawVenuePayloadRecord)
            .order_by(
                desc(RawVenuePayloadRecord.captured_at),
                RawVenuePayloadRecord.payload_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if venue_name is not None:
            stmt = stmt.where(RawVenuePayloadRecord.venue_name == venue_name)
        if endpoint_type is not None:
            stmt = stmt.where(RawVenuePayloadRecord.endpoint_type == endpoint_type.value)
        return [_raw_venue_payload_from_record(record) for record in self.session.scalars(stmt)]

    def upsert_venue_market_mapping(
        self, mapping: VenueMarketMapping
    ) -> VenueMarketMapping:
        existing = self.session.get(VenueMarketMappingRecord, mapping.mapping_id)
        if existing is not None:
            existing.venue_id = mapping.venue_id
            existing.venue_name = mapping.venue_name
            existing.external_event_id = mapping.external_event_id or existing.external_event_id
            existing.external_market_id = mapping.external_market_id
            existing.external_symbol = mapping.external_symbol or existing.external_symbol
            existing.canonical_event_id = mapping.canonical_event_id or existing.canonical_event_id
            existing.canonical_market_id = (
                mapping.canonical_market_id or existing.canonical_market_id
            )
            existing.external_url = mapping.external_url or existing.external_url
            existing.last_seen_at = mapping.last_seen_at
            existing.status = mapping.status.value
            existing.metadata_json = _metadata(
                {**(existing.metadata_json or {}), **mapping.metadata}
            )
            self.session.flush()
            return _venue_market_mapping_from_record(existing)
        self.session.merge(_venue_market_mapping_to_record(mapping))
        self.session.flush()
        return mapping

    def get_mapping_by_external_market_id(
        self, venue_name: str, external_market_id: str
    ) -> VenueMarketMapping | None:
        stmt = (
            select(VenueMarketMappingRecord)
            .where(VenueMarketMappingRecord.venue_name == venue_name)
            .where(VenueMarketMappingRecord.external_market_id == external_market_id)
            .order_by(
                desc(VenueMarketMappingRecord.last_seen_at),
                VenueMarketMappingRecord.mapping_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _venue_market_mapping_from_record(record) if record else None

    def get_mapping_by_canonical_market_id(
        self, canonical_market_id: str
    ) -> VenueMarketMapping | None:
        stmt = (
            select(VenueMarketMappingRecord)
            .where(VenueMarketMappingRecord.canonical_market_id == canonical_market_id)
            .order_by(
                desc(VenueMarketMappingRecord.last_seen_at),
                VenueMarketMappingRecord.mapping_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _venue_market_mapping_from_record(record) if record else None

    def list_venue_market_mappings(
        self,
        *,
        venue_name: str | None = None,
        canonical_market_id: str | None = None,
        external_market_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[VenueMarketMapping]:
        stmt = (
            select(VenueMarketMappingRecord)
            .order_by(
                VenueMarketMappingRecord.venue_name,
                VenueMarketMappingRecord.external_market_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if venue_name is not None:
            stmt = stmt.where(VenueMarketMappingRecord.venue_name == venue_name)
        if canonical_market_id is not None:
            stmt = stmt.where(
                VenueMarketMappingRecord.canonical_market_id == canonical_market_id
            )
        if external_market_id is not None:
            stmt = stmt.where(VenueMarketMappingRecord.external_market_id == external_market_id)
        return [
            _venue_market_mapping_from_record(record) for record in self.session.scalars(stmt)
        ]

    def upsert_venue_outcome_token_mapping(
        self, mapping: VenueOutcomeTokenMapping
    ) -> VenueOutcomeTokenMapping:
        existing = self.session.get(VenueOutcomeTokenMappingRecord, mapping.mapping_id)
        if existing is not None:
            existing.venue_id = mapping.venue_id
            existing.venue_name = mapping.venue_name
            existing.canonical_market_id = mapping.canonical_market_id
            existing.canonical_outcome_id = mapping.canonical_outcome_id
            existing.outcome_label = mapping.outcome_label
            existing.external_market_id = mapping.external_market_id
            existing.condition_id = mapping.condition_id
            existing.question_id = mapping.question_id
            existing.gamma_market_id = mapping.gamma_market_id
            existing.gamma_event_id = mapping.gamma_event_id
            existing.market_address = mapping.market_address
            existing.token_id = mapping.token_id
            existing.asset_id = mapping.asset_id
            existing.token_side = mapping.token_side.value
            existing.enable_orderbook = mapping.enable_orderbook
            existing.last_seen_at = mapping.last_seen_at
            existing.status = mapping.status.value
            existing.metadata_json = _metadata(mapping.metadata)
            self.session.flush()
            return _venue_outcome_token_mapping_from_record(existing)
        self.session.merge(_venue_outcome_token_mapping_to_record(mapping))
        self.session.flush()
        return mapping

    def get_venue_outcome_token_mapping(
        self, mapping_id: str
    ) -> VenueOutcomeTokenMapping | None:
        record = self.session.get(VenueOutcomeTokenMappingRecord, mapping_id)
        return _venue_outcome_token_mapping_from_record(record) if record else None

    def list_venue_outcome_token_mappings(
        self,
        *,
        venue_name: str | None = None,
        canonical_market_id: str | None = None,
        token_id: str | None = None,
        status: VenueOutcomeTokenStatus | str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[VenueOutcomeTokenMapping]:
        stmt = (
            select(VenueOutcomeTokenMappingRecord)
            .order_by(
                VenueOutcomeTokenMappingRecord.venue_name,
                VenueOutcomeTokenMappingRecord.canonical_market_id,
                VenueOutcomeTokenMappingRecord.token_side,
                VenueOutcomeTokenMappingRecord.token_id,
                VenueOutcomeTokenMappingRecord.mapping_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if venue_name is not None:
            stmt = stmt.where(VenueOutcomeTokenMappingRecord.venue_name == venue_name)
        if canonical_market_id is not None:
            stmt = stmt.where(
                VenueOutcomeTokenMappingRecord.canonical_market_id == canonical_market_id
            )
        if token_id is not None:
            stmt = stmt.where(
                or_(
                    VenueOutcomeTokenMappingRecord.token_id == token_id,
                    VenueOutcomeTokenMappingRecord.asset_id == token_id,
                )
            )
        if status is not None:
            status_value = (
                status.value if isinstance(status, VenueOutcomeTokenStatus) else str(status)
            )
            stmt = stmt.where(VenueOutcomeTokenMappingRecord.status == status_value)
        return [
            _venue_outcome_token_mapping_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_ingestion_run(self, run: IngestionRun) -> IngestionRun:
        self.session.merge(_ingestion_run_to_record(run))
        self.session.flush()
        return run

    def update_ingestion_run(self, run: IngestionRun) -> IngestionRun:
        self.session.merge(_ingestion_run_to_record(run))
        self.session.flush()
        return run

    def save_ingestion_error(self, error: IngestionError) -> IngestionError:
        self.session.merge(_ingestion_error_to_record(error))
        self.session.flush()
        return error

    def list_ingestion_runs(
        self,
        *,
        venue_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IngestionRun]:
        stmt = (
            select(IngestionRunRecord)
            .order_by(desc(IngestionRunRecord.started_at), IngestionRunRecord.ingestion_run_id)
            .limit(limit)
            .offset(offset)
        )
        if venue_name is not None:
            stmt = stmt.where(IngestionRunRecord.venue_name == venue_name)
        return [_ingestion_run_from_record(record) for record in self.session.scalars(stmt)]

    def get_ingestion_run(self, ingestion_run_id: str) -> IngestionRun | None:
        record = self.session.get(IngestionRunRecord, ingestion_run_id)
        return _ingestion_run_from_record(record) if record else None

    def list_ingestion_errors(self, ingestion_run_id: str) -> list[IngestionError]:
        stmt = (
            select(IngestionErrorRecord)
            .where(IngestionErrorRecord.ingestion_run_id == ingestion_run_id)
            .order_by(IngestionErrorRecord.occurred_at, IngestionErrorRecord.error_id)
        )
        return [_ingestion_error_from_record(record) for record in self.session.scalars(stmt)]

    def save_market_price_snapshot(
        self, snapshot: MarketPriceSnapshot
    ) -> MarketPriceSnapshot:
        self.session.merge(_market_price_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def get_market_price_snapshot(
        self, price_snapshot_id: str
    ) -> MarketPriceSnapshot | None:
        record = self.session.get(MarketPriceSnapshotRecord, price_snapshot_id)
        return _market_price_snapshot_from_record(record) if record else None

    def find_price_snapshot_by_hash(self, data_hash: str) -> MarketPriceSnapshot | None:
        stmt = (
            select(MarketPriceSnapshotRecord)
            .where(MarketPriceSnapshotRecord.data_hash == data_hash)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_price_snapshot_from_record(record) if record else None

    def get_latest_price_snapshot_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> MarketPriceSnapshot | None:
        stmt = (
            select(MarketPriceSnapshotRecord)
            .where(MarketPriceSnapshotRecord.market_id == market_id)
            .where(MarketPriceSnapshotRecord.available_at <= asof_timestamp)
            .order_by(
                desc(MarketPriceSnapshotRecord.available_at),
                desc(MarketPriceSnapshotRecord.price_snapshot_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_price_snapshot_from_record(record) if record else None

    def list_price_snapshots(
        self,
        market_id: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketPriceSnapshot]:
        stmt = (
            select(MarketPriceSnapshotRecord)
            .where(MarketPriceSnapshotRecord.market_id == market_id)
            .order_by(
                MarketPriceSnapshotRecord.available_at,
                MarketPriceSnapshotRecord.price_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if start_time is not None:
            stmt = stmt.where(MarketPriceSnapshotRecord.available_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(MarketPriceSnapshotRecord.available_at <= end_time)
        return [_market_price_snapshot_from_record(record) for record in self.session.scalars(stmt)]

    def save_market_liquidity_snapshot(
        self, snapshot: MarketLiquiditySnapshot
    ) -> MarketLiquiditySnapshot:
        self.session.merge(_market_liquidity_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def find_liquidity_snapshot_by_hash(
        self, data_hash: str
    ) -> MarketLiquiditySnapshot | None:
        stmt = (
            select(MarketLiquiditySnapshotRecord)
            .where(MarketLiquiditySnapshotRecord.data_hash == data_hash)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_liquidity_snapshot_from_record(record) if record else None

    def get_latest_liquidity_snapshot_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> MarketLiquiditySnapshot | None:
        stmt = (
            select(MarketLiquiditySnapshotRecord)
            .where(MarketLiquiditySnapshotRecord.market_id == market_id)
            .where(MarketLiquiditySnapshotRecord.available_at <= asof_timestamp)
            .order_by(
                desc(MarketLiquiditySnapshotRecord.available_at),
                desc(MarketLiquiditySnapshotRecord.liquidity_snapshot_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_liquidity_snapshot_from_record(record) if record else None

    def list_liquidity_snapshots(
        self,
        market_id: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketLiquiditySnapshot]:
        stmt = (
            select(MarketLiquiditySnapshotRecord)
            .where(MarketLiquiditySnapshotRecord.market_id == market_id)
            .order_by(
                MarketLiquiditySnapshotRecord.available_at,
                MarketLiquiditySnapshotRecord.liquidity_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if start_time is not None:
            stmt = stmt.where(MarketLiquiditySnapshotRecord.available_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(MarketLiquiditySnapshotRecord.available_at <= end_time)
        return [
            _market_liquidity_snapshot_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_market_data_quality_report(
        self, report: MarketDataQualityReport
    ) -> MarketDataQualityReport:
        self.session.merge(_market_data_quality_report_to_record(report))
        self.session.flush()
        return report

    def get_latest_quality_report_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> MarketDataQualityReport | None:
        stmt = (
            select(MarketDataQualityReportRecord)
            .where(MarketDataQualityReportRecord.market_id == market_id)
            .where(MarketDataQualityReportRecord.asof_timestamp <= asof_timestamp)
            .order_by(
                desc(MarketDataQualityReportRecord.asof_timestamp),
                desc(MarketDataQualityReportRecord.quality_report_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_data_quality_report_from_record(record) if record else None

    def list_quality_reports(
        self,
        market_id: str,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketDataQualityReport]:
        stmt = (
            select(MarketDataQualityReportRecord)
            .where(MarketDataQualityReportRecord.market_id == market_id)
            .order_by(
                desc(MarketDataQualityReportRecord.asof_timestamp),
                desc(MarketDataQualityReportRecord.quality_report_id),
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _market_data_quality_report_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def upsert_ingestion_cursor(self, cursor: IngestionCursor) -> IngestionCursor:
        self.session.merge(_ingestion_cursor_to_record(cursor))
        self.session.flush()
        return cursor

    def get_ingestion_cursor(self, cursor_id: str) -> IngestionCursor | None:
        record = self.session.get(IngestionCursorRecord, cursor_id)
        return _ingestion_cursor_from_record(record) if record else None

    def list_ingestion_cursors(
        self,
        *,
        venue_name: str | None = None,
        canonical_market_id: str | None = None,
        external_market_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IngestionCursor]:
        stmt = (
            select(IngestionCursorRecord)
            .order_by(IngestionCursorRecord.venue_name, IngestionCursorRecord.cursor_id)
            .limit(limit)
            .offset(offset)
        )
        if venue_name is not None:
            stmt = stmt.where(IngestionCursorRecord.venue_name == venue_name)
        if canonical_market_id is not None:
            stmt = stmt.where(IngestionCursorRecord.canonical_market_id == canonical_market_id)
        if external_market_id is not None:
            stmt = stmt.where(IngestionCursorRecord.external_market_id == external_market_id)
        return [_ingestion_cursor_from_record(record) for record in self.session.scalars(stmt)]

    def save_market_feature_snapshot(
        self, snapshot: MarketFeatureSnapshot
    ) -> MarketFeatureSnapshot:
        self.session.merge(_market_feature_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def find_feature_snapshot_by_hash(
        self, input_hash: str
    ) -> MarketFeatureSnapshot | None:
        stmt = (
            select(MarketFeatureSnapshotRecord)
            .where(MarketFeatureSnapshotRecord.input_hash == input_hash)
            .order_by(MarketFeatureSnapshotRecord.feature_snapshot_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_feature_snapshot_from_record(record) if record else None

    def save_integrity_signal(self, signal: IntegritySignal) -> IntegritySignal:
        self.session.merge(_integrity_signal_to_record(signal))
        self.session.flush()
        return signal

    def find_integrity_signal_by_hash(self, output_hash: str) -> IntegritySignal | None:
        stmt = (
            select(IntegritySignalRecord)
            .where(IntegritySignalRecord.output_hash == output_hash)
            .order_by(IntegritySignalRecord.integrity_signal_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _integrity_signal_from_record(record) if record else None

    def save_integrity_assessment(
        self, assessment: IntegrityAssessment
    ) -> IntegrityAssessment:
        self.session.merge(_integrity_assessment_to_record(assessment))
        self.session.flush()
        return assessment

    def find_integrity_assessment_by_hash(
        self, output_hash: str
    ) -> IntegrityAssessment | None:
        stmt = (
            select(IntegrityAssessmentRecord)
            .where(IntegrityAssessmentRecord.output_hash == output_hash)
            .order_by(IntegrityAssessmentRecord.integrity_assessment_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _integrity_assessment_from_record(record) if record else None

    def get_latest_integrity_assessment_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> IntegrityAssessment | None:
        stmt = (
            select(IntegrityAssessmentRecord)
            .where(IntegrityAssessmentRecord.market_id == market_id)
            .where(IntegrityAssessmentRecord.available_at <= asof_timestamp)
            .order_by(
                desc(IntegrityAssessmentRecord.available_at),
                desc(IntegrityAssessmentRecord.integrity_assessment_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _integrity_assessment_from_record(record) if record else None

    def list_integrity_signals(
        self,
        *,
        market_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[IntegritySignal]:
        stmt = (
            select(IntegritySignalRecord)
            .order_by(IntegritySignalRecord.available_at, IntegritySignalRecord.signal_name)
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(IntegritySignalRecord.market_id == market_id)
        if start_time is not None:
            stmt = stmt.where(IntegritySignalRecord.available_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(IntegritySignalRecord.available_at <= end_time)
        return [_integrity_signal_from_record(record) for record in self.session.scalars(stmt)]

    def list_integrity_assessments(
        self,
        *,
        market_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[IntegrityAssessment]:
        stmt = (
            select(IntegrityAssessmentRecord)
            .order_by(
                IntegrityAssessmentRecord.available_at,
                IntegrityAssessmentRecord.integrity_assessment_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(IntegrityAssessmentRecord.market_id == market_id)
        if start_time is not None:
            stmt = stmt.where(IntegrityAssessmentRecord.available_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(IntegrityAssessmentRecord.available_at <= end_time)
        return [
            _integrity_assessment_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_integrity_run(self, run: IntegrityRun) -> IntegrityRun:
        self.session.merge(_integrity_run_to_record(run))
        self.session.flush()
        return run

    def update_integrity_run(self, run: IntegrityRun) -> IntegrityRun:
        self.session.merge(_integrity_run_to_record(run))
        self.session.flush()
        return run

    def save_integrity_run_summary(
        self, summary: IntegrityRunSummary
    ) -> IntegrityRunSummary:
        self.session.merge(_integrity_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_integrity_run(self, integrity_run_id: str) -> IntegrityRun | None:
        record = self.session.get(IntegrityRunRecord, integrity_run_id)
        return _integrity_run_from_record(record) if record else None

    def get_integrity_run_summary(
        self, integrity_run_id: str
    ) -> IntegrityRunSummary | None:
        stmt = (
            select(IntegrityRunSummaryRecord)
            .where(IntegrityRunSummaryRecord.integrity_run_id == integrity_run_id)
            .order_by(
                desc(IntegrityRunSummaryRecord.created_at),
                desc(IntegrityRunSummaryRecord.summary_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _integrity_run_summary_from_record(record) if record else None

    def list_integrity_runs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IntegrityRun]:
        stmt = (
            select(IntegrityRunRecord)
            .order_by(desc(IntegrityRunRecord.created_at), IntegrityRunRecord.integrity_run_id)
            .limit(limit)
            .offset(offset)
        )
        return [_integrity_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_equivalence_candidate(
        self, candidate: EquivalenceCandidate
    ) -> EquivalenceCandidate:
        self.session.merge(_equivalence_candidate_to_record(candidate))
        self.session.flush()
        return candidate

    def find_equivalence_candidate_by_hash(
        self, input_hash: str
    ) -> EquivalenceCandidate | None:
        stmt = (
            select(EquivalenceCandidateRecord)
            .where(EquivalenceCandidateRecord.input_hash == input_hash)
            .order_by(EquivalenceCandidateRecord.candidate_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _equivalence_candidate_from_record(record) if record else None

    def get_equivalence_candidate(self, candidate_id: str) -> EquivalenceCandidate | None:
        record = self.session.get(EquivalenceCandidateRecord, candidate_id)
        return _equivalence_candidate_from_record(record) if record else None

    def list_equivalence_candidates(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[EquivalenceCandidate]:
        stmt = (
            select(EquivalenceCandidateRecord)
            .order_by(
                desc(EquivalenceCandidateRecord.asof_timestamp),
                EquivalenceCandidateRecord.candidate_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(
                or_(
                    EquivalenceCandidateRecord.left_market_id == market_id,
                    EquivalenceCandidateRecord.right_market_id == market_id,
                )
            )
        return [
            _equivalence_candidate_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_market_equivalence_assessment(
        self, assessment: MarketEquivalenceAssessment
    ) -> MarketEquivalenceAssessment:
        self.session.merge(_market_equivalence_assessment_to_record(assessment))
        self.session.flush()
        return assessment

    def find_equivalence_assessment_by_hash(
        self, output_hash: str
    ) -> MarketEquivalenceAssessment | None:
        stmt = (
            select(MarketEquivalenceAssessmentRecord)
            .where(MarketEquivalenceAssessmentRecord.output_hash == output_hash)
            .order_by(MarketEquivalenceAssessmentRecord.equivalence_assessment_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_equivalence_assessment_from_record(record) if record else None

    def get_market_equivalence_assessment(
        self, equivalence_assessment_id: str
    ) -> MarketEquivalenceAssessment | None:
        record = self.session.get(MarketEquivalenceAssessmentRecord, equivalence_assessment_id)
        return _market_equivalence_assessment_from_record(record) if record else None

    def get_latest_equivalence_assessment_asof(
        self,
        left_market_id: str,
        right_market_id: str,
        asof_timestamp: datetime,
    ) -> MarketEquivalenceAssessment | None:
        stmt = (
            select(MarketEquivalenceAssessmentRecord)
            .where(MarketEquivalenceAssessmentRecord.available_at <= asof_timestamp)
            .where(
                or_(
                    (
                        MarketEquivalenceAssessmentRecord.left_market_id == left_market_id
                    )
                    & (
                        MarketEquivalenceAssessmentRecord.right_market_id == right_market_id
                    ),
                    (
                        MarketEquivalenceAssessmentRecord.left_market_id == right_market_id
                    )
                    & (
                        MarketEquivalenceAssessmentRecord.right_market_id == left_market_id
                    ),
                )
            )
            .order_by(
                desc(MarketEquivalenceAssessmentRecord.available_at),
                desc(MarketEquivalenceAssessmentRecord.equivalence_assessment_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_equivalence_assessment_from_record(record) if record else None

    def list_latest_equivalence_assessments_for_market_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        limit: int = 500,
    ) -> list[MarketEquivalenceAssessment]:
        stmt = (
            select(MarketEquivalenceAssessmentRecord)
            .where(MarketEquivalenceAssessmentRecord.available_at <= asof_timestamp)
            .where(
                or_(
                    MarketEquivalenceAssessmentRecord.left_market_id == market_id,
                    MarketEquivalenceAssessmentRecord.right_market_id == market_id,
                )
            )
            .order_by(
                desc(MarketEquivalenceAssessmentRecord.available_at),
                desc(MarketEquivalenceAssessmentRecord.equivalence_assessment_id),
            )
            .limit(limit)
        )
        return [
            _market_equivalence_assessment_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def list_equivalence_assessments(
        self,
        *,
        market_id: str | None = None,
        status: EquivalenceStatus | None = None,
        permission: ComparisonPermission | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketEquivalenceAssessment]:
        stmt = (
            select(MarketEquivalenceAssessmentRecord)
            .order_by(
                desc(MarketEquivalenceAssessmentRecord.available_at),
                MarketEquivalenceAssessmentRecord.equivalence_assessment_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(
                or_(
                    MarketEquivalenceAssessmentRecord.left_market_id == market_id,
                    MarketEquivalenceAssessmentRecord.right_market_id == market_id,
                )
            )
        if status is not None:
            stmt = stmt.where(MarketEquivalenceAssessmentRecord.status == status.value)
        if permission is not None:
            stmt = stmt.where(
                MarketEquivalenceAssessmentRecord.comparison_permission == permission.value
            )
        return [
            _market_equivalence_assessment_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_outcome_equivalence_mapping(
        self, mapping: OutcomeEquivalenceMapping
    ) -> OutcomeEquivalenceMapping:
        self.session.merge(_outcome_equivalence_mapping_to_record(mapping))
        self.session.flush()
        return mapping

    def list_outcome_equivalence_mappings(
        self,
        equivalence_assessment_id: str,
    ) -> list[OutcomeEquivalenceMapping]:
        stmt = (
            select(OutcomeEquivalenceMappingRecord)
            .where(
                OutcomeEquivalenceMappingRecord.equivalence_assessment_id
                == equivalence_assessment_id
            )
            .order_by(OutcomeEquivalenceMappingRecord.outcome_mapping_id)
        )
        return [
            _outcome_equivalence_mapping_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_equivalence_class(self, equivalence_class: EquivalenceClass) -> EquivalenceClass:
        self.session.merge(_equivalence_class_to_record(equivalence_class))
        self.session.flush()
        return equivalence_class

    def list_equivalence_classes(
        self,
        *,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[EquivalenceClass]:
        stmt = (
            select(EquivalenceClassRecord)
            .order_by(
                desc(EquivalenceClassRecord.asof_timestamp),
                EquivalenceClassRecord.equivalence_class_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if asof_timestamp is not None:
            stmt = stmt.where(EquivalenceClassRecord.asof_timestamp <= asof_timestamp)
        return [_equivalence_class_from_record(record) for record in self.session.scalars(stmt)]

    def save_equivalence_run(self, run: EquivalenceRun) -> EquivalenceRun:
        self.session.merge(_equivalence_run_to_record(run))
        self.session.flush()
        return run

    def update_equivalence_run(self, run: EquivalenceRun) -> EquivalenceRun:
        self.session.merge(_equivalence_run_to_record(run))
        self.session.flush()
        return run

    def save_equivalence_run_summary(
        self, summary: EquivalenceRunSummary
    ) -> EquivalenceRunSummary:
        self.session.merge(_equivalence_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_equivalence_run(self, equivalence_run_id: str) -> EquivalenceRun | None:
        record = self.session.get(EquivalenceRunRecord, equivalence_run_id)
        return _equivalence_run_from_record(record) if record else None

    def get_equivalence_run_summary(
        self, equivalence_run_id: str
    ) -> EquivalenceRunSummary | None:
        stmt = (
            select(EquivalenceRunSummaryRecord)
            .where(EquivalenceRunSummaryRecord.equivalence_run_id == equivalence_run_id)
            .order_by(
                desc(EquivalenceRunSummaryRecord.created_at),
                desc(EquivalenceRunSummaryRecord.summary_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _equivalence_run_summary_from_record(record) if record else None

    def list_equivalence_runs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EquivalenceRun]:
        stmt = (
            select(EquivalenceRunRecord)
            .order_by(
                desc(EquivalenceRunRecord.created_at),
                EquivalenceRunRecord.equivalence_run_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [_equivalence_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_divergence_snapshot(
        self, snapshot: CrossVenueDivergenceSnapshot
    ) -> CrossVenueDivergenceSnapshot:
        self.session.merge(_divergence_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def find_divergence_snapshot_by_hash(
        self, input_hash: str
    ) -> CrossVenueDivergenceSnapshot | None:
        stmt = (
            select(CrossVenueDivergenceSnapshotRecord)
            .where(CrossVenueDivergenceSnapshotRecord.input_hash == input_hash)
            .order_by(CrossVenueDivergenceSnapshotRecord.divergence_snapshot_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _divergence_snapshot_from_record(record) if record else None

    def save_divergence_signal(
        self, signal: CrossVenueDivergenceSignal
    ) -> CrossVenueDivergenceSignal:
        self.session.merge(_divergence_signal_to_record(signal))
        self.session.flush()
        return signal

    def find_divergence_signal_by_hash(
        self, output_hash: str
    ) -> CrossVenueDivergenceSignal | None:
        stmt = (
            select(CrossVenueDivergenceSignalRecord)
            .where(CrossVenueDivergenceSignalRecord.output_hash == output_hash)
            .order_by(CrossVenueDivergenceSignalRecord.divergence_signal_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _divergence_signal_from_record(record) if record else None

    def save_divergence_assessment(
        self, assessment: CrossVenueDivergenceAssessment
    ) -> CrossVenueDivergenceAssessment:
        self.session.merge(_divergence_assessment_to_record(assessment))
        self.session.flush()
        return assessment

    def find_divergence_assessment_by_hash(
        self, output_hash: str
    ) -> CrossVenueDivergenceAssessment | None:
        stmt = (
            select(CrossVenueDivergenceAssessmentRecord)
            .where(CrossVenueDivergenceAssessmentRecord.output_hash == output_hash)
            .order_by(CrossVenueDivergenceAssessmentRecord.divergence_assessment_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _divergence_assessment_from_record(record) if record else None

    def get_divergence_assessment(
        self, divergence_assessment_id: str
    ) -> CrossVenueDivergenceAssessment | None:
        record = self.session.get(
            CrossVenueDivergenceAssessmentRecord,
            divergence_assessment_id,
        )
        return _divergence_assessment_from_record(record) if record else None

    def get_latest_divergence_assessment_asof(
        self,
        left_market_id: str,
        right_market_id: str,
        asof_timestamp: datetime,
    ) -> CrossVenueDivergenceAssessment | None:
        stmt = (
            select(CrossVenueDivergenceAssessmentRecord)
            .where(CrossVenueDivergenceAssessmentRecord.available_at <= asof_timestamp)
            .where(
                or_(
                    (
                        CrossVenueDivergenceAssessmentRecord.left_market_id
                        == left_market_id
                    )
                    & (
                        CrossVenueDivergenceAssessmentRecord.right_market_id
                        == right_market_id
                    ),
                    (
                        CrossVenueDivergenceAssessmentRecord.left_market_id
                        == right_market_id
                    )
                    & (
                        CrossVenueDivergenceAssessmentRecord.right_market_id
                        == left_market_id
                    ),
                )
            )
            .order_by(
                desc(CrossVenueDivergenceAssessmentRecord.available_at),
                desc(CrossVenueDivergenceAssessmentRecord.divergence_assessment_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _divergence_assessment_from_record(record) if record else None

    def list_latest_divergence_assessments_for_market_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        limit: int = 500,
    ) -> list[CrossVenueDivergenceAssessment]:
        stmt = (
            select(CrossVenueDivergenceAssessmentRecord)
            .where(CrossVenueDivergenceAssessmentRecord.available_at <= asof_timestamp)
            .where(
                or_(
                    CrossVenueDivergenceAssessmentRecord.left_market_id == market_id,
                    CrossVenueDivergenceAssessmentRecord.right_market_id == market_id,
                )
            )
            .order_by(
                desc(CrossVenueDivergenceAssessmentRecord.available_at),
                desc(CrossVenueDivergenceAssessmentRecord.divergence_assessment_id),
            )
            .limit(limit)
        )
        return [
            _divergence_assessment_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def list_divergence_snapshots(
        self,
        *,
        market_id: str | None = None,
        equivalence_assessment_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceSnapshot]:
        stmt = (
            select(CrossVenueDivergenceSnapshotRecord)
            .order_by(
                desc(CrossVenueDivergenceSnapshotRecord.available_at),
                CrossVenueDivergenceSnapshotRecord.divergence_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(
                or_(
                    CrossVenueDivergenceSnapshotRecord.left_market_id == market_id,
                    CrossVenueDivergenceSnapshotRecord.right_market_id == market_id,
                )
            )
        if equivalence_assessment_id is not None:
            stmt = stmt.where(
                CrossVenueDivergenceSnapshotRecord.equivalence_assessment_id
                == equivalence_assessment_id
            )
        if start_time is not None:
            stmt = stmt.where(CrossVenueDivergenceSnapshotRecord.asof_timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.where(CrossVenueDivergenceSnapshotRecord.asof_timestamp <= end_time)
        return [
            _divergence_snapshot_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def list_divergence_signals(
        self,
        *,
        market_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceSignal]:
        stmt = (
            select(CrossVenueDivergenceSignalRecord)
            .order_by(
                desc(CrossVenueDivergenceSignalRecord.available_at),
                CrossVenueDivergenceSignalRecord.divergence_signal_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(
                or_(
                    CrossVenueDivergenceSignalRecord.left_market_id == market_id,
                    CrossVenueDivergenceSignalRecord.right_market_id == market_id,
                )
            )
        if start_time is not None:
            stmt = stmt.where(CrossVenueDivergenceSignalRecord.asof_timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.where(CrossVenueDivergenceSignalRecord.asof_timestamp <= end_time)
        return [
            _divergence_signal_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def list_divergence_assessments(
        self,
        *,
        market_id: str | None = None,
        status: DivergenceStatus | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceAssessment]:
        stmt = (
            select(CrossVenueDivergenceAssessmentRecord)
            .order_by(
                desc(CrossVenueDivergenceAssessmentRecord.available_at),
                CrossVenueDivergenceAssessmentRecord.divergence_assessment_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(
                or_(
                    CrossVenueDivergenceAssessmentRecord.left_market_id == market_id,
                    CrossVenueDivergenceAssessmentRecord.right_market_id == market_id,
                )
            )
        if status is not None:
            stmt = stmt.where(CrossVenueDivergenceAssessmentRecord.status == status.value)
        return [
            _divergence_assessment_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_divergence_run(
        self, run: CrossVenueDivergenceRun
    ) -> CrossVenueDivergenceRun:
        self.session.merge(_divergence_run_to_record(run))
        self.session.flush()
        return run

    def update_divergence_run(
        self, run: CrossVenueDivergenceRun
    ) -> CrossVenueDivergenceRun:
        self.session.merge(_divergence_run_to_record(run))
        self.session.flush()
        return run

    def save_divergence_run_summary(
        self, summary: CrossVenueDivergenceRunSummary
    ) -> CrossVenueDivergenceRunSummary:
        self.session.merge(_divergence_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_divergence_run(self, divergence_run_id: str) -> CrossVenueDivergenceRun | None:
        record = self.session.get(CrossVenueDivergenceRunRecord, divergence_run_id)
        return _divergence_run_from_record(record) if record else None

    def get_divergence_run_summary(
        self, divergence_run_id: str
    ) -> CrossVenueDivergenceRunSummary | None:
        stmt = (
            select(CrossVenueDivergenceRunSummaryRecord)
            .where(
                CrossVenueDivergenceRunSummaryRecord.divergence_run_id
                == divergence_run_id
            )
            .order_by(
                desc(CrossVenueDivergenceRunSummaryRecord.created_at),
                desc(CrossVenueDivergenceRunSummaryRecord.summary_id),
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _divergence_run_summary_from_record(record) if record else None

    def list_divergence_runs(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceRun]:
        stmt = (
            select(CrossVenueDivergenceRunRecord)
            .order_by(
                desc(CrossVenueDivergenceRunRecord.created_at),
                CrossVenueDivergenceRunRecord.divergence_run_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [_divergence_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_trade_intent(self, intent: TradeIntent) -> TradeIntent:
        self.session.merge(_trade_intent_to_record(intent))
        self.session.flush()
        return intent

    def save_pretrade_policy(self, policy: PreTradePolicy) -> PreTradePolicy:
        self.session.merge(_pretrade_policy_to_record(policy))
        self.session.flush()
        return policy

    def get_pretrade_policy(self, policy_id: str) -> PreTradePolicy | None:
        record = self.session.get(PreTradePolicyRecord, policy_id)
        return _pretrade_policy_from_record(record) if record else None

    def get_active_pretrade_policy(
        self,
        policy_name: str | None = None,
        asof_timestamp: datetime | None = None,
    ) -> PreTradePolicy | None:
        stmt = (
            select(PreTradePolicyRecord)
            .where(PreTradePolicyRecord.is_active.is_(True))
            .order_by(desc(PreTradePolicyRecord.created_at), PreTradePolicyRecord.policy_id)
            .limit(1)
        )
        if policy_name is not None:
            stmt = stmt.where(PreTradePolicyRecord.policy_name == policy_name)
        if asof_timestamp is not None:
            stmt = stmt.where(
                or_(
                    PreTradePolicyRecord.effective_from.is_(None),
                    PreTradePolicyRecord.effective_from <= asof_timestamp,
                )
            ).where(
                or_(
                    PreTradePolicyRecord.effective_until.is_(None),
                    PreTradePolicyRecord.effective_until >= asof_timestamp,
                )
            )
        record = self.session.scalar(stmt)
        return _pretrade_policy_from_record(record) if record else None

    def list_pretrade_policies(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PreTradePolicy]:
        stmt = (
            select(PreTradePolicyRecord)
            .order_by(desc(PreTradePolicyRecord.created_at), PreTradePolicyRecord.policy_id)
            .limit(limit)
            .offset(offset)
        )
        return [_pretrade_policy_from_record(record) for record in self.session.scalars(stmt)]

    def save_market_restriction_rule(
        self, rule: MarketRestrictionRule
    ) -> MarketRestrictionRule:
        self.session.merge(_market_restriction_rule_to_record(rule))
        self.session.flush()
        return rule

    def list_market_restriction_rules(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketRestrictionRule]:
        stmt = (
            select(MarketRestrictionRuleRecord)
            .order_by(
                desc(MarketRestrictionRuleRecord.created_at),
                MarketRestrictionRuleRecord.restriction_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _market_restriction_rule_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_exposure_snapshot(self, snapshot: ExposureSnapshot) -> ExposureSnapshot:
        self.session.merge(_exposure_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def get_latest_exposure_snapshot_asof(
        self,
        *,
        market_id: str | None,
        event_id: str | None,
        venue_id: str | None,
        strategy_context: str | None,
        asof_timestamp: datetime,
    ) -> ExposureSnapshot | None:
        stmt = (
            select(ExposureSnapshotRecord)
            .where(ExposureSnapshotRecord.asof_timestamp <= asof_timestamp)
            .order_by(
                desc(ExposureSnapshotRecord.asof_timestamp),
                desc(ExposureSnapshotRecord.created_at),
                ExposureSnapshotRecord.exposure_snapshot_id,
            )
            .limit(1)
        )
        if market_id is not None:
            stmt = stmt.where(
                or_(
                    ExposureSnapshotRecord.market_id == market_id,
                    ExposureSnapshotRecord.market_id.is_(None),
                )
            )
        if event_id is not None:
            stmt = stmt.where(
                or_(
                    ExposureSnapshotRecord.event_id == event_id,
                    ExposureSnapshotRecord.event_id.is_(None),
                )
            )
        if venue_id is not None:
            stmt = stmt.where(
                or_(
                    ExposureSnapshotRecord.venue_id == venue_id,
                    ExposureSnapshotRecord.venue_id.is_(None),
                )
            )
        if strategy_context is not None:
            stmt = stmt.where(
                or_(
                    ExposureSnapshotRecord.strategy_context == strategy_context,
                    ExposureSnapshotRecord.strategy_context.is_(None),
                )
            )
        record = self.session.scalar(stmt)
        return _exposure_snapshot_from_record(record) if record else None

    def list_exposure_snapshots(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ExposureSnapshot]:
        stmt = (
            select(ExposureSnapshotRecord)
            .order_by(
                desc(ExposureSnapshotRecord.asof_timestamp),
                ExposureSnapshotRecord.exposure_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [_exposure_snapshot_from_record(record) for record in self.session.scalars(stmt)]

    def save_pretrade_input_snapshot(
        self, snapshot: PreTradeInputSnapshot
    ) -> PreTradeInputSnapshot:
        self.session.merge(_pretrade_input_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def save_pretrade_decision(self, decision: PreTradeDecision) -> PreTradeDecision:
        self.session.merge(_pretrade_decision_to_record(decision))
        self.session.flush()
        return decision

    def get_pretrade_decision(self, pretrade_decision_id: str) -> PreTradeDecision | None:
        record = self.session.get(PreTradeDecisionRecord, pretrade_decision_id)
        return _pretrade_decision_from_record(record) if record else None

    def get_latest_pretrade_decision_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
    ) -> PreTradeDecision | None:
        stmt = (
            select(PreTradeDecisionRecord)
            .where(PreTradeDecisionRecord.market_id == market_id)
            .where(PreTradeDecisionRecord.available_at <= asof_timestamp)
            .order_by(
                desc(PreTradeDecisionRecord.available_at),
                desc(PreTradeDecisionRecord.generated_at),
                PreTradeDecisionRecord.pretrade_decision_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _pretrade_decision_from_record(record) if record else None

    def list_pretrade_decisions(
        self,
        *,
        market_id: str | None = None,
        action: PreTradeAction | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PreTradeDecision]:
        stmt = (
            select(PreTradeDecisionRecord)
            .order_by(
                desc(PreTradeDecisionRecord.asof_timestamp),
                PreTradeDecisionRecord.pretrade_decision_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(PreTradeDecisionRecord.market_id == market_id)
        if action is not None:
            stmt = stmt.where(PreTradeDecisionRecord.action == action.value)
        if start_time is not None:
            stmt = stmt.where(PreTradeDecisionRecord.asof_timestamp >= start_time)
        if end_time is not None:
            stmt = stmt.where(PreTradeDecisionRecord.asof_timestamp <= end_time)
        return [_pretrade_decision_from_record(record) for record in self.session.scalars(stmt)]

    def save_pretrade_run(self, run: PreTradeRun) -> PreTradeRun:
        self.session.merge(_pretrade_run_to_record(run))
        self.session.flush()
        return run

    def update_pretrade_run(self, run: PreTradeRun) -> PreTradeRun:
        self.session.merge(_pretrade_run_to_record(run))
        self.session.flush()
        return run

    def save_pretrade_run_summary(
        self, summary: PreTradeRunSummary
    ) -> PreTradeRunSummary:
        self.session.merge(_pretrade_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_pretrade_run(self, pretrade_run_id: str) -> PreTradeRun | None:
        record = self.session.get(PreTradeRunRecord, pretrade_run_id)
        return _pretrade_run_from_record(record) if record else None

    def get_pretrade_run_summary(self, pretrade_run_id: str) -> PreTradeRunSummary | None:
        stmt = (
            select(PreTradeRunSummaryRecord)
            .where(PreTradeRunSummaryRecord.pretrade_run_id == pretrade_run_id)
            .order_by(
                desc(PreTradeRunSummaryRecord.created_at),
                PreTradeRunSummaryRecord.summary_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _pretrade_run_summary_from_record(record) if record else None

    def list_pretrade_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PreTradeRun]:
        stmt = (
            select(PreTradeRunRecord)
            .order_by(desc(PreTradeRunRecord.created_at), PreTradeRunRecord.pretrade_run_id)
            .limit(limit)
            .offset(offset)
        )
        return [_pretrade_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_paper_execution_policy(
        self, policy: PaperExecutionPolicy
    ) -> PaperExecutionPolicy:
        self.session.merge(_paper_execution_policy_to_record(policy))
        self.session.flush()
        return policy

    def get_paper_execution_policy(
        self, policy_id: str
    ) -> PaperExecutionPolicy | None:
        record = self.session.get(PaperExecutionPolicyRecord, policy_id)
        return _paper_execution_policy_from_record(record) if record else None

    def get_active_paper_execution_policy(
        self,
        policy_name: str | None = None,
    ) -> PaperExecutionPolicy | None:
        stmt = (
            select(PaperExecutionPolicyRecord)
            .where(PaperExecutionPolicyRecord.is_active.is_(True))
            .order_by(
                desc(PaperExecutionPolicyRecord.created_at),
                PaperExecutionPolicyRecord.paper_policy_id,
            )
            .limit(1)
        )
        if policy_name is not None:
            stmt = stmt.where(PaperExecutionPolicyRecord.policy_name == policy_name)
        record = self.session.scalar(stmt)
        return _paper_execution_policy_from_record(record) if record else None

    def list_paper_execution_policies(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperExecutionPolicy]:
        stmt = (
            select(PaperExecutionPolicyRecord)
            .order_by(
                desc(PaperExecutionPolicyRecord.created_at),
                PaperExecutionPolicyRecord.paper_policy_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _paper_execution_policy_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_paper_order(self, order: PaperOrder) -> PaperOrder:
        self.session.merge(_paper_order_to_record(order))
        self.session.flush()
        return order

    def get_paper_order(self, paper_order_id: str) -> PaperOrder | None:
        record = self.session.get(PaperOrderRecord, paper_order_id)
        return _paper_order_from_record(record) if record else None

    def list_paper_orders(
        self,
        *,
        market_id: str | None = None,
        status: PaperOrderStatus | None = None,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperOrder]:
        stmt = (
            select(PaperOrderRecord)
            .order_by(desc(PaperOrderRecord.asof_timestamp), PaperOrderRecord.paper_order_id)
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(PaperOrderRecord.market_id == market_id)
        if status is not None:
            stmt = stmt.where(PaperOrderRecord.status == status.value)
        if simulation_run_id is not None:
            stmt = stmt.where(PaperOrderRecord.simulation_run_id == simulation_run_id)
        return [_paper_order_from_record(record) for record in self.session.scalars(stmt)]

    def save_paper_fill(self, fill: PaperFill) -> PaperFill:
        self.session.merge(_paper_fill_to_record(fill))
        self.session.flush()
        return fill

    def list_paper_fills(
        self,
        *,
        market_id: str | None = None,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperFill]:
        stmt = (
            select(PaperFillRecord)
            .order_by(desc(PaperFillRecord.asof_timestamp), PaperFillRecord.paper_fill_id)
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(PaperFillRecord.market_id == market_id)
        if simulation_run_id is not None:
            stmt = stmt.where(PaperFillRecord.simulation_run_id == simulation_run_id)
        return [_paper_fill_from_record(record) for record in self.session.scalars(stmt)]

    def save_paper_ledger_entry(self, entry: PaperLedgerEntry) -> PaperLedgerEntry:
        self.session.merge(_paper_ledger_entry_to_record(entry))
        self.session.flush()
        return entry

    def list_paper_ledger_entries(
        self,
        *,
        simulation_run_id: str | None = None,
        limit: int = 10000,
        offset: int = 0,
    ) -> list[PaperLedgerEntry]:
        stmt = (
            select(PaperLedgerEntryRecord)
            .order_by(
                PaperLedgerEntryRecord.occurred_at,
                PaperLedgerEntryRecord.ledger_entry_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if simulation_run_id is not None:
            stmt = stmt.where(PaperLedgerEntryRecord.simulation_run_id == simulation_run_id)
        return [
            _paper_ledger_entry_from_record(record) for record in self.session.scalars(stmt)
        ]

    def save_paper_position_snapshot(
        self, snapshot: PaperPositionSnapshot
    ) -> PaperPositionSnapshot:
        self.session.merge(_paper_position_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def get_latest_paper_position_asof(
        self,
        market_id: str,
        *,
        outcome_id: str | None = None,
        simulation_run_id: str | None = None,
        asof_timestamp: datetime,
    ) -> PaperPositionSnapshot | None:
        stmt = (
            select(PaperPositionSnapshotRecord)
            .where(PaperPositionSnapshotRecord.market_id == market_id)
            .where(PaperPositionSnapshotRecord.available_at <= asof_timestamp)
            .order_by(
                desc(PaperPositionSnapshotRecord.available_at),
                desc(PaperPositionSnapshotRecord.generated_at),
                PaperPositionSnapshotRecord.position_snapshot_id,
            )
            .limit(1)
        )
        if outcome_id is not None:
            stmt = stmt.where(PaperPositionSnapshotRecord.outcome_id == outcome_id)
        if simulation_run_id is not None:
            stmt = stmt.where(PaperPositionSnapshotRecord.simulation_run_id == simulation_run_id)
        record = self.session.scalar(stmt)
        return _paper_position_snapshot_from_record(record) if record else None

    def list_paper_position_snapshots(
        self,
        *,
        market_id: str | None = None,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperPositionSnapshot]:
        stmt = (
            select(PaperPositionSnapshotRecord)
            .order_by(
                desc(PaperPositionSnapshotRecord.asof_timestamp),
                PaperPositionSnapshotRecord.position_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(PaperPositionSnapshotRecord.market_id == market_id)
        if simulation_run_id is not None:
            stmt = stmt.where(PaperPositionSnapshotRecord.simulation_run_id == simulation_run_id)
        return [
            _paper_position_snapshot_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_paper_portfolio_snapshot(
        self, snapshot: PaperPortfolioSnapshot
    ) -> PaperPortfolioSnapshot:
        self.session.merge(_paper_portfolio_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def get_latest_paper_portfolio_asof(
        self,
        *,
        simulation_run_id: str | None = None,
        asof_timestamp: datetime,
    ) -> PaperPortfolioSnapshot | None:
        stmt = (
            select(PaperPortfolioSnapshotRecord)
            .where(PaperPortfolioSnapshotRecord.available_at <= asof_timestamp)
            .order_by(
                desc(PaperPortfolioSnapshotRecord.available_at),
                desc(PaperPortfolioSnapshotRecord.generated_at),
                PaperPortfolioSnapshotRecord.portfolio_snapshot_id,
            )
            .limit(1)
        )
        if simulation_run_id is not None:
            stmt = stmt.where(PaperPortfolioSnapshotRecord.simulation_run_id == simulation_run_id)
        record = self.session.scalar(stmt)
        return _paper_portfolio_snapshot_from_record(record) if record else None

    def list_paper_portfolio_snapshots(
        self,
        *,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperPortfolioSnapshot]:
        stmt = (
            select(PaperPortfolioSnapshotRecord)
            .order_by(
                desc(PaperPortfolioSnapshotRecord.asof_timestamp),
                PaperPortfolioSnapshotRecord.portfolio_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if simulation_run_id is not None:
            stmt = stmt.where(PaperPortfolioSnapshotRecord.simulation_run_id == simulation_run_id)
        return [
            _paper_portfolio_snapshot_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_paper_simulation_run(
        self, run: PaperSimulationRun
    ) -> PaperSimulationRun:
        self.session.merge(_paper_simulation_run_to_record(run))
        self.session.flush()
        return run

    def update_paper_simulation_run(
        self, run: PaperSimulationRun
    ) -> PaperSimulationRun:
        self.session.merge(_paper_simulation_run_to_record(run))
        self.session.flush()
        return run

    def save_paper_simulation_run_summary(
        self, summary: PaperSimulationRunSummary
    ) -> PaperSimulationRunSummary:
        self.session.merge(_paper_simulation_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_paper_simulation_run(
        self, simulation_run_id: str
    ) -> PaperSimulationRun | None:
        record = self.session.get(PaperSimulationRunRecord, simulation_run_id)
        return _paper_simulation_run_from_record(record) if record else None

    def get_paper_simulation_run_summary(
        self, simulation_run_id: str
    ) -> PaperSimulationRunSummary | None:
        stmt = (
            select(PaperSimulationRunSummaryRecord)
            .where(PaperSimulationRunSummaryRecord.simulation_run_id == simulation_run_id)
            .order_by(
                desc(PaperSimulationRunSummaryRecord.created_at),
                PaperSimulationRunSummaryRecord.summary_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _paper_simulation_run_summary_from_record(record) if record else None

    def list_paper_simulation_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperSimulationRun]:
        stmt = (
            select(PaperSimulationRunRecord)
            .order_by(
                desc(PaperSimulationRunRecord.created_at),
                PaperSimulationRunRecord.simulation_run_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _paper_simulation_run_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_research_strategy_definition(
        self,
        definition: ResearchStrategyDefinition,
    ) -> ResearchStrategyDefinition:
        self.session.merge(_research_strategy_definition_to_record(definition))
        self.session.flush()
        return definition

    def get_research_strategy_definition(
        self,
        strategy_id: str,
    ) -> ResearchStrategyDefinition | None:
        record = self.session.get(ResearchStrategyDefinitionRecord, strategy_id)
        return _research_strategy_definition_from_record(record) if record else None

    def list_research_strategy_definitions(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchStrategyDefinition]:
        stmt = (
            select(ResearchStrategyDefinitionRecord)
            .order_by(
                desc(ResearchStrategyDefinitionRecord.created_at),
                ResearchStrategyDefinitionRecord.strategy_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _research_strategy_definition_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_research_feature_snapshot(
        self,
        snapshot: ResearchFeatureSnapshot,
    ) -> ResearchFeatureSnapshot:
        self.session.merge(_research_feature_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def find_research_feature_snapshot_by_hash(
        self,
        input_hash: str,
    ) -> ResearchFeatureSnapshot | None:
        stmt = (
            select(ResearchFeatureSnapshotRecord)
            .where(ResearchFeatureSnapshotRecord.input_hash == input_hash)
            .order_by(ResearchFeatureSnapshotRecord.research_feature_snapshot_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _research_feature_snapshot_from_record(record) if record else None

    def list_research_feature_snapshots(
        self,
        *,
        market_id: str | None = None,
        feature_source: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchFeatureSnapshot]:
        stmt = (
            select(ResearchFeatureSnapshotRecord)
            .order_by(
                desc(ResearchFeatureSnapshotRecord.available_at),
                ResearchFeatureSnapshotRecord.research_feature_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(ResearchFeatureSnapshotRecord.market_id == market_id)
        if feature_source is not None:
            stmt = stmt.where(
                ResearchFeatureSnapshotRecord.feature_source == feature_source
            )
        if asof_timestamp is not None:
            stmt = stmt.where(ResearchFeatureSnapshotRecord.available_at <= asof_timestamp)
        return [
            _research_feature_snapshot_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_research_signal(self, signal: ResearchSignal) -> ResearchSignal:
        self.session.merge(_research_signal_to_record(signal))
        self.session.flush()
        return signal

    def find_research_signal_by_hash(
        self,
        output_hash: str,
    ) -> ResearchSignal | None:
        stmt = (
            select(ResearchSignalRecord)
            .where(ResearchSignalRecord.output_hash == output_hash)
            .order_by(ResearchSignalRecord.research_signal_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _research_signal_from_record(record) if record else None

    def list_research_signals(
        self,
        *,
        market_id: str | None = None,
        strategy_id: str | None = None,
        signal_type: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchSignal]:
        stmt = (
            select(ResearchSignalRecord)
            .order_by(
                desc(ResearchSignalRecord.available_at),
                ResearchSignalRecord.research_signal_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(ResearchSignalRecord.market_id == market_id)
        if strategy_id is not None:
            stmt = stmt.where(ResearchSignalRecord.strategy_id == strategy_id)
        if signal_type is not None:
            stmt = stmt.where(ResearchSignalRecord.signal_type == signal_type)
        if asof_timestamp is not None:
            stmt = stmt.where(ResearchSignalRecord.available_at <= asof_timestamp)
        return [_research_signal_from_record(record) for record in self.session.scalars(stmt)]

    def save_research_intent_proposal(
        self,
        proposal: ResearchIntentProposal,
    ) -> ResearchIntentProposal:
        self.session.merge(_research_intent_proposal_to_record(proposal))
        self.session.flush()
        return proposal

    def find_research_intent_proposal_by_hash(
        self,
        output_hash: str,
    ) -> ResearchIntentProposal | None:
        stmt = (
            select(ResearchIntentProposalRecord)
            .where(ResearchIntentProposalRecord.output_hash == output_hash)
            .order_by(ResearchIntentProposalRecord.proposal_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _research_intent_proposal_from_record(record) if record else None

    def get_research_intent_proposal(
        self,
        proposal_id: str,
    ) -> ResearchIntentProposal | None:
        record = self.session.get(ResearchIntentProposalRecord, proposal_id)
        return _research_intent_proposal_from_record(record) if record else None

    def list_research_intent_proposals(
        self,
        *,
        market_id: str | None = None,
        strategy_id: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchIntentProposal]:
        stmt = (
            select(ResearchIntentProposalRecord)
            .order_by(
                desc(ResearchIntentProposalRecord.available_at),
                ResearchIntentProposalRecord.proposal_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(ResearchIntentProposalRecord.market_id == market_id)
        if strategy_id is not None:
            stmt = stmt.where(ResearchIntentProposalRecord.strategy_id == strategy_id)
        if asof_timestamp is not None:
            stmt = stmt.where(ResearchIntentProposalRecord.available_at <= asof_timestamp)
        return [
            _research_intent_proposal_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_research_decision_trace(
        self,
        trace: ResearchDecisionTrace,
    ) -> ResearchDecisionTrace:
        self.session.merge(_research_decision_trace_to_record(trace))
        self.session.flush()
        return trace

    def list_research_decision_traces(
        self,
        *,
        market_id: str | None = None,
        strategy_id: str | None = None,
        research_run_id: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchDecisionTrace]:
        stmt = (
            select(ResearchDecisionTraceRecord)
            .order_by(
                desc(ResearchDecisionTraceRecord.available_at),
                ResearchDecisionTraceRecord.trace_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(ResearchDecisionTraceRecord.market_id == market_id)
        if strategy_id is not None:
            stmt = stmt.where(ResearchDecisionTraceRecord.strategy_id == strategy_id)
        if research_run_id is not None:
            stmt = stmt.where(
                ResearchDecisionTraceRecord.research_run_id == research_run_id
            )
        if asof_timestamp is not None:
            stmt = stmt.where(ResearchDecisionTraceRecord.available_at <= asof_timestamp)
        return [
            _research_decision_trace_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_research_run(self, run: ResearchRun) -> ResearchRun:
        self.session.merge(_research_run_to_record(run))
        self.session.flush()
        return run

    def update_research_run(self, run: ResearchRun) -> ResearchRun:
        self.session.merge(_research_run_to_record(run))
        self.session.flush()
        return run

    def get_research_run(self, research_run_id: str) -> ResearchRun | None:
        record = self.session.get(ResearchRunRecord, research_run_id)
        return _research_run_from_record(record) if record else None

    def list_research_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchRun]:
        stmt = (
            select(ResearchRunRecord)
            .order_by(desc(ResearchRunRecord.created_at), ResearchRunRecord.research_run_id)
            .limit(limit)
            .offset(offset)
        )
        return [_research_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_research_run_summary(
        self,
        summary: ResearchRunSummary,
    ) -> ResearchRunSummary:
        self.session.merge(_research_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_research_run_summary(
        self,
        research_run_id: str,
    ) -> ResearchRunSummary | None:
        stmt = (
            select(ResearchRunSummaryRecord)
            .where(ResearchRunSummaryRecord.research_run_id == research_run_id)
            .order_by(
                desc(ResearchRunSummaryRecord.created_at),
                ResearchRunSummaryRecord.summary_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _research_run_summary_from_record(record) if record else None

    def save_research_attribution_report(
        self,
        report: ResearchAttributionReport,
    ) -> ResearchAttributionReport:
        self.session.merge(_research_attribution_report_to_record(report))
        self.session.flush()
        return report

    def get_research_attribution_report(
        self,
        research_run_id: str,
    ) -> ResearchAttributionReport | None:
        stmt = (
            select(ResearchAttributionReportRecord)
            .where(ResearchAttributionReportRecord.research_run_id == research_run_id)
            .order_by(
                desc(ResearchAttributionReportRecord.created_at),
                ResearchAttributionReportRecord.attribution_report_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _research_attribution_report_from_record(record) if record else None

    def save_scenario_seed_bundle(
        self,
        bundle: ScenarioSeedBundle,
    ) -> ScenarioSeedBundle:
        self.session.merge(_scenario_seed_bundle_to_record(bundle))
        self.session.flush()
        return bundle

    def find_scenario_seed_bundle_by_hash(
        self,
        input_hash: str,
    ) -> ScenarioSeedBundle | None:
        stmt = (
            select(ScenarioSeedBundleRecord)
            .where(ScenarioSeedBundleRecord.input_hash == input_hash)
            .order_by(ScenarioSeedBundleRecord.seed_bundle_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _scenario_seed_bundle_from_record(record) if record else None

    def get_scenario_seed_bundle(
        self,
        seed_bundle_id: str,
    ) -> ScenarioSeedBundle | None:
        record = self.session.get(ScenarioSeedBundleRecord, seed_bundle_id)
        return _scenario_seed_bundle_from_record(record) if record else None

    def get_latest_scenario_seed_bundle_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
    ) -> ScenarioSeedBundle | None:
        stmt = (
            select(ScenarioSeedBundleRecord)
            .where(ScenarioSeedBundleRecord.market_id == market_id)
            .where(ScenarioSeedBundleRecord.available_at <= asof_timestamp)
            .order_by(
                desc(ScenarioSeedBundleRecord.available_at),
                desc(ScenarioSeedBundleRecord.generated_at),
                ScenarioSeedBundleRecord.seed_bundle_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _scenario_seed_bundle_from_record(record) if record else None

    def save_scenario_simulation_spec(
        self,
        spec: ScenarioSimulationSpec,
    ) -> ScenarioSimulationSpec:
        self.session.merge(_scenario_simulation_spec_to_record(spec))
        self.session.flush()
        return spec

    def get_scenario_simulation_spec(
        self,
        scenario_spec_id: str,
    ) -> ScenarioSimulationSpec | None:
        record = self.session.get(ScenarioSimulationSpecRecord, scenario_spec_id)
        return _scenario_simulation_spec_from_record(record) if record else None

    def save_scenario_artifact(
        self,
        artifact: ScenarioArtifact,
    ) -> ScenarioArtifact:
        self.session.merge(_scenario_artifact_to_record(artifact))
        self.session.flush()
        return artifact

    def find_scenario_artifact_by_hash(
        self,
        payload_hash: str,
    ) -> ScenarioArtifact | None:
        stmt = (
            select(ScenarioArtifactRecord)
            .where(ScenarioArtifactRecord.payload_hash == payload_hash)
            .order_by(ScenarioArtifactRecord.scenario_artifact_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _scenario_artifact_from_record(record) if record else None

    def get_scenario_artifact(
        self,
        scenario_artifact_id: str,
    ) -> ScenarioArtifact | None:
        record = self.session.get(ScenarioArtifactRecord, scenario_artifact_id)
        return _scenario_artifact_from_record(record) if record else None

    def list_scenario_artifacts(
        self,
        *,
        market_id: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ScenarioArtifact]:
        stmt = (
            select(ScenarioArtifactRecord)
            .order_by(
                desc(ScenarioArtifactRecord.available_at),
                ScenarioArtifactRecord.scenario_artifact_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(ScenarioArtifactRecord.market_id == market_id)
        if asof_timestamp is not None:
            stmt = stmt.where(ScenarioArtifactRecord.available_at <= asof_timestamp)
        return [
            _scenario_artifact_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_scenario_feature_snapshot(
        self,
        snapshot: ScenarioFeatureSnapshot,
    ) -> ScenarioFeatureSnapshot:
        self.session.merge(_scenario_feature_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

    def find_scenario_feature_snapshot_by_hash(
        self,
        input_hash: str,
    ) -> ScenarioFeatureSnapshot | None:
        stmt = (
            select(ScenarioFeatureSnapshotRecord)
            .where(ScenarioFeatureSnapshotRecord.input_hash == input_hash)
            .order_by(ScenarioFeatureSnapshotRecord.scenario_feature_snapshot_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _scenario_feature_snapshot_from_record(record) if record else None

    def get_latest_scenario_feature_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
    ) -> ScenarioFeatureSnapshot | None:
        stmt = (
            select(ScenarioFeatureSnapshotRecord)
            .where(ScenarioFeatureSnapshotRecord.market_id == market_id)
            .where(ScenarioFeatureSnapshotRecord.available_at <= asof_timestamp)
            .order_by(
                desc(ScenarioFeatureSnapshotRecord.available_at),
                desc(ScenarioFeatureSnapshotRecord.generated_at),
                ScenarioFeatureSnapshotRecord.scenario_feature_snapshot_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _scenario_feature_snapshot_from_record(record) if record else None

    def list_scenario_features(
        self,
        *,
        market_id: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ScenarioFeatureSnapshot]:
        stmt = (
            select(ScenarioFeatureSnapshotRecord)
            .order_by(
                desc(ScenarioFeatureSnapshotRecord.available_at),
                ScenarioFeatureSnapshotRecord.scenario_feature_snapshot_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(ScenarioFeatureSnapshotRecord.market_id == market_id)
        if asof_timestamp is not None:
            stmt = stmt.where(ScenarioFeatureSnapshotRecord.available_at <= asof_timestamp)
        return [
            _scenario_feature_snapshot_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        self.session.merge(_scenario_run_to_record(run))
        self.session.flush()
        return run

    def update_scenario_run(self, run: ScenarioRun) -> ScenarioRun:
        self.session.merge(_scenario_run_to_record(run))
        self.session.flush()
        return run

    def get_scenario_run(self, scenario_run_id: str) -> ScenarioRun | None:
        record = self.session.get(ScenarioRunRecord, scenario_run_id)
        return _scenario_run_from_record(record) if record else None

    def list_scenario_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ScenarioRun]:
        stmt = (
            select(ScenarioRunRecord)
            .order_by(desc(ScenarioRunRecord.created_at), ScenarioRunRecord.scenario_run_id)
            .limit(limit)
            .offset(offset)
        )
        return [_scenario_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_scenario_run_summary(
        self,
        summary: ScenarioRunSummary,
    ) -> ScenarioRunSummary:
        self.session.merge(_scenario_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_scenario_run_summary(
        self,
        scenario_run_id: str,
    ) -> ScenarioRunSummary | None:
        stmt = (
            select(ScenarioRunSummaryRecord)
            .where(ScenarioRunSummaryRecord.scenario_run_id == scenario_run_id)
            .order_by(
                desc(ScenarioRunSummaryRecord.created_at),
                ScenarioRunSummaryRecord.summary_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _scenario_run_summary_from_record(record) if record else None

    def save_market_universe_definition(
        self,
        definition: MarketUniverseDefinition,
    ) -> MarketUniverseDefinition:
        self.session.merge(_market_universe_definition_to_record(definition))
        self.session.flush()
        return definition

    def get_market_universe_definition(
        self,
        universe_id: str,
    ) -> MarketUniverseDefinition | None:
        record = self.session.get(MarketUniverseDefinitionRecord, universe_id)
        return _market_universe_definition_from_record(record) if record else None

    def list_market_universe_definitions(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketUniverseDefinition]:
        stmt = (
            select(MarketUniverseDefinitionRecord)
            .order_by(
                MarketUniverseDefinitionRecord.universe_name,
                MarketUniverseDefinitionRecord.universe_version,
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _market_universe_definition_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_market_universe_member(
        self,
        member: MarketUniverseMember,
    ) -> MarketUniverseMember:
        self.session.merge(_market_universe_member_to_record(member))
        self.session.flush()
        return member

    def list_market_universe_members(
        self,
        *,
        universe_id: str,
        market_id: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketUniverseMember]:
        stmt = (
            select(MarketUniverseMemberRecord)
            .where(MarketUniverseMemberRecord.universe_id == universe_id)
            .order_by(
                desc(MarketUniverseMemberRecord.asof_timestamp),
                MarketUniverseMemberRecord.market_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(MarketUniverseMemberRecord.market_id == market_id)
        if asof_timestamp is not None:
            stmt = stmt.where(MarketUniverseMemberRecord.asof_timestamp <= asof_timestamp)
        return [
            _market_universe_member_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_collection_plan(self, plan: CollectionPlan) -> CollectionPlan:
        self.session.merge(_collection_plan_to_record(plan))
        self.session.flush()
        return plan

    def get_collection_plan(self, collection_plan_id: str) -> CollectionPlan | None:
        record = self.session.get(CollectionPlanRecord, collection_plan_id)
        return _collection_plan_from_record(record) if record else None

    def list_collection_plans(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CollectionPlan]:
        stmt = (
            select(CollectionPlanRecord)
            .order_by(CollectionPlanRecord.plan_name, CollectionPlanRecord.plan_version)
            .limit(limit)
            .offset(offset)
        )
        return [_collection_plan_from_record(record) for record in self.session.scalars(stmt)]

    def save_collection_run(self, run: CollectionRun) -> CollectionRun:
        self.session.merge(_collection_run_to_record(run))
        self.session.flush()
        return run

    def update_collection_run(self, run: CollectionRun) -> CollectionRun:
        return self.save_collection_run(run)

    def get_collection_run(self, collection_run_id: str) -> CollectionRun | None:
        record = self.session.get(CollectionRunRecord, collection_run_id)
        return _collection_run_from_record(record) if record else None

    def list_collection_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CollectionRun]:
        stmt = (
            select(CollectionRunRecord)
            .order_by(desc(CollectionRunRecord.created_at), CollectionRunRecord.collection_run_id)
            .limit(limit)
            .offset(offset)
        )
        return [_collection_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_backfill_job(self, job: BackfillJob) -> BackfillJob:
        self.session.merge(_backfill_job_to_record(job))
        self.session.flush()
        return job

    def update_backfill_job(self, job: BackfillJob) -> BackfillJob:
        return self.save_backfill_job(job)

    def get_backfill_job(self, backfill_job_id: str) -> BackfillJob | None:
        record = self.session.get(BackfillJobRecord, backfill_job_id)
        return _backfill_job_from_record(record) if record else None

    def list_backfill_jobs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[BackfillJob]:
        stmt = (
            select(BackfillJobRecord)
            .order_by(desc(BackfillJobRecord.created_at), BackfillJobRecord.backfill_job_id)
            .limit(limit)
            .offset(offset)
        )
        return [_backfill_job_from_record(record) for record in self.session.scalars(stmt)]

    def save_backfill_segment(self, segment: BackfillSegment) -> BackfillSegment:
        self.session.merge(_backfill_segment_to_record(segment))
        self.session.flush()
        return segment

    def update_backfill_segment(self, segment: BackfillSegment) -> BackfillSegment:
        return self.save_backfill_segment(segment)

    def list_backfill_segments(
        self,
        *,
        backfill_job_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[BackfillSegment]:
        stmt = (
            select(BackfillSegmentRecord)
            .order_by(
                BackfillSegmentRecord.segment_start_time,
                BackfillSegmentRecord.backfill_segment_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if backfill_job_id is not None:
            stmt = stmt.where(BackfillSegmentRecord.backfill_job_id == backfill_job_id)
        return [_backfill_segment_from_record(record) for record in self.session.scalars(stmt)]

    def save_data_coverage_report(
        self,
        report: DataCoverageReport,
    ) -> DataCoverageReport:
        self.session.merge(_data_coverage_report_to_record(report))
        self.session.flush()
        return report

    def get_data_coverage_report(
        self,
        coverage_report_id: str,
    ) -> DataCoverageReport | None:
        record = self.session.get(DataCoverageReportRecord, coverage_report_id)
        return _data_coverage_report_from_record(record) if record else None

    def list_data_coverage_reports(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DataCoverageReport]:
        stmt = (
            select(DataCoverageReportRecord)
            .order_by(
                desc(DataCoverageReportRecord.created_at),
                DataCoverageReportRecord.coverage_report_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [_data_coverage_report_from_record(record) for record in self.session.scalars(stmt)]

    def save_data_gap(self, gap: DataGap) -> DataGap:
        self.session.merge(_data_gap_to_record(gap))
        self.session.flush()
        return gap

    def list_data_gaps(
        self,
        *,
        market_id: str | None = None,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DataGap]:
        stmt = (
            select(DataGapRecord)
            .order_by(desc(DataGapRecord.detected_at), DataGapRecord.data_gap_id)
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(DataGapRecord.market_id == market_id)
        if asof_timestamp is not None:
            stmt = stmt.where(DataGapRecord.end_time <= asof_timestamp)
        return [_data_gap_from_record(record) for record in self.session.scalars(stmt)]

    def save_data_retention_policy(
        self,
        policy: DataRetentionPolicy,
    ) -> DataRetentionPolicy:
        self.session.merge(_data_retention_policy_to_record(policy))
        self.session.flush()
        return policy

    def list_data_retention_policies(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DataRetentionPolicy]:
        stmt = (
            select(DataRetentionPolicyRecord)
            .order_by(DataRetentionPolicyRecord.policy_name, DataRetentionPolicyRecord.created_at)
            .limit(limit)
            .offset(offset)
        )
        return [_data_retention_policy_from_record(record) for record in self.session.scalars(stmt)]

    def save_desk_watchlist(self, watchlist: DeskWatchlist) -> DeskWatchlist:
        self.session.merge(_desk_watchlist_to_record(watchlist))
        self.session.flush()
        return watchlist

    def get_desk_watchlist(self, watchlist_id: str) -> DeskWatchlist | None:
        record = self.session.get(DeskWatchlistRecord, watchlist_id)
        return _desk_watchlist_from_record(record) if record else None

    def list_desk_watchlists(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DeskWatchlist]:
        stmt = (
            select(DeskWatchlistRecord)
            .order_by(DeskWatchlistRecord.name, DeskWatchlistRecord.watchlist_id)
            .limit(limit)
            .offset(offset)
        )
        return [_desk_watchlist_from_record(record) for record in self.session.scalars(stmt)]

    def save_market_review_queue_item(
        self,
        item: MarketReviewQueueItem,
    ) -> MarketReviewQueueItem:
        self.session.merge(_market_review_queue_item_to_record(item))
        self.session.flush()
        return item

    def get_market_review_queue_item(
        self,
        queue_item_id: str,
    ) -> MarketReviewQueueItem | None:
        record = self.session.get(MarketReviewQueueItemRecord, queue_item_id)
        return _market_review_queue_item_from_record(record) if record else None

    def list_market_review_queue_items(
        self,
        *,
        market_id: str | None = None,
        queue_name: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketReviewQueueItem]:
        stmt = (
            select(MarketReviewQueueItemRecord)
            .order_by(
                desc(MarketReviewQueueItemRecord.priority_score),
                desc(MarketReviewQueueItemRecord.available_at),
                MarketReviewQueueItemRecord.market_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(MarketReviewQueueItemRecord.market_id == market_id)
        if queue_name is not None:
            stmt = stmt.where(MarketReviewQueueItemRecord.queue_name == queue_name)
        return [
            _market_review_queue_item_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_market_decision_card(self, card: MarketDecisionCard) -> MarketDecisionCard:
        self.session.merge(_market_decision_card_to_record(card))
        self.session.flush()
        return card

    def find_market_decision_card_by_hash(
        self,
        input_hash: str,
    ) -> MarketDecisionCard | None:
        stmt = (
            select(MarketDecisionCardRecord)
            .where(MarketDecisionCardRecord.input_hash == input_hash)
            .order_by(MarketDecisionCardRecord.decision_card_id)
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_decision_card_from_record(record) if record else None

    def get_latest_market_decision_card(
        self,
        market_id: str,
    ) -> MarketDecisionCard | None:
        stmt = (
            select(MarketDecisionCardRecord)
            .where(MarketDecisionCardRecord.market_id == market_id)
            .order_by(
                desc(MarketDecisionCardRecord.available_at),
                desc(MarketDecisionCardRecord.generated_at),
                MarketDecisionCardRecord.decision_card_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _market_decision_card_from_record(record) if record else None

    def list_market_decision_cards(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketDecisionCard]:
        stmt = (
            select(MarketDecisionCardRecord)
            .order_by(
                desc(MarketDecisionCardRecord.available_at),
                MarketDecisionCardRecord.decision_card_id,
            )
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(MarketDecisionCardRecord.market_id == market_id)
        return [
            _market_decision_card_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_cross_venue_comparison_card(
        self,
        card: CrossVenueComparisonCard,
    ) -> CrossVenueComparisonCard:
        self.session.merge(_cross_venue_comparison_card_to_record(card))
        self.session.flush()
        return card

    def get_cross_venue_comparison_card(
        self,
        comparison_card_id: str,
    ) -> CrossVenueComparisonCard | None:
        record = self.session.get(CrossVenueComparisonCardRecord, comparison_card_id)
        return _cross_venue_comparison_card_from_record(record) if record else None

    def list_cross_venue_comparison_cards(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueComparisonCard]:
        stmt = (
            select(CrossVenueComparisonCardRecord)
            .order_by(
                desc(CrossVenueComparisonCardRecord.asof_timestamp),
                CrossVenueComparisonCardRecord.comparison_card_id,
            )
            .limit(limit)
            .offset(offset)
        )
        return [
            _cross_venue_comparison_card_from_record(record)
            for record in self.session.scalars(stmt)
        ]

    def save_desk_review_note(self, note: DeskReviewNote) -> DeskReviewNote:
        self.session.merge(_desk_review_note_to_record(note))
        self.session.flush()
        return note

    def get_desk_review_note(self, note_id: str) -> DeskReviewNote | None:
        record = self.session.get(DeskReviewNoteRecord, note_id)
        return _desk_review_note_from_record(record) if record else None

    def list_desk_review_notes(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[DeskReviewNote]:
        stmt = (
            select(DeskReviewNoteRecord)
            .order_by(desc(DeskReviewNoteRecord.created_at), DeskReviewNoteRecord.note_id)
            .limit(limit)
            .offset(offset)
        )
        if market_id is not None:
            stmt = stmt.where(DeskReviewNoteRecord.market_id == market_id)
        return [_desk_review_note_from_record(record) for record in self.session.scalars(stmt)]

    def save_workbench_run(self, run: WorkbenchRun) -> WorkbenchRun:
        self.session.merge(_workbench_run_to_record(run))
        self.session.flush()
        return run

    def update_workbench_run(self, run: WorkbenchRun) -> WorkbenchRun:
        return self.save_workbench_run(run)

    def get_workbench_run(self, workbench_run_id: str) -> WorkbenchRun | None:
        record = self.session.get(WorkbenchRunRecord, workbench_run_id)
        return _workbench_run_from_record(record) if record else None

    def list_workbench_runs(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[WorkbenchRun]:
        stmt = (
            select(WorkbenchRunRecord)
            .order_by(desc(WorkbenchRunRecord.created_at), WorkbenchRunRecord.workbench_run_id)
            .limit(limit)
            .offset(offset)
        )
        return [_workbench_run_from_record(record) for record in self.session.scalars(stmt)]

    def save_workbench_run_summary(
        self,
        summary: WorkbenchRunSummary,
    ) -> WorkbenchRunSummary:
        self.session.merge(_workbench_run_summary_to_record(summary))
        self.session.flush()
        return summary

    def get_workbench_run_summary(
        self,
        workbench_run_id: str,
    ) -> WorkbenchRunSummary | None:
        stmt = (
            select(WorkbenchRunSummaryRecord)
            .where(WorkbenchRunSummaryRecord.workbench_run_id == workbench_run_id)
            .order_by(
                desc(WorkbenchRunSummaryRecord.created_at),
                WorkbenchRunSummaryRecord.summary_id,
            )
            .limit(1)
        )
        record = self.session.scalar(stmt)
        return _workbench_run_summary_from_record(record) if record else None


def _metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


def _json_compatible(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_compatible(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_compatible(item) for item in value]
    if isinstance(value, tuple):
        return [_json_compatible(item) for item in value]
    if isinstance(value, Decimal | datetime):
        return str(value)
    return value


def _json_metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    metadata = _json_compatible(dict(value or {}))
    return dict(metadata)


def _market_universe_definition_to_record(
    definition: MarketUniverseDefinition,
) -> MarketUniverseDefinitionRecord:
    return MarketUniverseDefinitionRecord(
        universe_id=definition.universe_id,
        universe_name=definition.universe_name,
        universe_version=definition.universe_version,
        created_at=definition.created_at,
        is_active=definition.is_active,
        venue_names=list(definition.venue_names),
        categories=list(definition.categories),
        market_statuses=list(definition.market_statuses),
        market_types=list(definition.market_types),
        include_market_ids=list(definition.include_market_ids),
        exclude_market_ids=list(definition.exclude_market_ids),
        title_include_patterns=list(definition.title_include_patterns),
        title_exclude_patterns=list(definition.title_exclude_patterns),
        min_market_data_quality_score=definition.min_market_data_quality_score,
        min_liquidity_depth=definition.min_liquidity_depth,
        metadata_json=_metadata(definition.metadata),
    )


def _market_universe_definition_from_record(
    record: MarketUniverseDefinitionRecord,
) -> MarketUniverseDefinition:
    return MarketUniverseDefinition(
        universe_id=record.universe_id,
        universe_name=record.universe_name,
        universe_version=record.universe_version,
        created_at=record.created_at,
        is_active=record.is_active,
        venue_names=list(record.venue_names),
        categories=list(record.categories),
        market_statuses=list(record.market_statuses),
        market_types=list(record.market_types),
        include_market_ids=list(record.include_market_ids),
        exclude_market_ids=list(record.exclude_market_ids),
        title_include_patterns=list(record.title_include_patterns),
        title_exclude_patterns=list(record.title_exclude_patterns),
        min_market_data_quality_score=record.min_market_data_quality_score,
        min_liquidity_depth=record.min_liquidity_depth,
        metadata=_metadata(record.metadata_json),
    )


def _market_universe_member_to_record(member: MarketUniverseMember) -> MarketUniverseMemberRecord:
    return MarketUniverseMemberRecord(
        universe_member_id=member.universe_member_id,
        universe_id=member.universe_id,
        market_id=member.market_id,
        venue_id=member.venue_id,
        venue_name=member.venue_name,
        event_id=member.event_id,
        added_at=member.added_at,
        asof_timestamp=member.asof_timestamp,
        inclusion_reason_codes=list(member.inclusion_reason_codes),
        exclusion_reason_codes=list(member.exclusion_reason_codes),
        metadata_json=_metadata(member.metadata),
    )


def _market_universe_member_from_record(record: MarketUniverseMemberRecord) -> MarketUniverseMember:
    return MarketUniverseMember(
        universe_member_id=record.universe_member_id,
        universe_id=record.universe_id,
        market_id=record.market_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        event_id=record.event_id,
        added_at=record.added_at,
        asof_timestamp=record.asof_timestamp,
        inclusion_reason_codes=list(record.inclusion_reason_codes),
        exclusion_reason_codes=list(record.exclusion_reason_codes),
        metadata=_metadata(record.metadata_json),
    )


def _collection_plan_to_record(plan: CollectionPlan) -> CollectionPlanRecord:
    return CollectionPlanRecord(
        collection_plan_id=plan.collection_plan_id,
        plan_name=plan.plan_name,
        plan_version=plan.plan_version,
        created_at=plan.created_at,
        is_active=plan.is_active,
        universe_id=plan.universe_id,
        venue_names=list(plan.venue_names),
        endpoint_types=list(plan.endpoint_types),
        cadence_seconds=plan.cadence_seconds,
        lookback_seconds=plan.lookback_seconds,
        max_markets_per_run=plan.max_markets_per_run,
        max_payloads_per_run=plan.max_payloads_per_run,
        allow_network_default=plan.allow_network_default,
        derive_market_data=plan.derive_market_data,
        compute_quality=plan.compute_quality,
        analyze_rules=plan.analyze_rules,
        recompute_verdicts=plan.recompute_verdicts,
        metadata_json=_metadata(plan.metadata),
    )


def _collection_plan_from_record(record: CollectionPlanRecord) -> CollectionPlan:
    return CollectionPlan(
        collection_plan_id=record.collection_plan_id,
        plan_name=record.plan_name,
        plan_version=record.plan_version,
        created_at=record.created_at,
        is_active=record.is_active,
        universe_id=record.universe_id,
        venue_names=list(record.venue_names),
        endpoint_types=list(record.endpoint_types),
        cadence_seconds=record.cadence_seconds,
        lookback_seconds=record.lookback_seconds,
        max_markets_per_run=record.max_markets_per_run,
        max_payloads_per_run=record.max_payloads_per_run,
        allow_network_default=record.allow_network_default,
        derive_market_data=record.derive_market_data,
        compute_quality=record.compute_quality,
        analyze_rules=record.analyze_rules,
        recompute_verdicts=record.recompute_verdicts,
        metadata=_metadata(record.metadata_json),
    )


def _collection_run_to_record(run: CollectionRun) -> CollectionRunRecord:
    return CollectionRunRecord(
        collection_run_id=run.collection_run_id,
        collection_plan_id=run.collection_plan_id,
        universe_id=run.universe_id,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        mode=run.mode.value,
        asof_timestamp=run.asof_timestamp,
        allow_network=run.allow_network,
        venue_names=list(run.venue_names),
        market_ids=list(run.market_ids),
        endpoint_types=list(run.endpoint_types),
        payloads_archived=run.payloads_archived,
        markets_processed=run.markets_processed,
        price_snapshots_created=run.price_snapshots_created,
        liquidity_snapshots_created=run.liquidity_snapshots_created,
        quality_reports_created=run.quality_reports_created,
        ingestion_runs_created=run.ingestion_runs_created,
        errors_count=run.errors_count,
        metadata_json=_metadata(run.metadata),
    )


def _collection_run_from_record(record: CollectionRunRecord) -> CollectionRun:
    return CollectionRun(
        collection_run_id=record.collection_run_id,
        collection_plan_id=record.collection_plan_id,
        universe_id=record.universe_id,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=CollectionRunStatus(record.status),
        mode=CollectionRunMode(record.mode),
        asof_timestamp=record.asof_timestamp,
        allow_network=record.allow_network,
        venue_names=list(record.venue_names),
        market_ids=list(record.market_ids),
        endpoint_types=list(record.endpoint_types),
        payloads_archived=record.payloads_archived,
        markets_processed=record.markets_processed,
        price_snapshots_created=record.price_snapshots_created,
        liquidity_snapshots_created=record.liquidity_snapshots_created,
        quality_reports_created=record.quality_reports_created,
        ingestion_runs_created=record.ingestion_runs_created,
        errors_count=record.errors_count,
        metadata=_metadata(record.metadata_json),
    )


def _backfill_job_to_record(job: BackfillJob) -> BackfillJobRecord:
    return BackfillJobRecord(
        backfill_job_id=job.backfill_job_id,
        job_name=job.job_name,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        status=job.status.value,
        venue_name=job.venue_name,
        market_ids=list(job.market_ids),
        endpoint_types=list(job.endpoint_types),
        start_time=job.start_time,
        end_time=job.end_time,
        interval_seconds=job.interval_seconds,
        allow_network=job.allow_network,
        max_segments=job.max_segments,
        segments_created=job.segments_created,
        segments_completed=job.segments_completed,
        segments_failed=job.segments_failed,
        metadata_json=_metadata(job.metadata),
    )


def _backfill_job_from_record(record: BackfillJobRecord) -> BackfillJob:
    return BackfillJob(
        backfill_job_id=record.backfill_job_id,
        job_name=record.job_name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=BackfillJobStatus(record.status),
        venue_name=record.venue_name,
        market_ids=list(record.market_ids),
        endpoint_types=list(record.endpoint_types),
        start_time=record.start_time,
        end_time=record.end_time,
        interval_seconds=record.interval_seconds,
        allow_network=record.allow_network,
        max_segments=record.max_segments,
        segments_created=record.segments_created,
        segments_completed=record.segments_completed,
        segments_failed=record.segments_failed,
        metadata=_metadata(record.metadata_json),
    )


def _backfill_segment_to_record(segment: BackfillSegment) -> BackfillSegmentRecord:
    return BackfillSegmentRecord(
        backfill_segment_id=segment.backfill_segment_id,
        backfill_job_id=segment.backfill_job_id,
        venue_name=segment.venue_name,
        market_id=segment.market_id,
        endpoint_type=segment.endpoint_type,
        segment_start_time=segment.segment_start_time,
        segment_end_time=segment.segment_end_time,
        status=segment.status.value,
        supported=segment.supported,
        unsupported_reason=segment.unsupported_reason,
        payloads_archived=segment.payloads_archived,
        snapshots_created=segment.snapshots_created,
        errors_count=segment.errors_count,
        metadata_json=_metadata(segment.metadata),
    )


def _backfill_segment_from_record(record: BackfillSegmentRecord) -> BackfillSegment:
    return BackfillSegment(
        backfill_segment_id=record.backfill_segment_id,
        backfill_job_id=record.backfill_job_id,
        venue_name=record.venue_name,
        market_id=record.market_id,
        endpoint_type=record.endpoint_type,
        segment_start_time=record.segment_start_time,
        segment_end_time=record.segment_end_time,
        status=BackfillSegmentStatus(record.status),
        supported=record.supported,
        unsupported_reason=record.unsupported_reason,
        payloads_archived=record.payloads_archived,
        snapshots_created=record.snapshots_created,
        errors_count=record.errors_count,
        metadata=_metadata(record.metadata_json),
    )


def _data_coverage_report_to_record(report: DataCoverageReport) -> DataCoverageReportRecord:
    return DataCoverageReportRecord(
        coverage_report_id=report.coverage_report_id,
        asof_timestamp=report.asof_timestamp,
        created_at=report.created_at,
        scope_type=report.scope_type.value,
        universe_id=report.universe_id,
        market_id=report.market_id,
        venue_name=report.venue_name,
        start_time=report.start_time,
        end_time=report.end_time,
        total_markets=report.total_markets,
        markets_with_rules=report.markets_with_rules,
        markets_with_orderbooks=report.markets_with_orderbooks,
        markets_with_price_snapshots=report.markets_with_price_snapshots,
        markets_with_liquidity_snapshots=report.markets_with_liquidity_snapshots,
        markets_with_quality_reports=report.markets_with_quality_reports,
        stale_markets=report.stale_markets,
        missing_rule_markets=report.missing_rule_markets,
        missing_price_markets=report.missing_price_markets,
        missing_liquidity_markets=report.missing_liquidity_markets,
        average_quality_score=report.average_quality_score,
        coverage_score=report.coverage_score,
        reason_codes=list(report.reason_codes),
        metadata_json=_metadata(report.metadata),
    )


def _data_coverage_report_from_record(record: DataCoverageReportRecord) -> DataCoverageReport:
    return DataCoverageReport(
        coverage_report_id=record.coverage_report_id,
        asof_timestamp=record.asof_timestamp,
        created_at=record.created_at,
        scope_type=CoverageScopeType(record.scope_type),
        universe_id=record.universe_id,
        market_id=record.market_id,
        venue_name=record.venue_name,
        start_time=record.start_time,
        end_time=record.end_time,
        total_markets=record.total_markets,
        markets_with_rules=record.markets_with_rules,
        markets_with_orderbooks=record.markets_with_orderbooks,
        markets_with_price_snapshots=record.markets_with_price_snapshots,
        markets_with_liquidity_snapshots=record.markets_with_liquidity_snapshots,
        markets_with_quality_reports=record.markets_with_quality_reports,
        stale_markets=record.stale_markets,
        missing_rule_markets=record.missing_rule_markets,
        missing_price_markets=record.missing_price_markets,
        missing_liquidity_markets=record.missing_liquidity_markets,
        average_quality_score=record.average_quality_score,
        coverage_score=record.coverage_score,
        reason_codes=list(record.reason_codes),
        metadata=_metadata(record.metadata_json),
    )


def _data_gap_to_record(gap: DataGap) -> DataGapRecord:
    return DataGapRecord(
        data_gap_id=gap.data_gap_id,
        coverage_report_id=gap.coverage_report_id,
        market_id=gap.market_id,
        venue_name=gap.venue_name,
        gap_type=gap.gap_type.value,
        severity=gap.severity.value,
        start_time=gap.start_time,
        end_time=gap.end_time,
        detected_at=gap.detected_at,
        expected_cadence_seconds=gap.expected_cadence_seconds,
        observed_count=gap.observed_count,
        expected_count=gap.expected_count,
        reason_code=gap.reason_code,
        description=gap.description,
        metadata_json=_metadata(gap.metadata),
    )


def _data_gap_from_record(record: DataGapRecord) -> DataGap:
    return DataGap(
        data_gap_id=record.data_gap_id,
        coverage_report_id=record.coverage_report_id,
        market_id=record.market_id,
        venue_name=record.venue_name,
        gap_type=DataGapType(record.gap_type),
        severity=DataGapSeverity(record.severity),
        start_time=record.start_time,
        end_time=record.end_time,
        detected_at=record.detected_at,
        expected_cadence_seconds=record.expected_cadence_seconds,
        observed_count=record.observed_count,
        expected_count=record.expected_count,
        reason_code=record.reason_code,
        description=record.description,
        metadata=_metadata(record.metadata_json),
    )


def _data_retention_policy_to_record(policy: DataRetentionPolicy) -> DataRetentionPolicyRecord:
    return DataRetentionPolicyRecord(
        retention_policy_id=policy.retention_policy_id,
        policy_name=policy.policy_name,
        created_at=policy.created_at,
        is_active=policy.is_active,
        raw_payload_retention_days=policy.raw_payload_retention_days,
        orderbook_snapshot_retention_days=policy.orderbook_snapshot_retention_days,
        price_snapshot_retention_days=policy.price_snapshot_retention_days,
        liquidity_snapshot_retention_days=policy.liquidity_snapshot_retention_days,
        quality_report_retention_days=policy.quality_report_retention_days,
        archive_before_delete=policy.archive_before_delete,
        metadata_json=_metadata(policy.metadata),
    )


def _data_retention_policy_from_record(record: DataRetentionPolicyRecord) -> DataRetentionPolicy:
    return DataRetentionPolicy(
        retention_policy_id=record.retention_policy_id,
        policy_name=record.policy_name,
        created_at=record.created_at,
        is_active=record.is_active,
        raw_payload_retention_days=record.raw_payload_retention_days,
        orderbook_snapshot_retention_days=record.orderbook_snapshot_retention_days,
        price_snapshot_retention_days=record.price_snapshot_retention_days,
        liquidity_snapshot_retention_days=record.liquidity_snapshot_retention_days,
        quality_report_retention_days=record.quality_report_retention_days,
        archive_before_delete=record.archive_before_delete,
        metadata=_metadata(record.metadata_json),
    )


def _desk_watchlist_to_record(watchlist: DeskWatchlist) -> DeskWatchlistRecord:
    return DeskWatchlistRecord(
        watchlist_id=watchlist.watchlist_id,
        name=watchlist.name,
        description=watchlist.description,
        created_at=watchlist.created_at,
        is_active=watchlist.is_active,
        market_ids=list(watchlist.market_ids),
        tags=list(watchlist.tags),
        metadata_json=_json_metadata(watchlist.metadata),
    )


def _desk_watchlist_from_record(record: DeskWatchlistRecord) -> DeskWatchlist:
    return DeskWatchlist(
        watchlist_id=record.watchlist_id,
        name=record.name,
        description=record.description,
        created_at=record.created_at,
        is_active=record.is_active,
        market_ids=list(record.market_ids),
        tags=list(record.tags),
        metadata=_metadata(record.metadata_json),
    )


def _market_review_queue_item_to_record(
    item: MarketReviewQueueItem,
) -> MarketReviewQueueItemRecord:
    return MarketReviewQueueItemRecord(
        queue_item_id=item.queue_item_id,
        market_id=item.market_id,
        asof_timestamp=item.asof_timestamp,
        generated_at=item.generated_at,
        available_at=item.available_at,
        queue_name=item.queue_name,
        priority_score=item.priority_score,
        priority_bucket=item.priority_bucket.value,
        review_status=item.review_status.value,
        primary_reason_code=item.primary_reason_code,
        reason_codes=list(item.reason_codes),
        evidence_ref_ids=list(item.evidence_ref_ids),
        latest_quality_report_id=item.latest_quality_report_id,
        latest_integrity_assessment_id=item.latest_integrity_assessment_id,
        latest_equivalence_assessment_ids=list(item.latest_equivalence_assessment_ids),
        latest_divergence_assessment_ids=list(item.latest_divergence_assessment_ids),
        latest_pretrade_decision_id=item.latest_pretrade_decision_id,
        latest_research_signal_ids=list(item.latest_research_signal_ids),
        latest_paper_order_ids=list(item.latest_paper_order_ids),
        metadata_json=_json_metadata(item.metadata),
    )


def _market_review_queue_item_from_record(
    record: MarketReviewQueueItemRecord,
) -> MarketReviewQueueItem:
    return MarketReviewQueueItem(
        queue_item_id=record.queue_item_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        queue_name=record.queue_name,
        priority_score=record.priority_score,
        priority_bucket=ReviewPriorityBucket(record.priority_bucket),
        review_status=ReviewStatus(record.review_status),
        primary_reason_code=record.primary_reason_code,
        reason_codes=list(record.reason_codes),
        evidence_ref_ids=list(record.evidence_ref_ids),
        latest_quality_report_id=record.latest_quality_report_id,
        latest_integrity_assessment_id=record.latest_integrity_assessment_id,
        latest_equivalence_assessment_ids=list(record.latest_equivalence_assessment_ids),
        latest_divergence_assessment_ids=list(record.latest_divergence_assessment_ids),
        latest_pretrade_decision_id=record.latest_pretrade_decision_id,
        latest_research_signal_ids=list(record.latest_research_signal_ids),
        latest_paper_order_ids=list(record.latest_paper_order_ids),
        metadata=_metadata(record.metadata_json),
    )


def _market_decision_card_to_record(card: MarketDecisionCard) -> MarketDecisionCardRecord:
    return MarketDecisionCardRecord(
        decision_card_id=card.decision_card_id,
        market_id=card.market_id,
        asof_timestamp=card.asof_timestamp,
        generated_at=card.generated_at,
        available_at=card.available_at,
        title=card.title,
        venue_name=card.venue_name,
        market_status=card.market_status,
        category=card.category,
        latest_price=card.latest_price,
        bid=card.bid,
        ask=card.ask,
        spread=card.spread,
        liquidity_summary=_json_metadata(card.liquidity_summary),
        data_quality_summary=_json_metadata(card.data_quality_summary),
        rule_summary=_json_metadata(card.rule_summary),
        integrity_summary=_json_metadata(card.integrity_summary),
        equivalence_summary=_json_metadata(card.equivalence_summary),
        divergence_summary=_json_metadata(card.divergence_summary),
        pretrade_summary=_json_metadata(card.pretrade_summary),
        paper_summary=_json_metadata(card.paper_summary),
        research_summary=_json_metadata(card.research_summary),
        scenario_summary=_json_metadata(card.scenario_summary),
        data_gap_summary=_json_metadata(card.data_gap_summary),
        review_priority_score=card.review_priority_score,
        review_reason_codes=list(card.review_reason_codes),
        recommended_next_review_action=card.recommended_next_review_action.value,
        source_ref_ids=list(card.source_ref_ids),
        input_hash=card.input_hash,
        output_hash=card.output_hash,
        metadata_json=_json_metadata(card.metadata),
    )


def _market_decision_card_from_record(record: MarketDecisionCardRecord) -> MarketDecisionCard:
    return MarketDecisionCard(
        decision_card_id=record.decision_card_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        title=record.title,
        venue_name=record.venue_name,
        market_status=record.market_status,
        category=record.category,
        latest_price=record.latest_price,
        bid=record.bid,
        ask=record.ask,
        spread=record.spread,
        liquidity_summary=_metadata(record.liquidity_summary),
        data_quality_summary=_metadata(record.data_quality_summary),
        rule_summary=_metadata(record.rule_summary),
        integrity_summary=_metadata(record.integrity_summary),
        equivalence_summary=_metadata(record.equivalence_summary),
        divergence_summary=_metadata(record.divergence_summary),
        pretrade_summary=_metadata(record.pretrade_summary),
        paper_summary=_metadata(record.paper_summary),
        research_summary=_metadata(record.research_summary),
        scenario_summary=_metadata(record.scenario_summary),
        data_gap_summary=_metadata(record.data_gap_summary),
        review_priority_score=record.review_priority_score,
        review_reason_codes=list(record.review_reason_codes),
        recommended_next_review_action=RecommendedReviewAction(
            record.recommended_next_review_action
        ),
        source_ref_ids=list(record.source_ref_ids),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _cross_venue_comparison_card_to_record(
    card: CrossVenueComparisonCard,
) -> CrossVenueComparisonCardRecord:
    return CrossVenueComparisonCardRecord(
        comparison_card_id=card.comparison_card_id,
        equivalence_assessment_id=card.equivalence_assessment_id,
        divergence_assessment_id=card.divergence_assessment_id,
        asof_timestamp=card.asof_timestamp,
        left_market_id=card.left_market_id,
        right_market_id=card.right_market_id,
        equivalence_status=card.equivalence_status,
        comparison_permission=card.comparison_permission,
        equivalence_score=card.equivalence_score,
        divergence_status=card.divergence_status,
        divergence_score=card.divergence_score,
        aligned_price_summary=_json_metadata(card.aligned_price_summary),
        liquidity_comparison=_json_metadata(card.liquidity_comparison),
        data_quality_comparison=_json_metadata(card.data_quality_comparison),
        rule_comparison=_json_metadata(card.rule_comparison),
        integrity_comparison=_json_metadata(card.integrity_comparison),
        reason_codes=list(card.reason_codes),
        recommended_next_review_action=card.recommended_next_review_action.value,
        source_ref_ids=list(card.source_ref_ids),
        metadata_json=_json_metadata(card.metadata),
    )


def _cross_venue_comparison_card_from_record(
    record: CrossVenueComparisonCardRecord,
) -> CrossVenueComparisonCard:
    return CrossVenueComparisonCard(
        comparison_card_id=record.comparison_card_id,
        equivalence_assessment_id=record.equivalence_assessment_id,
        divergence_assessment_id=record.divergence_assessment_id,
        asof_timestamp=record.asof_timestamp,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        equivalence_status=record.equivalence_status,
        comparison_permission=record.comparison_permission,
        equivalence_score=record.equivalence_score,
        divergence_status=record.divergence_status,
        divergence_score=record.divergence_score,
        aligned_price_summary=_metadata(record.aligned_price_summary),
        liquidity_comparison=_metadata(record.liquidity_comparison),
        data_quality_comparison=_metadata(record.data_quality_comparison),
        rule_comparison=_metadata(record.rule_comparison),
        integrity_comparison=_metadata(record.integrity_comparison),
        reason_codes=list(record.reason_codes),
        recommended_next_review_action=RecommendedReviewAction(
            record.recommended_next_review_action
        ),
        source_ref_ids=list(record.source_ref_ids),
        metadata=_metadata(record.metadata_json),
    )


def _desk_review_note_to_record(note: DeskReviewNote) -> DeskReviewNoteRecord:
    return DeskReviewNoteRecord(
        note_id=note.note_id,
        created_at=note.created_at,
        market_id=note.market_id,
        queue_item_id=note.queue_item_id,
        decision_card_id=note.decision_card_id,
        comparison_card_id=note.comparison_card_id,
        author=note.author,
        note_type=note.note_type.value,
        text=note.text,
        tags=list(note.tags),
        metadata_json=_json_metadata(note.metadata),
    )


def _desk_review_note_from_record(record: DeskReviewNoteRecord) -> DeskReviewNote:
    return DeskReviewNote(
        note_id=record.note_id,
        created_at=record.created_at,
        market_id=record.market_id,
        queue_item_id=record.queue_item_id,
        decision_card_id=record.decision_card_id,
        comparison_card_id=record.comparison_card_id,
        author=record.author,
        note_type=DeskReviewNoteType(record.note_type),
        text=record.text,
        tags=list(record.tags),
        metadata=_metadata(record.metadata_json),
    )


def _workbench_run_to_record(run: WorkbenchRun) -> WorkbenchRunRecord:
    return WorkbenchRunRecord(
        workbench_run_id=run.workbench_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        asof_timestamp=run.asof_timestamp,
        market_ids=list(run.market_ids),
        queues_built=run.queues_built,
        cards_built=run.cards_built,
        comparison_cards_built=run.comparison_cards_built,
        errors_count=run.errors_count,
        metadata_json=_json_metadata(run.metadata),
    )


def _workbench_run_from_record(record: WorkbenchRunRecord) -> WorkbenchRun:
    return WorkbenchRun(
        workbench_run_id=record.workbench_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=WorkbenchRunStatus(record.status),
        asof_timestamp=record.asof_timestamp,
        market_ids=list(record.market_ids),
        queues_built=record.queues_built,
        cards_built=record.cards_built,
        comparison_cards_built=record.comparison_cards_built,
        errors_count=record.errors_count,
        metadata=_metadata(record.metadata_json),
    )


def _workbench_run_summary_to_record(
    summary: WorkbenchRunSummary,
) -> WorkbenchRunSummaryRecord:
    return WorkbenchRunSummaryRecord(
        summary_id=summary.summary_id,
        workbench_run_id=summary.workbench_run_id,
        created_at=summary.created_at,
        total_queue_items=summary.total_queue_items,
        total_decision_cards=summary.total_decision_cards,
        total_comparison_cards=summary.total_comparison_cards,
        priority_counts=dict(summary.priority_counts),
        review_action_counts=dict(summary.review_action_counts),
        top_reason_codes=dict(summary.top_reason_codes),
        markets_reviewed=summary.markets_reviewed,
        metadata_json=_json_metadata(summary.metadata),
    )


def _workbench_run_summary_from_record(
    record: WorkbenchRunSummaryRecord,
) -> WorkbenchRunSummary:
    return WorkbenchRunSummary(
        summary_id=record.summary_id,
        workbench_run_id=record.workbench_run_id,
        created_at=record.created_at,
        total_queue_items=record.total_queue_items,
        total_decision_cards=record.total_decision_cards,
        total_comparison_cards=record.total_comparison_cards,
        priority_counts=dict(record.priority_counts),
        review_action_counts=dict(record.review_action_counts),
        top_reason_codes=dict(record.top_reason_codes),
        markets_reviewed=record.markets_reviewed,
        metadata=_metadata(record.metadata_json),
    )


def _venue_to_record(venue: Venue) -> VenueRecord:
    return VenueRecord(
        venue_id=venue.venue_id,
        name=venue.name,
        jurisdiction=venue.jurisdiction,
        venue_type=venue.venue_type.value,
        metadata_json=_metadata(venue.metadata),
    )


def _venue_from_record(record: VenueRecord) -> Venue:
    return Venue(
        venue_id=record.venue_id,
        name=record.name,
        jurisdiction=record.jurisdiction,
        venue_type=VenueType(record.venue_type),
        metadata=_metadata(record.metadata_json),
    )


def _event_to_record(event: Event) -> EventRecord:
    return EventRecord(
        event_id=event.event_id,
        venue_id=event.venue_id,
        title=event.title,
        category=event.category,
        start_time=event.start_time,
        end_time=event.end_time,
        metadata_json=_metadata(event.metadata),
    )


def _event_from_record(record: EventRecord) -> Event:
    return Event(
        event_id=record.event_id,
        venue_id=record.venue_id,
        title=record.title,
        category=record.category,
        start_time=record.start_time,
        end_time=record.end_time,
        metadata=_metadata(record.metadata_json),
    )


def _market_to_record(market: Market) -> MarketRecord:
    return MarketRecord(
        market_id=market.market_id,
        venue_id=market.venue_id,
        event_id=market.event_id,
        title=market.title,
        description=market.description,
        market_type=market.market_type.value,
        status=market.status.value,
        created_time=market.created_time,
        close_time=market.close_time,
        settlement_time=market.settlement_time,
        metadata_json=_metadata(market.metadata),
    )


def _market_from_record(record: MarketRecord) -> Market:
    return Market(
        market_id=record.market_id,
        venue_id=record.venue_id,
        event_id=record.event_id,
        title=record.title,
        description=record.description,
        market_type=MarketType(record.market_type),
        status=MarketStatus(record.status),
        created_time=record.created_time,
        close_time=record.close_time,
        settlement_time=record.settlement_time,
        metadata=_metadata(record.metadata_json),
    )


def _outcome_to_record(outcome: Outcome) -> OutcomeRecord:
    return OutcomeRecord(
        outcome_id=outcome.outcome_id,
        market_id=outcome.market_id,
        label=outcome.label,
        payout=outcome.payout,
        metadata_json=_metadata(outcome.metadata),
    )


def _outcome_from_record(record: OutcomeRecord) -> Outcome:
    return Outcome(
        outcome_id=record.outcome_id,
        market_id=record.market_id,
        label=record.label,
        payout=record.payout,
        metadata=_metadata(record.metadata_json),
    )


def _rule_snapshot_to_record(snapshot: MarketRuleSnapshot) -> MarketRuleSnapshotRecord:
    return MarketRuleSnapshotRecord(
        rule_snapshot_id=snapshot.rule_snapshot_id,
        market_id=snapshot.market_id,
        captured_at=snapshot.captured_at,
        raw_rule_text=snapshot.raw_rule_text,
        normalized_rule_text=snapshot.normalized_rule_text,
        resolution_source=snapshot.resolution_source,
        settlement_authority=snapshot.settlement_authority,
        time_zone=snapshot.time_zone,
        rule_hash=snapshot.rule_hash,
        metadata_json=_metadata(snapshot.metadata),
    )


def _rule_snapshot_from_record(record: MarketRuleSnapshotRecord) -> MarketRuleSnapshot:
    return MarketRuleSnapshot(
        rule_snapshot_id=record.rule_snapshot_id,
        market_id=record.market_id,
        captured_at=record.captured_at,
        raw_rule_text=record.raw_rule_text,
        normalized_rule_text=record.normalized_rule_text,
        resolution_source=record.resolution_source,
        settlement_authority=record.settlement_authority,
        time_zone=record.time_zone,
        rule_hash=record.rule_hash,
        metadata=_metadata(record.metadata_json),
    )


def _orderbook_snapshot_to_record(snapshot: OrderBookSnapshot) -> OrderBookSnapshotRecord:
    return OrderBookSnapshotRecord(
        snapshot_id=snapshot.snapshot_id,
        market_id=snapshot.market_id,
        captured_at=snapshot.captured_at,
        bids=[_price_level_to_json(level) for level in snapshot.bids],
        asks=[_price_level_to_json(level) for level in snapshot.asks],
        metadata_json=_metadata(snapshot.metadata),
    )


def _orderbook_snapshot_from_record(record: OrderBookSnapshotRecord) -> OrderBookSnapshot:
    return OrderBookSnapshot(
        snapshot_id=record.snapshot_id,
        market_id=record.market_id,
        captured_at=record.captured_at,
        bids=[_price_level_from_json(level) for level in record.bids],
        asks=[_price_level_from_json(level) for level in record.asks],
        metadata=_metadata(record.metadata_json),
    )


def _trade_print_to_record(trade_print: TradePrint) -> TradePrintRecord:
    return TradePrintRecord(
        trade_id=trade_print.trade_id,
        market_id=trade_print.market_id,
        executed_at=trade_print.executed_at,
        price=trade_print.price,
        quantity=trade_print.quantity,
        side=trade_print.side.value,
        metadata_json=_metadata(trade_print.metadata),
    )


def _trade_print_from_record(record: TradePrintRecord) -> TradePrint:
    return TradePrint(
        trade_id=record.trade_id,
        market_id=record.market_id,
        executed_at=record.executed_at,
        price=record.price,
        quantity=record.quantity,
        side=TradeSide(record.side),
        metadata=_metadata(record.metadata_json),
    )


def _resolution_event_to_record(resolution_event: ResolutionEvent) -> ResolutionEventRecord:
    return ResolutionEventRecord(
        resolution_event_id=resolution_event.resolution_event_id,
        market_id=resolution_event.market_id,
        resolved_at=resolution_event.resolved_at,
        outcome_id=resolution_event.outcome_id,
        result_label=resolution_event.result_label,
        resolution_source_url=resolution_event.resolution_source_url,
        notes=resolution_event.notes,
        metadata_json=_metadata(resolution_event.metadata),
    )


def _resolution_event_from_record(record: ResolutionEventRecord) -> ResolutionEvent:
    return ResolutionEvent(
        resolution_event_id=record.resolution_event_id,
        market_id=record.market_id,
        resolved_at=record.resolved_at,
        outcome_id=record.outcome_id,
        result_label=record.result_label,
        resolution_source_url=record.resolution_source_url,
        notes=record.notes,
        metadata=_metadata(record.metadata_json),
    )


def _trust_verdict_to_record(verdict: TrustVerdict) -> TrustVerdictRecord:
    return TrustVerdictRecord(
        verdict_id=verdict.verdict_id,
        market_id=verdict.market_id,
        asof_timestamp=verdict.asof_timestamp,
        price_integrity_score=verdict.price_integrity_score,
        resolution_risk_score=verdict.resolution_risk_score,
        liquidity_risk_score=verdict.liquidity_risk_score,
        cross_venue_consistency_score=verdict.cross_venue_consistency_score,
        information_freshness_score=verdict.information_freshness_score,
        manipulation_risk_score=verdict.manipulation_risk_score,
        action=verdict.action.value,
        reason_codes=list(verdict.reason_codes),
        source_refs=list(verdict.source_refs),
        model_versions=_metadata(verdict.model_versions),
        data_versions=_metadata(verdict.data_versions),
        metadata_json=_metadata(verdict.metadata),
    )


def _trust_verdict_from_record(record: TrustVerdictRecord) -> TrustVerdict:
    return TrustVerdict(
        verdict_id=record.verdict_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        price_integrity_score=record.price_integrity_score,
        resolution_risk_score=record.resolution_risk_score,
        liquidity_risk_score=record.liquidity_risk_score,
        cross_venue_consistency_score=record.cross_venue_consistency_score,
        information_freshness_score=record.information_freshness_score,
        manipulation_risk_score=record.manipulation_risk_score,
        action=VerdictAction(record.action),
        reason_codes=list(record.reason_codes),
        source_refs=list(record.source_refs),
        model_versions=_metadata(record.model_versions),
        data_versions=_metadata(record.data_versions),
        metadata=_metadata(record.metadata_json),
    )


def _resolution_source_to_record(source: ResolutionSource) -> ResolutionSourceRecord:
    return ResolutionSourceRecord(
        source_id=source.source_id,
        canonical_name=source.canonical_name,
        source_type=source.source_type.value,
        url=source.url,
        jurisdiction=source.jurisdiction,
        reliability_rank=source.reliability_rank,
        metadata_json=_metadata(source.metadata),
    )


def _resolution_source_from_record(record: ResolutionSourceRecord) -> ResolutionSource:
    return ResolutionSource(
        source_id=record.source_id,
        canonical_name=record.canonical_name,
        source_type=ResolutionSourceType(record.source_type),
        url=record.url,
        jurisdiction=record.jurisdiction,
        reliability_rank=record.reliability_rank,
        metadata=_metadata(record.metadata_json),
    )


def _resolution_predicate_to_record(
    predicate: ResolutionPredicate,
) -> ResolutionPredicateRecord:
    return ResolutionPredicateRecord(
        predicate_id=predicate.predicate_id,
        market_id=predicate.market_id,
        rule_snapshot_id=predicate.rule_snapshot_id,
        captured_at=predicate.captured_at,
        predicate_type=predicate.predicate_type.value,
        parse_status=predicate.parse_status.value,
        subject=predicate.subject,
        condition=predicate.condition,
        threshold_value=predicate.threshold_value,
        threshold_unit=predicate.threshold_unit,
        comparator=predicate.comparator.value if predicate.comparator else None,
        time_window_start=predicate.time_window_start,
        time_window_end=predicate.time_window_end,
        time_zone=predicate.time_zone,
        resolution_source_id=predicate.resolution_source_id,
        settlement_authority=predicate.settlement_authority,
        confidence_score=predicate.confidence_score,
        evidence_spans=_evidence_spans_to_json(predicate.evidence_spans),
        normalized_predicate_text=predicate.normalized_predicate_text,
        metadata_json=_metadata(predicate.metadata),
    )


def _resolution_predicate_from_record(
    record: ResolutionPredicateRecord,
) -> ResolutionPredicate:
    return ResolutionPredicate(
        predicate_id=record.predicate_id,
        market_id=record.market_id,
        rule_snapshot_id=record.rule_snapshot_id,
        captured_at=record.captured_at,
        predicate_type=PredicateType(record.predicate_type),
        parse_status=ParseStatus(record.parse_status),
        subject=record.subject,
        condition=record.condition,
        threshold_value=record.threshold_value,
        threshold_unit=record.threshold_unit,
        comparator=Comparator(record.comparator) if record.comparator else None,
        time_window_start=record.time_window_start,
        time_window_end=record.time_window_end,
        time_zone=record.time_zone,
        resolution_source_id=record.resolution_source_id,
        settlement_authority=record.settlement_authority,
        confidence_score=record.confidence_score,
        evidence_spans=_evidence_spans_from_json(record.evidence_spans),
        normalized_predicate_text=record.normalized_predicate_text,
        metadata=_metadata(record.metadata_json),
    )


def _ambiguity_assessment_to_record(
    assessment: AmbiguityAssessment,
) -> AmbiguityAssessmentRecord:
    return AmbiguityAssessmentRecord(
        assessment_id=assessment.assessment_id,
        market_id=assessment.market_id,
        rule_snapshot_id=assessment.rule_snapshot_id,
        captured_at=assessment.captured_at,
        overall_score=assessment.overall_score,
        source_ambiguity_score=assessment.source_ambiguity_score,
        temporal_ambiguity_score=assessment.temporal_ambiguity_score,
        definition_ambiguity_score=assessment.definition_ambiguity_score,
        measurement_ambiguity_score=assessment.measurement_ambiguity_score,
        actor_ambiguity_score=assessment.actor_ambiguity_score,
        threshold_ambiguity_score=assessment.threshold_ambiguity_score,
        dispute_ambiguity_score=assessment.dispute_ambiguity_score,
        exceptional_case_ambiguity_score=assessment.exceptional_case_ambiguity_score,
        venue_adjudication_ambiguity_score=assessment.venue_adjudication_ambiguity_score,
        reason_codes=list(assessment.reason_codes),
        evidence_spans=_evidence_spans_to_json(assessment.evidence_spans),
        metadata_json=_metadata(assessment.metadata),
    )


def _ambiguity_assessment_from_record(
    record: AmbiguityAssessmentRecord,
) -> AmbiguityAssessment:
    return AmbiguityAssessment(
        assessment_id=record.assessment_id,
        market_id=record.market_id,
        rule_snapshot_id=record.rule_snapshot_id,
        captured_at=record.captured_at,
        overall_score=record.overall_score,
        source_ambiguity_score=record.source_ambiguity_score,
        temporal_ambiguity_score=record.temporal_ambiguity_score,
        definition_ambiguity_score=record.definition_ambiguity_score,
        measurement_ambiguity_score=record.measurement_ambiguity_score,
        actor_ambiguity_score=record.actor_ambiguity_score,
        threshold_ambiguity_score=record.threshold_ambiguity_score,
        dispute_ambiguity_score=record.dispute_ambiguity_score,
        exceptional_case_ambiguity_score=record.exceptional_case_ambiguity_score,
        venue_adjudication_ambiguity_score=record.venue_adjudication_ambiguity_score,
        reason_codes=list(record.reason_codes),
        evidence_spans=_evidence_spans_from_json(record.evidence_spans),
        metadata=_metadata(record.metadata_json),
    )


def _rule_snapshot_diff_to_record(diff: RuleSnapshotDiff) -> RuleSnapshotDiffRecord:
    return RuleSnapshotDiffRecord(
        diff_id=diff.diff_id,
        market_id=diff.market_id,
        from_rule_snapshot_id=diff.from_rule_snapshot_id,
        to_rule_snapshot_id=diff.to_rule_snapshot_id,
        created_at=diff.created_at,
        raw_text_changed=diff.raw_text_changed,
        normalized_text_changed=diff.normalized_text_changed,
        resolution_source_changed=diff.resolution_source_changed,
        settlement_authority_changed=diff.settlement_authority_changed,
        time_zone_changed=diff.time_zone_changed,
        old_rule_hash=diff.old_rule_hash,
        new_rule_hash=diff.new_rule_hash,
        changed_terms=list(diff.changed_terms),
        added_text_fragments=list(diff.added_text_fragments),
        removed_text_fragments=list(diff.removed_text_fragments),
        semantic_change_flags=list(diff.semantic_change_flags),
        metadata_json=_metadata(diff.metadata),
    )


def _rule_snapshot_diff_from_record(record: RuleSnapshotDiffRecord) -> RuleSnapshotDiff:
    return RuleSnapshotDiff(
        diff_id=record.diff_id,
        market_id=record.market_id,
        from_rule_snapshot_id=record.from_rule_snapshot_id,
        to_rule_snapshot_id=record.to_rule_snapshot_id,
        created_at=record.created_at,
        raw_text_changed=record.raw_text_changed,
        normalized_text_changed=record.normalized_text_changed,
        resolution_source_changed=record.resolution_source_changed,
        settlement_authority_changed=record.settlement_authority_changed,
        time_zone_changed=record.time_zone_changed,
        old_rule_hash=record.old_rule_hash,
        new_rule_hash=record.new_rule_hash,
        changed_terms=list(record.changed_terms),
        added_text_fragments=list(record.added_text_fragments),
        removed_text_fragments=list(record.removed_text_fragments),
        semantic_change_flags=list(record.semantic_change_flags),
        metadata=_metadata(record.metadata_json),
    )


def _replay_run_to_record(run: ReplayRun) -> ReplayRunRecord:
    return ReplayRunRecord(
        run_id=run.run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        policy_name=run.policy_name,
        policy_version=run.policy_version,
        start_time=run.start_time,
        end_time=run.end_time,
        interval_seconds=run.interval_seconds,
        market_ids=list(run.market_ids),
        max_steps=run.max_steps,
        config_json=_metadata(run.config),
        metadata_json=_metadata(run.metadata),
    )


def _replay_run_from_record(record: ReplayRunRecord) -> ReplayRun:
    return ReplayRun(
        run_id=record.run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=ReplayRunStatus(record.status),
        policy_name=record.policy_name,
        policy_version=record.policy_version,
        start_time=record.start_time,
        end_time=record.end_time,
        interval_seconds=record.interval_seconds,
        market_ids=list(record.market_ids),
        max_steps=record.max_steps,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
    )


def _replay_step_to_record(step: ReplayStep) -> ReplayStepRecord:
    return ReplayStepRecord(
        step_id=step.step_id,
        run_id=step.run_id,
        market_id=step.market_id,
        asof_timestamp=step.asof_timestamp,
        market_status=step.market_status,
        rule_snapshot_id=step.rule_snapshot_id,
        rule_snapshot_hash=step.rule_snapshot_hash,
        orderbook_snapshot_id=step.orderbook_snapshot_id,
        resolution_predicate_id=step.resolution_predicate_id,
        ambiguity_assessment_id=step.ambiguity_assessment_id,
        trust_verdict_id=step.trust_verdict_id,
        action=step.action,
        allowed_size_multiplier=step.allowed_size_multiplier,
        price_integrity_score=step.price_integrity_score,
        resolution_risk_score=step.resolution_risk_score,
        liquidity_risk_score=step.liquidity_risk_score,
        cross_venue_consistency_score=step.cross_venue_consistency_score,
        information_freshness_score=step.information_freshness_score,
        manipulation_risk_score=step.manipulation_risk_score,
        reason_codes=list(step.reason_codes),
        input_hash=step.input_hash,
        output_hash=step.output_hash,
        error_code=step.error_code,
        error_message=step.error_message,
        metadata_json=_metadata(step.metadata),
    )


def _replay_step_from_record(record: ReplayStepRecord) -> ReplayStep:
    return ReplayStep(
        step_id=record.step_id,
        run_id=record.run_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        market_status=record.market_status,
        rule_snapshot_id=record.rule_snapshot_id,
        rule_snapshot_hash=record.rule_snapshot_hash,
        orderbook_snapshot_id=record.orderbook_snapshot_id,
        resolution_predicate_id=record.resolution_predicate_id,
        ambiguity_assessment_id=record.ambiguity_assessment_id,
        trust_verdict_id=record.trust_verdict_id,
        action=record.action,
        allowed_size_multiplier=record.allowed_size_multiplier,
        price_integrity_score=record.price_integrity_score,
        resolution_risk_score=record.resolution_risk_score,
        liquidity_risk_score=record.liquidity_risk_score,
        cross_venue_consistency_score=record.cross_venue_consistency_score,
        information_freshness_score=record.information_freshness_score,
        manipulation_risk_score=record.manipulation_risk_score,
        reason_codes=list(record.reason_codes),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        error_code=record.error_code,
        error_message=record.error_message,
        metadata=_metadata(record.metadata_json),
    )


def _replay_summary_to_record(summary: ReplayRunSummary) -> ReplayRunSummaryRecord:
    return ReplayRunSummaryRecord(
        summary_id=summary.summary_id,
        run_id=summary.run_id,
        created_at=summary.created_at,
        total_steps=summary.total_steps,
        errored_steps=summary.errored_steps,
        action_counts=dict(summary.action_counts),
        average_scores={key: str(value) for key, value in summary.average_scores.items()},
        no_trade_rate=summary.no_trade_rate,
        manual_review_rate=summary.manual_review_rate,
        passive_only_rate=summary.passive_only_rate,
        allow_rate=summary.allow_rate,
        allowed_exposure_units=summary.allowed_exposure_units,
        blocked_exposure_units=summary.blocked_exposure_units,
        markets_replayed=summary.markets_replayed,
        metadata_json=_metadata(summary.metadata),
    )


def _replay_summary_from_record(record: ReplayRunSummaryRecord) -> ReplayRunSummary:
    return ReplayRunSummary(
        summary_id=record.summary_id,
        run_id=record.run_id,
        created_at=record.created_at,
        total_steps=record.total_steps,
        errored_steps=record.errored_steps,
        action_counts=dict(record.action_counts),
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        no_trade_rate=record.no_trade_rate,
        manual_review_rate=record.manual_review_rate,
        passive_only_rate=record.passive_only_rate,
        allow_rate=record.allow_rate,
        allowed_exposure_units=record.allowed_exposure_units,
        blocked_exposure_units=record.blocked_exposure_units,
        markets_replayed=record.markets_replayed,
        metadata=_metadata(record.metadata_json),
    )


def _raw_venue_payload_to_record(payload: RawVenuePayload) -> RawVenuePayloadRecord:
    return RawVenuePayloadRecord(
        payload_id=payload.payload_id,
        venue_id=payload.venue_id,
        venue_name=payload.venue_name,
        endpoint_type=payload.endpoint_type.value,
        external_id=payload.external_id,
        captured_at=payload.captured_at,
        source_url=payload.source_url,
        request_params=_metadata(payload.request_params),
        response_payload=_metadata(payload.response_payload),
        response_hash=payload.response_hash,
        schema_version=payload.schema_version,
        metadata_json=_metadata(payload.metadata),
    )


def _raw_venue_payload_from_record(record: RawVenuePayloadRecord) -> RawVenuePayload:
    return RawVenuePayload(
        payload_id=record.payload_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        endpoint_type=VenueEndpointType(record.endpoint_type),
        external_id=record.external_id,
        captured_at=record.captured_at,
        source_url=record.source_url,
        request_params=_metadata(record.request_params),
        response_payload=_metadata(record.response_payload),
        response_hash=record.response_hash,
        schema_version=record.schema_version,
        metadata=_metadata(record.metadata_json),
    )


def _venue_market_mapping_to_record(
    mapping: VenueMarketMapping,
) -> VenueMarketMappingRecord:
    return VenueMarketMappingRecord(
        mapping_id=mapping.mapping_id,
        venue_id=mapping.venue_id,
        venue_name=mapping.venue_name,
        external_event_id=mapping.external_event_id,
        external_market_id=mapping.external_market_id,
        external_symbol=mapping.external_symbol,
        canonical_event_id=mapping.canonical_event_id,
        canonical_market_id=mapping.canonical_market_id,
        external_url=mapping.external_url,
        first_seen_at=mapping.first_seen_at,
        last_seen_at=mapping.last_seen_at,
        status=mapping.status.value,
        metadata_json=_metadata(mapping.metadata),
    )


def _venue_market_mapping_from_record(
    record: VenueMarketMappingRecord,
) -> VenueMarketMapping:
    return VenueMarketMapping(
        mapping_id=record.mapping_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        external_event_id=record.external_event_id,
        external_market_id=record.external_market_id,
        external_symbol=record.external_symbol,
        canonical_event_id=record.canonical_event_id,
        canonical_market_id=record.canonical_market_id,
        external_url=record.external_url,
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
        status=VenueMappingStatus(record.status),
        metadata=_metadata(record.metadata_json),
    )


def _venue_outcome_token_mapping_to_record(
    mapping: VenueOutcomeTokenMapping,
) -> VenueOutcomeTokenMappingRecord:
    return VenueOutcomeTokenMappingRecord(
        mapping_id=mapping.mapping_id,
        venue_id=mapping.venue_id,
        venue_name=mapping.venue_name,
        canonical_market_id=mapping.canonical_market_id,
        canonical_outcome_id=mapping.canonical_outcome_id,
        outcome_label=mapping.outcome_label,
        external_market_id=mapping.external_market_id,
        condition_id=mapping.condition_id,
        question_id=mapping.question_id,
        gamma_market_id=mapping.gamma_market_id,
        gamma_event_id=mapping.gamma_event_id,
        market_address=mapping.market_address,
        token_id=mapping.token_id,
        asset_id=mapping.asset_id,
        token_side=mapping.token_side.value,
        enable_orderbook=mapping.enable_orderbook,
        first_seen_at=mapping.first_seen_at,
        last_seen_at=mapping.last_seen_at,
        status=mapping.status.value,
        metadata_json=_metadata(mapping.metadata),
    )


def _venue_outcome_token_mapping_from_record(
    record: VenueOutcomeTokenMappingRecord,
) -> VenueOutcomeTokenMapping:
    return VenueOutcomeTokenMapping(
        mapping_id=record.mapping_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        canonical_market_id=record.canonical_market_id,
        canonical_outcome_id=record.canonical_outcome_id,
        outcome_label=record.outcome_label,
        external_market_id=record.external_market_id,
        condition_id=record.condition_id,
        question_id=record.question_id,
        gamma_market_id=record.gamma_market_id,
        gamma_event_id=record.gamma_event_id,
        market_address=record.market_address,
        token_id=record.token_id,
        asset_id=record.asset_id,
        token_side=VenueOutcomeTokenSide(record.token_side),
        enable_orderbook=record.enable_orderbook,
        first_seen_at=record.first_seen_at,
        last_seen_at=record.last_seen_at,
        status=VenueOutcomeTokenStatus(record.status),
        metadata=_metadata(record.metadata_json),
    )


def _ingestion_run_to_record(run: IngestionRun) -> IngestionRunRecord:
    return IngestionRunRecord(
        ingestion_run_id=run.ingestion_run_id,
        venue_id=run.venue_id,
        venue_name=run.venue_name,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        mode=run.mode.value,
        source=run.source.value,
        endpoint_types=list(run.endpoint_types),
        markets_seen=run.markets_seen,
        markets_created=run.markets_created,
        markets_updated=run.markets_updated,
        rule_snapshots_created=run.rule_snapshots_created,
        orderbook_snapshots_created=run.orderbook_snapshots_created,
        price_snapshots_created=run.price_snapshots_created,
        liquidity_snapshots_created=run.liquidity_snapshots_created,
        quality_reports_created=run.quality_reports_created,
        payloads_archived=run.payloads_archived,
        errors_count=run.errors_count,
        metadata_json=_metadata(run.metadata),
    )


def _ingestion_run_from_record(record: IngestionRunRecord) -> IngestionRun:
    return IngestionRun(
        ingestion_run_id=record.ingestion_run_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=IngestionRunStatus(record.status),
        mode=IngestionMode(record.mode),
        source=IngestionSource(record.source),
        endpoint_types=list(record.endpoint_types),
        markets_seen=record.markets_seen,
        markets_created=record.markets_created,
        markets_updated=record.markets_updated,
        rule_snapshots_created=record.rule_snapshots_created,
        orderbook_snapshots_created=record.orderbook_snapshots_created,
        price_snapshots_created=record.price_snapshots_created,
        liquidity_snapshots_created=record.liquidity_snapshots_created,
        quality_reports_created=record.quality_reports_created,
        payloads_archived=record.payloads_archived,
        errors_count=record.errors_count,
        metadata=_metadata(record.metadata_json),
    )


def _ingestion_error_to_record(error: IngestionError) -> IngestionErrorRecord:
    return IngestionErrorRecord(
        error_id=error.error_id,
        ingestion_run_id=error.ingestion_run_id,
        venue_id=error.venue_id,
        external_id=error.external_id,
        endpoint_type=error.endpoint_type,
        occurred_at=error.occurred_at,
        error_code=error.error_code,
        error_message=error.error_message,
        payload_id=error.payload_id,
        metadata_json=_metadata(error.metadata),
    )


def _ingestion_error_from_record(record: IngestionErrorRecord) -> IngestionError:
    return IngestionError(
        error_id=record.error_id,
        ingestion_run_id=record.ingestion_run_id,
        venue_id=record.venue_id,
        external_id=record.external_id,
        endpoint_type=record.endpoint_type,
        occurred_at=record.occurred_at,
        error_code=record.error_code,
        error_message=record.error_message,
        payload_id=record.payload_id,
        metadata=_metadata(record.metadata_json),
    )


def _market_price_snapshot_to_record(
    snapshot: MarketPriceSnapshot,
) -> MarketPriceSnapshotRecord:
    return MarketPriceSnapshotRecord(
        price_snapshot_id=snapshot.price_snapshot_id,
        market_id=snapshot.market_id,
        outcome_id=snapshot.outcome_id,
        venue_id=snapshot.venue_id,
        venue_name=snapshot.venue_name,
        source=snapshot.source.value,
        observed_at=snapshot.observed_at,
        captured_at=snapshot.captured_at,
        available_at=snapshot.available_at,
        price=snapshot.price,
        bid=snapshot.bid,
        ask=snapshot.ask,
        mid=snapshot.mid,
        spread=snapshot.spread,
        last_trade_price=snapshot.last_trade_price,
        volume=snapshot.volume,
        open_interest=snapshot.open_interest,
        source_payload_id=snapshot.source_payload_id,
        orderbook_snapshot_id=snapshot.orderbook_snapshot_id,
        external_market_id=snapshot.external_market_id,
        external_outcome_id=snapshot.external_outcome_id,
        data_hash=snapshot.data_hash,
        metadata_json=_metadata(snapshot.metadata),
    )


def _market_price_snapshot_from_record(
    record: MarketPriceSnapshotRecord,
) -> MarketPriceSnapshot:
    return MarketPriceSnapshot(
        price_snapshot_id=record.price_snapshot_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        source=MarketPriceSource(record.source),
        observed_at=record.observed_at,
        captured_at=record.captured_at,
        available_at=record.available_at,
        price=record.price,
        bid=record.bid,
        ask=record.ask,
        mid=record.mid,
        spread=record.spread,
        last_trade_price=record.last_trade_price,
        volume=record.volume,
        open_interest=record.open_interest,
        source_payload_id=record.source_payload_id,
        orderbook_snapshot_id=record.orderbook_snapshot_id,
        external_market_id=record.external_market_id,
        external_outcome_id=record.external_outcome_id,
        data_hash=record.data_hash,
        metadata=_metadata(record.metadata_json),
    )


def _market_liquidity_snapshot_to_record(
    snapshot: MarketLiquiditySnapshot,
) -> MarketLiquiditySnapshotRecord:
    return MarketLiquiditySnapshotRecord(
        liquidity_snapshot_id=snapshot.liquidity_snapshot_id,
        market_id=snapshot.market_id,
        venue_id=snapshot.venue_id,
        venue_name=snapshot.venue_name,
        observed_at=snapshot.observed_at,
        captured_at=snapshot.captured_at,
        available_at=snapshot.available_at,
        best_bid=snapshot.best_bid,
        best_ask=snapshot.best_ask,
        mid_price=snapshot.mid_price,
        spread=snapshot.spread,
        spread_bps=snapshot.spread_bps,
        bid_depth=snapshot.bid_depth,
        ask_depth=snapshot.ask_depth,
        total_bid_depth=snapshot.total_bid_depth,
        total_ask_depth=snapshot.total_ask_depth,
        book_imbalance=snapshot.book_imbalance,
        is_empty_book=snapshot.is_empty_book,
        is_crossed_book=snapshot.is_crossed_book,
        source_payload_id=snapshot.source_payload_id,
        orderbook_snapshot_id=snapshot.orderbook_snapshot_id,
        data_hash=snapshot.data_hash,
        metadata_json=_metadata(snapshot.metadata),
    )


def _market_liquidity_snapshot_from_record(
    record: MarketLiquiditySnapshotRecord,
) -> MarketLiquiditySnapshot:
    return MarketLiquiditySnapshot(
        liquidity_snapshot_id=record.liquidity_snapshot_id,
        market_id=record.market_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        observed_at=record.observed_at,
        captured_at=record.captured_at,
        available_at=record.available_at,
        best_bid=record.best_bid,
        best_ask=record.best_ask,
        mid_price=record.mid_price,
        spread=record.spread,
        spread_bps=record.spread_bps,
        bid_depth=record.bid_depth,
        ask_depth=record.ask_depth,
        total_bid_depth=record.total_bid_depth,
        total_ask_depth=record.total_ask_depth,
        book_imbalance=record.book_imbalance,
        is_empty_book=record.is_empty_book,
        is_crossed_book=record.is_crossed_book,
        source_payload_id=record.source_payload_id,
        orderbook_snapshot_id=record.orderbook_snapshot_id,
        data_hash=record.data_hash,
        metadata=_metadata(record.metadata_json),
    )


def _market_data_quality_report_to_record(
    report: MarketDataQualityReport,
) -> MarketDataQualityReportRecord:
    return MarketDataQualityReportRecord(
        quality_report_id=report.quality_report_id,
        market_id=report.market_id,
        asof_timestamp=report.asof_timestamp,
        created_at=report.created_at,
        latest_price_snapshot_id=report.latest_price_snapshot_id,
        latest_liquidity_snapshot_id=report.latest_liquidity_snapshot_id,
        latest_orderbook_snapshot_id=report.latest_orderbook_snapshot_id,
        latest_rule_snapshot_id=report.latest_rule_snapshot_id,
        freshness_seconds=report.freshness_seconds,
        quality_score=report.quality_score,
        severity=report.severity.value,
        has_recent_price=report.has_recent_price,
        has_recent_orderbook=report.has_recent_orderbook,
        has_rule_snapshot=report.has_rule_snapshot,
        has_venue_mapping=report.has_venue_mapping,
        stale_market_data=report.stale_market_data,
        crossed_book=report.crossed_book,
        empty_book=report.empty_book,
        wide_spread=report.wide_spread,
        out_of_bounds_price=report.out_of_bounds_price,
        missing_bid_or_ask=report.missing_bid_or_ask,
        reason_codes=list(report.reason_codes),
        metadata_json=_metadata(report.metadata),
    )


def _market_data_quality_report_from_record(
    record: MarketDataQualityReportRecord,
) -> MarketDataQualityReport:
    return MarketDataQualityReport(
        quality_report_id=record.quality_report_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        created_at=record.created_at,
        latest_price_snapshot_id=record.latest_price_snapshot_id,
        latest_liquidity_snapshot_id=record.latest_liquidity_snapshot_id,
        latest_orderbook_snapshot_id=record.latest_orderbook_snapshot_id,
        latest_rule_snapshot_id=record.latest_rule_snapshot_id,
        freshness_seconds=record.freshness_seconds,
        quality_score=record.quality_score,
        severity=MarketDataQualitySeverity(record.severity),
        has_recent_price=record.has_recent_price,
        has_recent_orderbook=record.has_recent_orderbook,
        has_rule_snapshot=record.has_rule_snapshot,
        has_venue_mapping=record.has_venue_mapping,
        stale_market_data=record.stale_market_data,
        crossed_book=record.crossed_book,
        empty_book=record.empty_book,
        wide_spread=record.wide_spread,
        out_of_bounds_price=record.out_of_bounds_price,
        missing_bid_or_ask=record.missing_bid_or_ask,
        reason_codes=list(record.reason_codes),
        metadata=_metadata(record.metadata_json),
    )


def _ingestion_cursor_to_record(cursor: IngestionCursor) -> IngestionCursorRecord:
    return IngestionCursorRecord(
        cursor_id=cursor.cursor_id,
        venue_id=cursor.venue_id,
        venue_name=cursor.venue_name,
        endpoint_type=cursor.endpoint_type,
        external_market_id=cursor.external_market_id,
        canonical_market_id=cursor.canonical_market_id,
        cursor_value=cursor.cursor_value,
        last_observed_at=cursor.last_observed_at,
        last_captured_at=cursor.last_captured_at,
        last_available_at=cursor.last_available_at,
        last_success_at=cursor.last_success_at,
        status=cursor.status.value,
        metadata_json=_metadata(cursor.metadata),
    )


def _ingestion_cursor_from_record(record: IngestionCursorRecord) -> IngestionCursor:
    return IngestionCursor(
        cursor_id=record.cursor_id,
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        endpoint_type=record.endpoint_type,
        external_market_id=record.external_market_id,
        canonical_market_id=record.canonical_market_id,
        cursor_value=record.cursor_value,
        last_observed_at=record.last_observed_at,
        last_captured_at=record.last_captured_at,
        last_available_at=record.last_available_at,
        last_success_at=record.last_success_at,
        status=IngestionCursorStatus(record.status),
        metadata=_metadata(record.metadata_json),
    )


def _market_feature_snapshot_to_record(
    snapshot: MarketFeatureSnapshot,
) -> MarketFeatureSnapshotRecord:
    return MarketFeatureSnapshotRecord(
        feature_snapshot_id=snapshot.feature_snapshot_id,
        market_id=snapshot.market_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        latest_price_snapshot_id=snapshot.latest_price_snapshot_id,
        previous_price_snapshot_id=snapshot.previous_price_snapshot_id,
        latest_liquidity_snapshot_id=snapshot.latest_liquidity_snapshot_id,
        previous_liquidity_snapshot_id=snapshot.previous_liquidity_snapshot_id,
        latest_quality_report_id=snapshot.latest_quality_report_id,
        latest_rule_snapshot_id=snapshot.latest_rule_snapshot_id,
        latest_rule_snapshot_hash=snapshot.latest_rule_snapshot_hash,
        latest_rule_diff_id=snapshot.latest_rule_diff_id,
        price=snapshot.price,
        bid=snapshot.bid,
        ask=snapshot.ask,
        mid=snapshot.mid,
        spread=snapshot.spread,
        spread_bps=snapshot.spread_bps,
        total_bid_depth=snapshot.total_bid_depth,
        total_ask_depth=snapshot.total_ask_depth,
        total_depth=snapshot.total_depth,
        book_imbalance=snapshot.book_imbalance,
        is_empty_book=snapshot.is_empty_book,
        is_crossed_book=snapshot.is_crossed_book,
        has_missing_bid_or_ask=snapshot.has_missing_bid_or_ask,
        market_data_quality_score=snapshot.market_data_quality_score,
        market_data_quality_reason_codes=list(snapshot.market_data_quality_reason_codes),
        freshness_seconds=snapshot.freshness_seconds,
        price_change_abs=snapshot.price_change_abs,
        price_change_pct=snapshot.price_change_pct,
        mid_change_abs=snapshot.mid_change_abs,
        spread_change_abs=snapshot.spread_change_abs,
        depth_change_pct=snapshot.depth_change_pct,
        rule_changed_recently=snapshot.rule_changed_recently,
        rule_change_age_seconds=snapshot.rule_change_age_seconds,
        input_hash=snapshot.input_hash,
        metadata_json=_metadata(snapshot.metadata),
    )


def _market_feature_snapshot_from_record(
    record: MarketFeatureSnapshotRecord,
) -> MarketFeatureSnapshot:
    return MarketFeatureSnapshot(
        feature_snapshot_id=record.feature_snapshot_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        latest_price_snapshot_id=record.latest_price_snapshot_id,
        previous_price_snapshot_id=record.previous_price_snapshot_id,
        latest_liquidity_snapshot_id=record.latest_liquidity_snapshot_id,
        previous_liquidity_snapshot_id=record.previous_liquidity_snapshot_id,
        latest_quality_report_id=record.latest_quality_report_id,
        latest_rule_snapshot_id=record.latest_rule_snapshot_id,
        latest_rule_snapshot_hash=record.latest_rule_snapshot_hash,
        latest_rule_diff_id=record.latest_rule_diff_id,
        price=record.price,
        bid=record.bid,
        ask=record.ask,
        mid=record.mid,
        spread=record.spread,
        spread_bps=record.spread_bps,
        total_bid_depth=record.total_bid_depth,
        total_ask_depth=record.total_ask_depth,
        total_depth=record.total_depth,
        book_imbalance=record.book_imbalance,
        is_empty_book=record.is_empty_book,
        is_crossed_book=record.is_crossed_book,
        has_missing_bid_or_ask=record.has_missing_bid_or_ask,
        market_data_quality_score=record.market_data_quality_score,
        market_data_quality_reason_codes=list(record.market_data_quality_reason_codes),
        freshness_seconds=record.freshness_seconds,
        price_change_abs=record.price_change_abs,
        price_change_pct=record.price_change_pct,
        mid_change_abs=record.mid_change_abs,
        spread_change_abs=record.spread_change_abs,
        depth_change_pct=record.depth_change_pct,
        rule_changed_recently=record.rule_changed_recently,
        rule_change_age_seconds=record.rule_change_age_seconds,
        input_hash=record.input_hash,
        metadata=_metadata(record.metadata_json),
    )


def _integrity_signal_to_record(signal: IntegritySignal) -> IntegritySignalRecord:
    return IntegritySignalRecord(
        integrity_signal_id=signal.integrity_signal_id,
        market_id=signal.market_id,
        asof_timestamp=signal.asof_timestamp,
        generated_at=signal.generated_at,
        available_at=signal.available_at,
        feature_snapshot_id=signal.feature_snapshot_id,
        signal_name=signal.signal_name,
        signal_version=signal.signal_version,
        category=signal.category.value,
        severity=signal.severity.value,
        score=signal.score,
        action_hint=signal.action_hint.value,
        reason_code=signal.reason_code,
        message=signal.message,
        evidence=signal.model_dump(mode="json")["evidence"],
        input_hash=signal.input_hash,
        output_hash=signal.output_hash,
        metadata_json=_metadata(signal.metadata),
    )


def _integrity_signal_from_record(record: IntegritySignalRecord) -> IntegritySignal:
    return IntegritySignal(
        integrity_signal_id=record.integrity_signal_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        feature_snapshot_id=record.feature_snapshot_id,
        signal_name=record.signal_name,
        signal_version=record.signal_version,
        category=SignalCategory(record.category),
        severity=SignalSeverity(record.severity),
        score=record.score,
        action_hint=IntegrityActionHint(record.action_hint),
        reason_code=record.reason_code,
        message=record.message,
        evidence=_metadata(record.evidence),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _integrity_assessment_to_record(
    assessment: IntegrityAssessment,
) -> IntegrityAssessmentRecord:
    return IntegrityAssessmentRecord(
        integrity_assessment_id=assessment.integrity_assessment_id,
        market_id=assessment.market_id,
        asof_timestamp=assessment.asof_timestamp,
        generated_at=assessment.generated_at,
        available_at=assessment.available_at,
        feature_snapshot_id=assessment.feature_snapshot_id,
        signal_ids=list(assessment.signal_ids),
        overall_risk_score=assessment.overall_risk_score,
        price_anomaly_score=assessment.price_anomaly_score,
        liquidity_anomaly_score=assessment.liquidity_anomaly_score,
        freshness_risk_score=assessment.freshness_risk_score,
        orderbook_structure_score=assessment.orderbook_structure_score,
        rule_change_risk_score=assessment.rule_change_risk_score,
        rule_price_coupling_score=assessment.rule_price_coupling_score,
        data_quality_risk_score=assessment.data_quality_risk_score,
        manipulation_proxy_score=assessment.manipulation_proxy_score,
        severity=assessment.severity.value,
        action_hint=assessment.action_hint.value,
        reason_codes=list(assessment.reason_codes),
        input_hash=assessment.input_hash,
        output_hash=assessment.output_hash,
        metadata_json=_metadata(assessment.metadata),
    )


def _integrity_assessment_from_record(
    record: IntegrityAssessmentRecord,
) -> IntegrityAssessment:
    return IntegrityAssessment(
        integrity_assessment_id=record.integrity_assessment_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        feature_snapshot_id=record.feature_snapshot_id,
        signal_ids=list(record.signal_ids),
        overall_risk_score=record.overall_risk_score,
        price_anomaly_score=record.price_anomaly_score,
        liquidity_anomaly_score=record.liquidity_anomaly_score,
        freshness_risk_score=record.freshness_risk_score,
        orderbook_structure_score=record.orderbook_structure_score,
        rule_change_risk_score=record.rule_change_risk_score,
        rule_price_coupling_score=record.rule_price_coupling_score,
        data_quality_risk_score=record.data_quality_risk_score,
        manipulation_proxy_score=record.manipulation_proxy_score,
        severity=SignalSeverity(record.severity),
        action_hint=IntegrityActionHint(record.action_hint),
        reason_codes=list(record.reason_codes),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _integrity_run_to_record(run: IntegrityRun) -> IntegrityRunRecord:
    return IntegrityRunRecord(
        integrity_run_id=run.integrity_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        start_time=run.start_time,
        end_time=run.end_time,
        interval_seconds=run.interval_seconds,
        asof_timestamp=run.asof_timestamp,
        market_ids=list(run.market_ids),
        max_steps=run.max_steps,
        config_json=_metadata(run.config),
        metadata_json=_metadata(run.metadata),
        assessments_created=run.assessments_created,
        signals_created=run.signals_created,
        errors_count=run.errors_count,
    )


def _integrity_run_from_record(record: IntegrityRunRecord) -> IntegrityRun:
    return IntegrityRun(
        integrity_run_id=record.integrity_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=IntegrityRunStatus(record.status),
        start_time=record.start_time,
        end_time=record.end_time,
        interval_seconds=record.interval_seconds,
        asof_timestamp=record.asof_timestamp,
        market_ids=list(record.market_ids),
        max_steps=record.max_steps,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        assessments_created=record.assessments_created,
        signals_created=record.signals_created,
        errors_count=record.errors_count,
    )


def _integrity_run_summary_to_record(
    summary: IntegrityRunSummary,
) -> IntegrityRunSummaryRecord:
    return IntegrityRunSummaryRecord(
        summary_id=summary.summary_id,
        integrity_run_id=summary.integrity_run_id,
        created_at=summary.created_at,
        total_assessments=summary.total_assessments,
        total_signals=summary.total_signals,
        severity_counts=dict(summary.severity_counts),
        category_counts=dict(summary.category_counts),
        action_hint_counts=dict(summary.action_hint_counts),
        average_scores={key: str(value) for key, value in summary.average_scores.items()},
        no_trade_rate=summary.no_trade_rate,
        manual_review_rate=summary.manual_review_rate,
        passive_only_rate=summary.passive_only_rate,
        allow_smaller_size_rate=summary.allow_smaller_size_rate,
        markets_scanned=summary.markets_scanned,
        metadata_json=_metadata(summary.metadata),
    )


def _integrity_run_summary_from_record(
    record: IntegrityRunSummaryRecord,
) -> IntegrityRunSummary:
    return IntegrityRunSummary(
        summary_id=record.summary_id,
        integrity_run_id=record.integrity_run_id,
        created_at=record.created_at,
        total_assessments=record.total_assessments,
        total_signals=record.total_signals,
        severity_counts=dict(record.severity_counts),
        category_counts=dict(record.category_counts),
        action_hint_counts=dict(record.action_hint_counts),
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        no_trade_rate=record.no_trade_rate,
        manual_review_rate=record.manual_review_rate,
        passive_only_rate=record.passive_only_rate,
        allow_smaller_size_rate=record.allow_smaller_size_rate,
        markets_scanned=record.markets_scanned,
        metadata=_metadata(record.metadata_json),
    )


def _equivalence_candidate_to_record(
    candidate: EquivalenceCandidate,
) -> EquivalenceCandidateRecord:
    return EquivalenceCandidateRecord(
        candidate_id=candidate.candidate_id,
        left_market_id=candidate.left_market_id,
        right_market_id=candidate.right_market_id,
        asof_timestamp=candidate.asof_timestamp,
        generated_at=candidate.generated_at,
        candidate_score=candidate.candidate_score,
        candidate_reasons=list(candidate.candidate_reasons),
        left_venue_id=candidate.left_venue_id,
        right_venue_id=candidate.right_venue_id,
        title_similarity_score=candidate.title_similarity_score,
        category_match=candidate.category_match,
        shared_tokens=list(candidate.shared_tokens),
        input_hash=candidate.input_hash,
        metadata_json=_metadata(candidate.metadata),
    )


def _equivalence_candidate_from_record(
    record: EquivalenceCandidateRecord,
) -> EquivalenceCandidate:
    return EquivalenceCandidate(
        candidate_id=record.candidate_id,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        candidate_score=record.candidate_score,
        candidate_reasons=list(record.candidate_reasons),
        left_venue_id=record.left_venue_id,
        right_venue_id=record.right_venue_id,
        title_similarity_score=record.title_similarity_score,
        category_match=record.category_match,
        shared_tokens=list(record.shared_tokens),
        input_hash=record.input_hash,
        metadata=_metadata(record.metadata_json),
    )


def _market_equivalence_assessment_to_record(
    assessment: MarketEquivalenceAssessment,
) -> MarketEquivalenceAssessmentRecord:
    return MarketEquivalenceAssessmentRecord(
        equivalence_assessment_id=assessment.equivalence_assessment_id,
        left_market_id=assessment.left_market_id,
        right_market_id=assessment.right_market_id,
        asof_timestamp=assessment.asof_timestamp,
        generated_at=assessment.generated_at,
        available_at=assessment.available_at,
        left_rule_snapshot_id=assessment.left_rule_snapshot_id,
        right_rule_snapshot_id=assessment.right_rule_snapshot_id,
        left_rule_snapshot_hash=assessment.left_rule_snapshot_hash,
        right_rule_snapshot_hash=assessment.right_rule_snapshot_hash,
        left_resolution_predicate_id=assessment.left_resolution_predicate_id,
        right_resolution_predicate_id=assessment.right_resolution_predicate_id,
        left_ambiguity_assessment_id=assessment.left_ambiguity_assessment_id,
        right_ambiguity_assessment_id=assessment.right_ambiguity_assessment_id,
        left_venue_id=assessment.left_venue_id,
        right_venue_id=assessment.right_venue_id,
        status=assessment.status.value,
        comparison_permission=assessment.comparison_permission.value,
        overall_score=assessment.overall_score,
        confidence_score=assessment.confidence_score,
        title_similarity_score=assessment.title_similarity_score,
        event_identity_score=assessment.event_identity_score,
        outcome_structure_score=assessment.outcome_structure_score,
        outcome_mapping_score=assessment.outcome_mapping_score,
        predicate_similarity_score=assessment.predicate_similarity_score,
        resolution_source_score=assessment.resolution_source_score,
        settlement_authority_score=assessment.settlement_authority_score,
        temporal_alignment_score=assessment.temporal_alignment_score,
        threshold_alignment_score=assessment.threshold_alignment_score,
        timezone_alignment_score=assessment.timezone_alignment_score,
        ambiguity_compatibility_score=assessment.ambiguity_compatibility_score,
        venue_rule_compatibility_score=assessment.venue_rule_compatibility_score,
        same_venue=assessment.same_venue,
        same_event_likely=assessment.same_event_likely,
        same_outcome_universe_likely=assessment.same_outcome_universe_likely,
        inverse_outcome_likely=assessment.inverse_outcome_likely,
        resolution_source_mismatch=assessment.resolution_source_mismatch,
        settlement_authority_mismatch=assessment.settlement_authority_mismatch,
        deadline_mismatch=assessment.deadline_mismatch,
        timezone_mismatch=assessment.timezone_mismatch,
        threshold_mismatch=assessment.threshold_mismatch,
        high_ambiguity=assessment.high_ambiguity,
        insufficient_rule_data=assessment.insufficient_rule_data,
        reason_codes=list(assessment.reason_codes),
        evidence=assessment.model_dump(mode="json")["evidence"],
        input_hash=assessment.input_hash,
        output_hash=assessment.output_hash,
        metadata_json=_metadata(assessment.metadata),
    )


def _market_equivalence_assessment_from_record(
    record: MarketEquivalenceAssessmentRecord,
) -> MarketEquivalenceAssessment:
    return MarketEquivalenceAssessment(
        equivalence_assessment_id=record.equivalence_assessment_id,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        left_rule_snapshot_id=record.left_rule_snapshot_id,
        right_rule_snapshot_id=record.right_rule_snapshot_id,
        left_rule_snapshot_hash=record.left_rule_snapshot_hash,
        right_rule_snapshot_hash=record.right_rule_snapshot_hash,
        left_resolution_predicate_id=record.left_resolution_predicate_id,
        right_resolution_predicate_id=record.right_resolution_predicate_id,
        left_ambiguity_assessment_id=record.left_ambiguity_assessment_id,
        right_ambiguity_assessment_id=record.right_ambiguity_assessment_id,
        left_venue_id=record.left_venue_id,
        right_venue_id=record.right_venue_id,
        status=EquivalenceStatus(record.status),
        comparison_permission=ComparisonPermission(record.comparison_permission),
        overall_score=record.overall_score,
        confidence_score=record.confidence_score,
        title_similarity_score=record.title_similarity_score,
        event_identity_score=record.event_identity_score,
        outcome_structure_score=record.outcome_structure_score,
        outcome_mapping_score=record.outcome_mapping_score,
        predicate_similarity_score=record.predicate_similarity_score,
        resolution_source_score=record.resolution_source_score,
        settlement_authority_score=record.settlement_authority_score,
        temporal_alignment_score=record.temporal_alignment_score,
        threshold_alignment_score=record.threshold_alignment_score,
        timezone_alignment_score=record.timezone_alignment_score,
        ambiguity_compatibility_score=record.ambiguity_compatibility_score,
        venue_rule_compatibility_score=record.venue_rule_compatibility_score,
        same_venue=record.same_venue,
        same_event_likely=record.same_event_likely,
        same_outcome_universe_likely=record.same_outcome_universe_likely,
        inverse_outcome_likely=record.inverse_outcome_likely,
        resolution_source_mismatch=record.resolution_source_mismatch,
        settlement_authority_mismatch=record.settlement_authority_mismatch,
        deadline_mismatch=record.deadline_mismatch,
        timezone_mismatch=record.timezone_mismatch,
        threshold_mismatch=record.threshold_mismatch,
        high_ambiguity=record.high_ambiguity,
        insufficient_rule_data=record.insufficient_rule_data,
        reason_codes=list(record.reason_codes),
        evidence=_metadata(record.evidence),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _outcome_equivalence_mapping_to_record(
    mapping: OutcomeEquivalenceMapping,
) -> OutcomeEquivalenceMappingRecord:
    return OutcomeEquivalenceMappingRecord(
        outcome_mapping_id=mapping.outcome_mapping_id,
        equivalence_assessment_id=mapping.equivalence_assessment_id,
        left_market_id=mapping.left_market_id,
        right_market_id=mapping.right_market_id,
        left_outcome_id=mapping.left_outcome_id,
        right_outcome_id=mapping.right_outcome_id,
        left_label=mapping.left_label,
        right_label=mapping.right_label,
        relation=mapping.relation.value,
        score=mapping.score,
        evidence=mapping.model_dump(mode="json")["evidence"],
        metadata_json=_metadata(mapping.metadata),
    )


def _outcome_equivalence_mapping_from_record(
    record: OutcomeEquivalenceMappingRecord,
) -> OutcomeEquivalenceMapping:
    return OutcomeEquivalenceMapping(
        outcome_mapping_id=record.outcome_mapping_id,
        equivalence_assessment_id=record.equivalence_assessment_id,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        left_outcome_id=record.left_outcome_id,
        right_outcome_id=record.right_outcome_id,
        left_label=record.left_label,
        right_label=record.right_label,
        relation=OutcomeRelation(record.relation),
        score=record.score,
        evidence=_metadata(record.evidence),
        metadata=_metadata(record.metadata_json),
    )


def _equivalence_class_to_record(equivalence_class: EquivalenceClass) -> EquivalenceClassRecord:
    return EquivalenceClassRecord(
        equivalence_class_id=equivalence_class.equivalence_class_id,
        asof_timestamp=equivalence_class.asof_timestamp,
        created_at=equivalence_class.created_at,
        status=equivalence_class.status.value,
        representative_title=equivalence_class.representative_title,
        market_ids=list(equivalence_class.market_ids),
        assessment_ids=list(equivalence_class.assessment_ids),
        min_pair_score=equivalence_class.min_pair_score,
        average_pair_score=equivalence_class.average_pair_score,
        confidence_score=equivalence_class.confidence_score,
        comparison_permission=equivalence_class.comparison_permission.value,
        reason_codes=list(equivalence_class.reason_codes),
        metadata_json=_metadata(equivalence_class.metadata),
    )


def _equivalence_class_from_record(record: EquivalenceClassRecord) -> EquivalenceClass:
    return EquivalenceClass(
        equivalence_class_id=record.equivalence_class_id,
        asof_timestamp=record.asof_timestamp,
        created_at=record.created_at,
        status=EquivalenceClassStatus(record.status),
        representative_title=record.representative_title,
        market_ids=list(record.market_ids),
        assessment_ids=list(record.assessment_ids),
        min_pair_score=record.min_pair_score,
        average_pair_score=record.average_pair_score,
        confidence_score=record.confidence_score,
        comparison_permission=ComparisonPermission(record.comparison_permission),
        reason_codes=list(record.reason_codes),
        metadata=_metadata(record.metadata_json),
    )


def _equivalence_run_to_record(run: EquivalenceRun) -> EquivalenceRunRecord:
    return EquivalenceRunRecord(
        equivalence_run_id=run.equivalence_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        asof_timestamp=run.asof_timestamp,
        market_ids=list(run.market_ids),
        venue_names=list(run.venue_names),
        max_pairs=run.max_pairs,
        min_candidate_score=run.min_candidate_score,
        config_json=_metadata(run.config),
        metadata_json=_metadata(run.metadata),
        candidates_created=run.candidates_created,
        assessments_created=run.assessments_created,
        classes_created=run.classes_created,
        errors_count=run.errors_count,
    )


def _equivalence_run_from_record(record: EquivalenceRunRecord) -> EquivalenceRun:
    return EquivalenceRun(
        equivalence_run_id=record.equivalence_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=EquivalenceRunStatus(record.status),
        asof_timestamp=record.asof_timestamp,
        market_ids=list(record.market_ids),
        venue_names=list(record.venue_names),
        max_pairs=record.max_pairs,
        min_candidate_score=record.min_candidate_score,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        candidates_created=record.candidates_created,
        assessments_created=record.assessments_created,
        classes_created=record.classes_created,
        errors_count=record.errors_count,
    )


def _equivalence_run_summary_to_record(
    summary: EquivalenceRunSummary,
) -> EquivalenceRunSummaryRecord:
    return EquivalenceRunSummaryRecord(
        summary_id=summary.summary_id,
        equivalence_run_id=summary.equivalence_run_id,
        created_at=summary.created_at,
        total_candidates=summary.total_candidates,
        total_assessments=summary.total_assessments,
        total_classes=summary.total_classes,
        status_counts=dict(summary.status_counts),
        permission_counts=dict(summary.permission_counts),
        average_scores={key: str(value) for key, value in summary.average_scores.items()},
        comparable_rate=summary.comparable_rate,
        manual_review_rate=summary.manual_review_rate,
        do_not_compare_rate=summary.do_not_compare_rate,
        markets_compared=summary.markets_compared,
        metadata_json=_metadata(summary.metadata),
    )


def _equivalence_run_summary_from_record(
    record: EquivalenceRunSummaryRecord,
) -> EquivalenceRunSummary:
    return EquivalenceRunSummary(
        summary_id=record.summary_id,
        equivalence_run_id=record.equivalence_run_id,
        created_at=record.created_at,
        total_candidates=record.total_candidates,
        total_assessments=record.total_assessments,
        total_classes=record.total_classes,
        status_counts=dict(record.status_counts),
        permission_counts=dict(record.permission_counts),
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        comparable_rate=record.comparable_rate,
        manual_review_rate=record.manual_review_rate,
        do_not_compare_rate=record.do_not_compare_rate,
        markets_compared=record.markets_compared,
        metadata=_metadata(record.metadata_json),
    )


def _divergence_snapshot_to_record(
    snapshot: CrossVenueDivergenceSnapshot,
) -> CrossVenueDivergenceSnapshotRecord:
    return CrossVenueDivergenceSnapshotRecord(
        divergence_snapshot_id=snapshot.divergence_snapshot_id,
        equivalence_assessment_id=snapshot.equivalence_assessment_id,
        outcome_mapping_id=snapshot.outcome_mapping_id,
        left_market_id=snapshot.left_market_id,
        right_market_id=snapshot.right_market_id,
        left_venue_id=snapshot.left_venue_id,
        right_venue_id=snapshot.right_venue_id,
        left_outcome_id=snapshot.left_outcome_id,
        right_outcome_id=snapshot.right_outcome_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        equivalence_status=snapshot.equivalence_status,
        comparison_permission=snapshot.comparison_permission,
        equivalence_score=snapshot.equivalence_score,
        equivalence_confidence_score=snapshot.equivalence_confidence_score,
        outcome_relation=snapshot.outcome_relation,
        left_price_snapshot_id=snapshot.left_price_snapshot_id,
        right_price_snapshot_id=snapshot.right_price_snapshot_id,
        left_liquidity_snapshot_id=snapshot.left_liquidity_snapshot_id,
        right_liquidity_snapshot_id=snapshot.right_liquidity_snapshot_id,
        left_quality_report_id=snapshot.left_quality_report_id,
        right_quality_report_id=snapshot.right_quality_report_id,
        left_integrity_assessment_id=snapshot.left_integrity_assessment_id,
        right_integrity_assessment_id=snapshot.right_integrity_assessment_id,
        left_price=snapshot.left_price,
        right_price_raw=snapshot.right_price_raw,
        right_price_aligned=snapshot.right_price_aligned,
        left_mid=snapshot.left_mid,
        right_mid_raw=snapshot.right_mid_raw,
        right_mid_aligned=snapshot.right_mid_aligned,
        left_bid=snapshot.left_bid,
        left_ask=snapshot.left_ask,
        right_bid_raw=snapshot.right_bid_raw,
        right_ask_raw=snapshot.right_ask_raw,
        right_bid_aligned=snapshot.right_bid_aligned,
        right_ask_aligned=snapshot.right_ask_aligned,
        signed_mid_gap=snapshot.signed_mid_gap,
        absolute_mid_gap=snapshot.absolute_mid_gap,
        signed_price_gap=snapshot.signed_price_gap,
        absolute_price_gap=snapshot.absolute_price_gap,
        gap_bps=snapshot.gap_bps,
        combined_spread=snapshot.combined_spread,
        spread_adjusted_gap=snapshot.spread_adjusted_gap,
        left_spread=snapshot.left_spread,
        right_spread=snapshot.right_spread,
        left_total_depth=snapshot.left_total_depth,
        right_total_depth=snapshot.right_total_depth,
        min_total_depth=snapshot.min_total_depth,
        left_quality_score=snapshot.left_quality_score,
        right_quality_score=snapshot.right_quality_score,
        left_integrity_risk_score=snapshot.left_integrity_risk_score,
        right_integrity_risk_score=snapshot.right_integrity_risk_score,
        stale_side=snapshot.stale_side,
        weaker_side=snapshot.weaker_side,
        comparable=snapshot.comparable,
        comparable_with_haircut=snapshot.comparable_with_haircut,
        manual_review_required=snapshot.manual_review_required,
        do_not_compare=snapshot.do_not_compare,
        missing_price_data=snapshot.missing_price_data,
        missing_liquidity_data=snapshot.missing_liquidity_data,
        stale_data=snapshot.stale_data,
        low_quality_data=snapshot.low_quality_data,
        high_integrity_risk=snapshot.high_integrity_risk,
        wide_spread=snapshot.wide_spread,
        one_sided_or_empty_book=snapshot.one_sided_or_empty_book,
        input_hash=snapshot.input_hash,
        output_hash=snapshot.output_hash,
        metadata_json=_metadata(snapshot.metadata),
    )


def _divergence_snapshot_from_record(
    record: CrossVenueDivergenceSnapshotRecord,
) -> CrossVenueDivergenceSnapshot:
    return CrossVenueDivergenceSnapshot(
        divergence_snapshot_id=record.divergence_snapshot_id,
        equivalence_assessment_id=record.equivalence_assessment_id,
        outcome_mapping_id=record.outcome_mapping_id,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        left_venue_id=record.left_venue_id,
        right_venue_id=record.right_venue_id,
        left_outcome_id=record.left_outcome_id,
        right_outcome_id=record.right_outcome_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        equivalence_status=record.equivalence_status,
        comparison_permission=record.comparison_permission,
        equivalence_score=record.equivalence_score,
        equivalence_confidence_score=record.equivalence_confidence_score,
        outcome_relation=record.outcome_relation,
        left_price_snapshot_id=record.left_price_snapshot_id,
        right_price_snapshot_id=record.right_price_snapshot_id,
        left_liquidity_snapshot_id=record.left_liquidity_snapshot_id,
        right_liquidity_snapshot_id=record.right_liquidity_snapshot_id,
        left_quality_report_id=record.left_quality_report_id,
        right_quality_report_id=record.right_quality_report_id,
        left_integrity_assessment_id=record.left_integrity_assessment_id,
        right_integrity_assessment_id=record.right_integrity_assessment_id,
        left_price=record.left_price,
        right_price_raw=record.right_price_raw,
        right_price_aligned=record.right_price_aligned,
        left_mid=record.left_mid,
        right_mid_raw=record.right_mid_raw,
        right_mid_aligned=record.right_mid_aligned,
        left_bid=record.left_bid,
        left_ask=record.left_ask,
        right_bid_raw=record.right_bid_raw,
        right_ask_raw=record.right_ask_raw,
        right_bid_aligned=record.right_bid_aligned,
        right_ask_aligned=record.right_ask_aligned,
        signed_mid_gap=record.signed_mid_gap,
        absolute_mid_gap=record.absolute_mid_gap,
        signed_price_gap=record.signed_price_gap,
        absolute_price_gap=record.absolute_price_gap,
        gap_bps=record.gap_bps,
        combined_spread=record.combined_spread,
        spread_adjusted_gap=record.spread_adjusted_gap,
        left_spread=record.left_spread,
        right_spread=record.right_spread,
        left_total_depth=record.left_total_depth,
        right_total_depth=record.right_total_depth,
        min_total_depth=record.min_total_depth,
        left_quality_score=record.left_quality_score,
        right_quality_score=record.right_quality_score,
        left_integrity_risk_score=record.left_integrity_risk_score,
        right_integrity_risk_score=record.right_integrity_risk_score,
        stale_side=record.stale_side,
        weaker_side=record.weaker_side,
        comparable=record.comparable,
        comparable_with_haircut=record.comparable_with_haircut,
        manual_review_required=record.manual_review_required,
        do_not_compare=record.do_not_compare,
        missing_price_data=record.missing_price_data,
        missing_liquidity_data=record.missing_liquidity_data,
        stale_data=record.stale_data,
        low_quality_data=record.low_quality_data,
        high_integrity_risk=record.high_integrity_risk,
        wide_spread=record.wide_spread,
        one_sided_or_empty_book=record.one_sided_or_empty_book,
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _divergence_signal_to_record(
    signal: CrossVenueDivergenceSignal,
) -> CrossVenueDivergenceSignalRecord:
    return CrossVenueDivergenceSignalRecord(
        divergence_signal_id=signal.divergence_signal_id,
        divergence_snapshot_id=signal.divergence_snapshot_id,
        equivalence_assessment_id=signal.equivalence_assessment_id,
        left_market_id=signal.left_market_id,
        right_market_id=signal.right_market_id,
        asof_timestamp=signal.asof_timestamp,
        generated_at=signal.generated_at,
        available_at=signal.available_at,
        signal_name=signal.signal_name,
        signal_version=signal.signal_version,
        category=signal.category.value,
        severity=signal.severity.value,
        score=signal.score,
        action_hint=signal.action_hint.value,
        reason_code=signal.reason_code,
        message=signal.message,
        evidence=signal.model_dump(mode="json")["evidence"],
        input_hash=signal.input_hash,
        output_hash=signal.output_hash,
        metadata_json=_metadata(signal.metadata),
    )


def _divergence_signal_from_record(
    record: CrossVenueDivergenceSignalRecord,
) -> CrossVenueDivergenceSignal:
    return CrossVenueDivergenceSignal(
        divergence_signal_id=record.divergence_signal_id,
        divergence_snapshot_id=record.divergence_snapshot_id,
        equivalence_assessment_id=record.equivalence_assessment_id,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        signal_name=record.signal_name,
        signal_version=record.signal_version,
        category=DivergenceSignalCategory(record.category),
        severity=DivergenceSignalSeverity(record.severity),
        score=record.score,
        action_hint=DivergenceActionHint(record.action_hint),
        reason_code=record.reason_code,
        message=record.message,
        evidence=_metadata(record.evidence),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _divergence_assessment_to_record(
    assessment: CrossVenueDivergenceAssessment,
) -> CrossVenueDivergenceAssessmentRecord:
    return CrossVenueDivergenceAssessmentRecord(
        divergence_assessment_id=assessment.divergence_assessment_id,
        divergence_snapshot_id=assessment.divergence_snapshot_id,
        equivalence_assessment_id=assessment.equivalence_assessment_id,
        outcome_mapping_id=assessment.outcome_mapping_id,
        left_market_id=assessment.left_market_id,
        right_market_id=assessment.right_market_id,
        asof_timestamp=assessment.asof_timestamp,
        generated_at=assessment.generated_at,
        available_at=assessment.available_at,
        signal_ids=list(assessment.signal_ids),
        overall_divergence_score=assessment.overall_divergence_score,
        price_divergence_score=assessment.price_divergence_score,
        spread_adjusted_score=assessment.spread_adjusted_score,
        persistence_score=assessment.persistence_score,
        stale_side_score=assessment.stale_side_score,
        low_liquidity_score=assessment.low_liquidity_score,
        low_data_quality_score=assessment.low_data_quality_score,
        integrity_context_score=assessment.integrity_context_score,
        equivalence_context_score=assessment.equivalence_context_score,
        status=assessment.status.value,
        severity=assessment.severity.value,
        action_hint=assessment.action_hint.value,
        reason_codes=list(assessment.reason_codes),
        absolute_mid_gap=assessment.absolute_mid_gap,
        spread_adjusted_gap=assessment.spread_adjusted_gap,
        gap_bps=assessment.gap_bps,
        comparison_permission=assessment.comparison_permission,
        equivalence_score=assessment.equivalence_score,
        equivalence_confidence_score=assessment.equivalence_confidence_score,
        input_hash=assessment.input_hash,
        output_hash=assessment.output_hash,
        metadata_json=_metadata(assessment.metadata),
    )


def _divergence_assessment_from_record(
    record: CrossVenueDivergenceAssessmentRecord,
) -> CrossVenueDivergenceAssessment:
    return CrossVenueDivergenceAssessment(
        divergence_assessment_id=record.divergence_assessment_id,
        divergence_snapshot_id=record.divergence_snapshot_id,
        equivalence_assessment_id=record.equivalence_assessment_id,
        outcome_mapping_id=record.outcome_mapping_id,
        left_market_id=record.left_market_id,
        right_market_id=record.right_market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        signal_ids=list(record.signal_ids),
        overall_divergence_score=record.overall_divergence_score,
        price_divergence_score=record.price_divergence_score,
        spread_adjusted_score=record.spread_adjusted_score,
        persistence_score=record.persistence_score,
        stale_side_score=record.stale_side_score,
        low_liquidity_score=record.low_liquidity_score,
        low_data_quality_score=record.low_data_quality_score,
        integrity_context_score=record.integrity_context_score,
        equivalence_context_score=record.equivalence_context_score,
        status=DivergenceStatus(record.status),
        severity=DivergenceSignalSeverity(record.severity),
        action_hint=DivergenceActionHint(record.action_hint),
        reason_codes=list(record.reason_codes),
        absolute_mid_gap=record.absolute_mid_gap,
        spread_adjusted_gap=record.spread_adjusted_gap,
        gap_bps=record.gap_bps,
        comparison_permission=record.comparison_permission,
        equivalence_score=record.equivalence_score,
        equivalence_confidence_score=record.equivalence_confidence_score,
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _divergence_run_to_record(
    run: CrossVenueDivergenceRun,
) -> CrossVenueDivergenceRunRecord:
    return CrossVenueDivergenceRunRecord(
        divergence_run_id=run.divergence_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        asof_timestamp=run.asof_timestamp,
        equivalence_assessment_ids=list(run.equivalence_assessment_ids),
        market_ids=list(run.market_ids),
        max_pairs=run.max_pairs,
        config_json=_metadata(run.config),
        metadata_json=_metadata(run.metadata),
        snapshots_created=run.snapshots_created,
        signals_created=run.signals_created,
        assessments_created=run.assessments_created,
        errors_count=run.errors_count,
    )


def _divergence_run_from_record(
    record: CrossVenueDivergenceRunRecord,
) -> CrossVenueDivergenceRun:
    return CrossVenueDivergenceRun(
        divergence_run_id=record.divergence_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=DivergenceRunStatus(record.status),
        asof_timestamp=record.asof_timestamp,
        equivalence_assessment_ids=list(record.equivalence_assessment_ids),
        market_ids=list(record.market_ids),
        max_pairs=record.max_pairs,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        snapshots_created=record.snapshots_created,
        signals_created=record.signals_created,
        assessments_created=record.assessments_created,
        errors_count=record.errors_count,
    )


def _divergence_run_summary_to_record(
    summary: CrossVenueDivergenceRunSummary,
) -> CrossVenueDivergenceRunSummaryRecord:
    return CrossVenueDivergenceRunSummaryRecord(
        summary_id=summary.summary_id,
        divergence_run_id=summary.divergence_run_id,
        created_at=summary.created_at,
        total_snapshots=summary.total_snapshots,
        total_signals=summary.total_signals,
        total_assessments=summary.total_assessments,
        status_counts=dict(summary.status_counts),
        severity_counts=dict(summary.severity_counts),
        action_hint_counts=dict(summary.action_hint_counts),
        average_scores={key: str(value) for key, value in summary.average_scores.items()},
        watch_rate=summary.watch_rate,
        material_divergence_rate=summary.material_divergence_rate,
        needs_review_rate=summary.needs_review_rate,
        do_not_compare_rate=summary.do_not_compare_rate,
        markets_compared=summary.markets_compared,
        metadata_json=_metadata(summary.metadata),
    )


def _divergence_run_summary_from_record(
    record: CrossVenueDivergenceRunSummaryRecord,
) -> CrossVenueDivergenceRunSummary:
    return CrossVenueDivergenceRunSummary(
        summary_id=record.summary_id,
        divergence_run_id=record.divergence_run_id,
        created_at=record.created_at,
        total_snapshots=record.total_snapshots,
        total_signals=record.total_signals,
        total_assessments=record.total_assessments,
        status_counts=dict(record.status_counts),
        severity_counts=dict(record.severity_counts),
        action_hint_counts=dict(record.action_hint_counts),
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        watch_rate=record.watch_rate,
        material_divergence_rate=record.material_divergence_rate,
        needs_review_rate=record.needs_review_rate,
        do_not_compare_rate=record.do_not_compare_rate,
        markets_compared=record.markets_compared,
        metadata=_metadata(record.metadata_json),
    )


def _trade_intent_to_record(intent: TradeIntent) -> TradeIntentRecord:
    return TradeIntentRecord(
        trade_intent_id=intent.trade_intent_id,
        market_id=intent.market_id,
        outcome_id=intent.outcome_id,
        venue_id=intent.venue_id,
        strategy_context=intent.strategy_context.value,
        side=intent.side.value,
        intent_type=intent.intent_type.value,
        requested_price=intent.requested_price,
        requested_size_units=intent.requested_size_units,
        requested_notional_usd=intent.requested_notional_usd,
        asof_timestamp=intent.asof_timestamp,
        metadata_json=_metadata(intent.metadata),
    )


def _trade_intent_from_record(record: TradeIntentRecord) -> TradeIntent:
    return TradeIntent(
        trade_intent_id=record.trade_intent_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        strategy_context=StrategyContext(record.strategy_context),
        side=PreTradeSide(record.side),
        intent_type=TradeIntentType(record.intent_type),
        requested_price=record.requested_price,
        requested_size_units=record.requested_size_units,
        requested_notional_usd=record.requested_notional_usd,
        asof_timestamp=record.asof_timestamp,
        metadata=_metadata(record.metadata_json),
    )


def _pretrade_policy_to_record(policy: PreTradePolicy) -> PreTradePolicyRecord:
    return PreTradePolicyRecord(
        policy_id=policy.policy_id,
        policy_name=policy.policy_name,
        policy_version=policy.policy_version,
        created_at=policy.created_at,
        effective_from=policy.effective_from,
        effective_until=policy.effective_until,
        is_active=policy.is_active,
        max_order_size_units=policy.max_order_size_units,
        max_market_exposure_units=policy.max_market_exposure_units,
        max_event_exposure_units=policy.max_event_exposure_units,
        max_venue_exposure_units=policy.max_venue_exposure_units,
        max_strategy_exposure_units=policy.max_strategy_exposure_units,
        allow_unknown_exposure=policy.allow_unknown_exposure,
        require_active_market=policy.require_active_market,
        require_rule_snapshot=policy.require_rule_snapshot,
        require_trust_verdict=policy.require_trust_verdict,
        require_market_data_quality=policy.require_market_data_quality,
        min_market_data_quality_score=policy.min_market_data_quality_score,
        max_resolution_risk_score=policy.max_resolution_risk_score,
        max_integrity_risk_score=policy.max_integrity_risk_score,
        max_divergence_score_without_review=policy.max_divergence_score_without_review,
        max_staleness_seconds=policy.max_staleness_seconds,
        max_spread=policy.max_spread,
        max_spread_bps=policy.max_spread_bps,
        allow_manual_review_markets=policy.allow_manual_review_markets,
        allow_comparable_with_haircut=policy.allow_comparable_with_haircut,
        metadata_json=_metadata(policy.metadata),
    )


def _pretrade_policy_from_record(record: PreTradePolicyRecord) -> PreTradePolicy:
    return PreTradePolicy(
        policy_id=record.policy_id,
        policy_name=record.policy_name,
        policy_version=record.policy_version,
        created_at=record.created_at,
        effective_from=record.effective_from,
        effective_until=record.effective_until,
        is_active=record.is_active,
        max_order_size_units=record.max_order_size_units,
        max_market_exposure_units=record.max_market_exposure_units,
        max_event_exposure_units=record.max_event_exposure_units,
        max_venue_exposure_units=record.max_venue_exposure_units,
        max_strategy_exposure_units=record.max_strategy_exposure_units,
        allow_unknown_exposure=record.allow_unknown_exposure,
        require_active_market=record.require_active_market,
        require_rule_snapshot=record.require_rule_snapshot,
        require_trust_verdict=record.require_trust_verdict,
        require_market_data_quality=record.require_market_data_quality,
        min_market_data_quality_score=record.min_market_data_quality_score,
        max_resolution_risk_score=record.max_resolution_risk_score,
        max_integrity_risk_score=record.max_integrity_risk_score,
        max_divergence_score_without_review=record.max_divergence_score_without_review,
        max_staleness_seconds=record.max_staleness_seconds,
        max_spread=record.max_spread,
        max_spread_bps=record.max_spread_bps,
        allow_manual_review_markets=record.allow_manual_review_markets,
        allow_comparable_with_haircut=record.allow_comparable_with_haircut,
        metadata=_metadata(record.metadata_json),
    )


def _market_restriction_rule_to_record(
    rule: MarketRestrictionRule,
) -> MarketRestrictionRuleRecord:
    return MarketRestrictionRuleRecord(
        restriction_id=rule.restriction_id,
        created_at=rule.created_at,
        is_active=rule.is_active,
        restriction_type=rule.restriction_type.value,
        scope_type=rule.scope_type.value,
        venue_id=rule.venue_id,
        venue_name=rule.venue_name,
        market_id=rule.market_id,
        event_id=rule.event_id,
        category=rule.category,
        title_pattern=rule.title_pattern,
        reason_code=rule.reason_code,
        description=rule.description,
        effective_from=rule.effective_from,
        effective_until=rule.effective_until,
        metadata_json=_metadata(rule.metadata),
    )


def _market_restriction_rule_from_record(
    record: MarketRestrictionRuleRecord,
) -> MarketRestrictionRule:
    return MarketRestrictionRule(
        restriction_id=record.restriction_id,
        created_at=record.created_at,
        is_active=record.is_active,
        restriction_type=RestrictionType(record.restriction_type),
        scope_type=RestrictionScopeType(record.scope_type),
        venue_id=record.venue_id,
        venue_name=record.venue_name,
        market_id=record.market_id,
        event_id=record.event_id,
        category=record.category,
        title_pattern=record.title_pattern,
        reason_code=record.reason_code,
        description=record.description,
        effective_from=record.effective_from,
        effective_until=record.effective_until,
        metadata=_metadata(record.metadata_json),
    )


def _exposure_snapshot_to_record(snapshot: ExposureSnapshot) -> ExposureSnapshotRecord:
    return ExposureSnapshotRecord(
        exposure_snapshot_id=snapshot.exposure_snapshot_id,
        asof_timestamp=snapshot.asof_timestamp,
        created_at=snapshot.created_at,
        source=snapshot.source.value,
        market_id=snapshot.market_id,
        event_id=snapshot.event_id,
        venue_id=snapshot.venue_id,
        strategy_context=snapshot.strategy_context,
        market_exposure_units=snapshot.market_exposure_units,
        event_exposure_units=snapshot.event_exposure_units,
        venue_exposure_units=snapshot.venue_exposure_units,
        strategy_exposure_units=snapshot.strategy_exposure_units,
        metadata_json=_metadata(snapshot.metadata),
    )


def _exposure_snapshot_from_record(record: ExposureSnapshotRecord) -> ExposureSnapshot:
    return ExposureSnapshot(
        exposure_snapshot_id=record.exposure_snapshot_id,
        asof_timestamp=record.asof_timestamp,
        created_at=record.created_at,
        source=ExposureSource(record.source),
        market_id=record.market_id,
        event_id=record.event_id,
        venue_id=record.venue_id,
        strategy_context=record.strategy_context,
        market_exposure_units=record.market_exposure_units,
        event_exposure_units=record.event_exposure_units,
        venue_exposure_units=record.venue_exposure_units,
        strategy_exposure_units=record.strategy_exposure_units,
        metadata=_metadata(record.metadata_json),
    )


def _pretrade_input_snapshot_to_record(
    snapshot: PreTradeInputSnapshot,
) -> PreTradeInputSnapshotRecord:
    return PreTradeInputSnapshotRecord(
        input_snapshot_id=snapshot.input_snapshot_id,
        trade_intent_id=snapshot.trade_intent_id,
        market_id=snapshot.market_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        market_status=snapshot.market_status,
        event_id=snapshot.event_id,
        venue_id=snapshot.venue_id,
        latest_rule_snapshot_id=snapshot.latest_rule_snapshot_id,
        latest_rule_snapshot_hash=snapshot.latest_rule_snapshot_hash,
        latest_trust_verdict_id=snapshot.latest_trust_verdict_id,
        latest_quality_report_id=snapshot.latest_quality_report_id,
        latest_integrity_assessment_id=snapshot.latest_integrity_assessment_id,
        latest_equivalence_assessment_ids=list(snapshot.latest_equivalence_assessment_ids),
        latest_divergence_assessment_ids=list(snapshot.latest_divergence_assessment_ids),
        latest_price_snapshot_id=snapshot.latest_price_snapshot_id,
        latest_liquidity_snapshot_id=snapshot.latest_liquidity_snapshot_id,
        exposure_snapshot_id=snapshot.exposure_snapshot_id,
        policy_id=snapshot.policy_id,
        restriction_ids=list(snapshot.restriction_ids),
        resolution_risk_score=snapshot.resolution_risk_score,
        market_data_quality_score=snapshot.market_data_quality_score,
        integrity_risk_score=snapshot.integrity_risk_score,
        max_divergence_score=snapshot.max_divergence_score,
        comparable_market_count=snapshot.comparable_market_count,
        manual_review_equivalence_count=snapshot.manual_review_equivalence_count,
        do_not_compare_equivalence_count=snapshot.do_not_compare_equivalence_count,
        divergence_watch_count=snapshot.divergence_watch_count,
        material_divergence_count=snapshot.material_divergence_count,
        divergence_needs_review_count=snapshot.divergence_needs_review_count,
        divergence_do_not_compare_count=snapshot.divergence_do_not_compare_count,
        current_market_exposure_units=snapshot.current_market_exposure_units,
        current_event_exposure_units=snapshot.current_event_exposure_units,
        current_venue_exposure_units=snapshot.current_venue_exposure_units,
        current_strategy_exposure_units=snapshot.current_strategy_exposure_units,
        input_hash=snapshot.input_hash,
        metadata_json=_metadata(snapshot.metadata),
    )


def _pretrade_input_snapshot_from_record(
    record: PreTradeInputSnapshotRecord,
) -> PreTradeInputSnapshot:
    return PreTradeInputSnapshot(
        input_snapshot_id=record.input_snapshot_id,
        trade_intent_id=record.trade_intent_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        market_status=record.market_status,
        event_id=record.event_id,
        venue_id=record.venue_id,
        latest_rule_snapshot_id=record.latest_rule_snapshot_id,
        latest_rule_snapshot_hash=record.latest_rule_snapshot_hash,
        latest_trust_verdict_id=record.latest_trust_verdict_id,
        latest_quality_report_id=record.latest_quality_report_id,
        latest_integrity_assessment_id=record.latest_integrity_assessment_id,
        latest_equivalence_assessment_ids=list(record.latest_equivalence_assessment_ids),
        latest_divergence_assessment_ids=list(record.latest_divergence_assessment_ids),
        latest_price_snapshot_id=record.latest_price_snapshot_id,
        latest_liquidity_snapshot_id=record.latest_liquidity_snapshot_id,
        exposure_snapshot_id=record.exposure_snapshot_id,
        policy_id=record.policy_id,
        restriction_ids=list(record.restriction_ids),
        resolution_risk_score=record.resolution_risk_score,
        market_data_quality_score=record.market_data_quality_score,
        integrity_risk_score=record.integrity_risk_score,
        max_divergence_score=record.max_divergence_score,
        comparable_market_count=record.comparable_market_count,
        manual_review_equivalence_count=record.manual_review_equivalence_count,
        do_not_compare_equivalence_count=record.do_not_compare_equivalence_count,
        divergence_watch_count=record.divergence_watch_count,
        material_divergence_count=record.material_divergence_count,
        divergence_needs_review_count=record.divergence_needs_review_count,
        divergence_do_not_compare_count=record.divergence_do_not_compare_count,
        current_market_exposure_units=record.current_market_exposure_units,
        current_event_exposure_units=record.current_event_exposure_units,
        current_venue_exposure_units=record.current_venue_exposure_units,
        current_strategy_exposure_units=record.current_strategy_exposure_units,
        input_hash=record.input_hash,
        metadata=_metadata(record.metadata_json),
    )


def _pretrade_decision_to_record(decision: PreTradeDecision) -> PreTradeDecisionRecord:
    return PreTradeDecisionRecord(
        pretrade_decision_id=decision.pretrade_decision_id,
        trade_intent_id=decision.trade_intent_id,
        input_snapshot_id=decision.input_snapshot_id,
        market_id=decision.market_id,
        asof_timestamp=decision.asof_timestamp,
        generated_at=decision.generated_at,
        available_at=decision.available_at,
        policy_id=decision.policy_id,
        policy_name=decision.policy_name,
        policy_version=decision.policy_version,
        action=decision.action.value,
        allowed_size_multiplier=decision.allowed_size_multiplier,
        requested_size_units=decision.requested_size_units,
        max_allowed_size_units=decision.max_allowed_size_units,
        final_allowed_size_units=decision.final_allowed_size_units,
        passive_only=decision.passive_only,
        manual_review_required=decision.manual_review_required,
        hard_blocked=decision.hard_blocked,
        composite_risk_score=decision.composite_risk_score,
        resolution_risk_score=decision.resolution_risk_score,
        market_data_quality_score=decision.market_data_quality_score,
        integrity_risk_score=decision.integrity_risk_score,
        max_divergence_score=decision.max_divergence_score,
        exposure_risk_score=decision.exposure_risk_score,
        hard_blockers=list(decision.hard_blockers),
        warnings=list(decision.warnings),
        reason_codes=list(decision.reason_codes),
        evidence=dict(decision.evidence),
        input_hash=decision.input_hash,
        output_hash=decision.output_hash,
        metadata_json=_metadata(decision.metadata),
    )


def _pretrade_decision_from_record(record: PreTradeDecisionRecord) -> PreTradeDecision:
    return PreTradeDecision(
        pretrade_decision_id=record.pretrade_decision_id,
        trade_intent_id=record.trade_intent_id,
        input_snapshot_id=record.input_snapshot_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        policy_id=record.policy_id,
        policy_name=record.policy_name,
        policy_version=record.policy_version,
        action=PreTradeAction(record.action),
        allowed_size_multiplier=record.allowed_size_multiplier,
        requested_size_units=record.requested_size_units,
        max_allowed_size_units=record.max_allowed_size_units,
        final_allowed_size_units=record.final_allowed_size_units,
        passive_only=record.passive_only,
        manual_review_required=record.manual_review_required,
        hard_blocked=record.hard_blocked,
        composite_risk_score=record.composite_risk_score,
        resolution_risk_score=record.resolution_risk_score,
        market_data_quality_score=record.market_data_quality_score,
        integrity_risk_score=record.integrity_risk_score,
        max_divergence_score=record.max_divergence_score,
        exposure_risk_score=record.exposure_risk_score,
        hard_blockers=list(record.hard_blockers),
        warnings=list(record.warnings),
        reason_codes=list(record.reason_codes),
        evidence=dict(record.evidence),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _pretrade_run_to_record(run: PreTradeRun) -> PreTradeRunRecord:
    return PreTradeRunRecord(
        pretrade_run_id=run.pretrade_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        asof_timestamp=run.asof_timestamp,
        policy_id=run.policy_id,
        market_ids=list(run.market_ids),
        max_checks=run.max_checks,
        config_json=_metadata(run.config),
        metadata_json=_metadata(run.metadata),
        decisions_created=run.decisions_created,
        errors_count=run.errors_count,
    )


def _pretrade_run_from_record(record: PreTradeRunRecord) -> PreTradeRun:
    return PreTradeRun(
        pretrade_run_id=record.pretrade_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=PreTradeRunStatus(record.status),
        asof_timestamp=record.asof_timestamp,
        policy_id=record.policy_id,
        market_ids=list(record.market_ids),
        max_checks=record.max_checks,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        decisions_created=record.decisions_created,
        errors_count=record.errors_count,
    )


def _pretrade_run_summary_to_record(
    summary: PreTradeRunSummary,
) -> PreTradeRunSummaryRecord:
    return PreTradeRunSummaryRecord(
        summary_id=summary.summary_id,
        pretrade_run_id=summary.pretrade_run_id,
        created_at=summary.created_at,
        total_decisions=summary.total_decisions,
        action_counts=dict(summary.action_counts),
        average_scores={key: str(value) for key, value in summary.average_scores.items()},
        no_trade_rate=summary.no_trade_rate,
        manual_review_rate=summary.manual_review_rate,
        passive_only_rate=summary.passive_only_rate,
        allow_smaller_size_rate=summary.allow_smaller_size_rate,
        allow_rate=summary.allow_rate,
        hard_block_rate=summary.hard_block_rate,
        total_requested_size_units=summary.total_requested_size_units,
        total_final_allowed_size_units=summary.total_final_allowed_size_units,
        metadata_json=_metadata(summary.metadata),
    )


def _pretrade_run_summary_from_record(
    record: PreTradeRunSummaryRecord,
) -> PreTradeRunSummary:
    return PreTradeRunSummary(
        summary_id=record.summary_id,
        pretrade_run_id=record.pretrade_run_id,
        created_at=record.created_at,
        total_decisions=record.total_decisions,
        action_counts=dict(record.action_counts),
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        no_trade_rate=record.no_trade_rate,
        manual_review_rate=record.manual_review_rate,
        passive_only_rate=record.passive_only_rate,
        allow_smaller_size_rate=record.allow_smaller_size_rate,
        allow_rate=record.allow_rate,
        hard_block_rate=record.hard_block_rate,
        total_requested_size_units=record.total_requested_size_units,
        total_final_allowed_size_units=record.total_final_allowed_size_units,
        metadata=_metadata(record.metadata_json),
    )


def _paper_execution_policy_to_record(
    policy: PaperExecutionPolicy,
) -> PaperExecutionPolicyRecord:
    return PaperExecutionPolicyRecord(
        paper_policy_id=policy.paper_policy_id,
        policy_name=policy.policy_name,
        policy_version=policy.policy_version,
        created_at=policy.created_at,
        is_active=policy.is_active,
        allow_simulated_shorts=policy.allow_simulated_shorts,
        allow_partial_fills=policy.allow_partial_fills,
        default_fee_bps=policy.default_fee_bps,
        max_slippage_bps=policy.max_slippage_bps,
        require_pretrade_allow=policy.require_pretrade_allow,
        allow_pretrade_allow_smaller_size=policy.allow_pretrade_allow_smaller_size,
        allow_pretrade_passive_only_for_passive_orders=(
            policy.allow_pretrade_passive_only_for_passive_orders
        ),
        reject_manual_review=policy.reject_manual_review,
        reject_no_trade=policy.reject_no_trade,
        fill_model=policy.fill_model.value,
        metadata_json=_metadata(policy.metadata),
    )


def _paper_execution_policy_from_record(
    record: PaperExecutionPolicyRecord,
) -> PaperExecutionPolicy:
    return PaperExecutionPolicy(
        paper_policy_id=record.paper_policy_id,
        policy_name=record.policy_name,
        policy_version=record.policy_version,
        created_at=record.created_at,
        is_active=record.is_active,
        allow_simulated_shorts=record.allow_simulated_shorts,
        allow_partial_fills=record.allow_partial_fills,
        default_fee_bps=record.default_fee_bps,
        max_slippage_bps=record.max_slippage_bps,
        require_pretrade_allow=record.require_pretrade_allow,
        allow_pretrade_allow_smaller_size=record.allow_pretrade_allow_smaller_size,
        allow_pretrade_passive_only_for_passive_orders=(
            record.allow_pretrade_passive_only_for_passive_orders
        ),
        reject_manual_review=record.reject_manual_review,
        reject_no_trade=record.reject_no_trade,
        fill_model=FillModel(record.fill_model),
        metadata=_metadata(record.metadata_json),
    )


def _paper_order_to_record(order: PaperOrder) -> PaperOrderRecord:
    return PaperOrderRecord(
        paper_order_id=order.paper_order_id,
        trade_intent_id=order.trade_intent_id,
        pretrade_decision_id=order.pretrade_decision_id,
        paper_policy_id=order.paper_policy_id,
        simulation_run_id=order.simulation_run_id,
        market_id=order.market_id,
        outcome_id=order.outcome_id,
        venue_id=order.venue_id,
        side=order.side.value,
        intent_type=order.intent_type,
        requested_price=order.requested_price,
        limit_price=order.limit_price,
        requested_size_units=order.requested_size_units,
        accepted_size_units=order.accepted_size_units,
        filled_size_units=order.filled_size_units,
        remaining_size_units=order.remaining_size_units,
        status=order.status.value,
        rejection_reason_codes=list(order.rejection_reason_codes),
        created_at=order.created_at,
        asof_timestamp=order.asof_timestamp,
        available_at=order.available_at,
        metadata_json=_metadata(order.metadata),
    )


def _paper_order_from_record(record: PaperOrderRecord) -> PaperOrder:
    return PaperOrder(
        paper_order_id=record.paper_order_id,
        trade_intent_id=record.trade_intent_id,
        pretrade_decision_id=record.pretrade_decision_id,
        paper_policy_id=record.paper_policy_id,
        simulation_run_id=record.simulation_run_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        side=PreTradeSide(record.side),
        intent_type=record.intent_type,
        requested_price=record.requested_price,
        limit_price=record.limit_price,
        requested_size_units=record.requested_size_units,
        accepted_size_units=record.accepted_size_units,
        filled_size_units=record.filled_size_units,
        remaining_size_units=record.remaining_size_units,
        status=PaperOrderStatus(record.status),
        rejection_reason_codes=list(record.rejection_reason_codes),
        created_at=record.created_at,
        asof_timestamp=record.asof_timestamp,
        available_at=record.available_at,
        metadata=_metadata(record.metadata_json),
    )


def _paper_fill_to_record(fill: PaperFill) -> PaperFillRecord:
    return PaperFillRecord(
        paper_fill_id=fill.paper_fill_id,
        paper_order_id=fill.paper_order_id,
        simulation_run_id=fill.simulation_run_id,
        market_id=fill.market_id,
        outcome_id=fill.outcome_id,
        venue_id=fill.venue_id,
        side=fill.side.value,
        filled_at=fill.filled_at,
        asof_timestamp=fill.asof_timestamp,
        price=fill.price,
        size_units=fill.size_units,
        notional=fill.notional,
        fee_amount=fill.fee_amount,
        fee_bps=fill.fee_bps,
        liquidity_source=fill.liquidity_source.value,
        source_orderbook_snapshot_id=fill.source_orderbook_snapshot_id,
        source_price_snapshot_id=fill.source_price_snapshot_id,
        source_liquidity_snapshot_id=fill.source_liquidity_snapshot_id,
        fill_reason=fill.fill_reason,
        is_simulated=fill.is_simulated,
        metadata_json=_metadata(fill.metadata),
    )


def _paper_fill_from_record(record: PaperFillRecord) -> PaperFill:
    return PaperFill(
        paper_fill_id=record.paper_fill_id,
        paper_order_id=record.paper_order_id,
        simulation_run_id=record.simulation_run_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        side=PreTradeSide(record.side),
        filled_at=record.filled_at,
        asof_timestamp=record.asof_timestamp,
        price=record.price,
        size_units=record.size_units,
        notional=record.notional,
        fee_amount=record.fee_amount,
        fee_bps=record.fee_bps,
        liquidity_source=LiquiditySource(record.liquidity_source),
        source_orderbook_snapshot_id=record.source_orderbook_snapshot_id,
        source_price_snapshot_id=record.source_price_snapshot_id,
        source_liquidity_snapshot_id=record.source_liquidity_snapshot_id,
        fill_reason=record.fill_reason,
        is_simulated=record.is_simulated,
        metadata=_metadata(record.metadata_json),
    )


def _paper_ledger_entry_to_record(
    entry: PaperLedgerEntry,
) -> PaperLedgerEntryRecord:
    return PaperLedgerEntryRecord(
        ledger_entry_id=entry.ledger_entry_id,
        simulation_run_id=entry.simulation_run_id,
        paper_order_id=entry.paper_order_id,
        paper_fill_id=entry.paper_fill_id,
        market_id=entry.market_id,
        outcome_id=entry.outcome_id,
        venue_id=entry.venue_id,
        entry_type=entry.entry_type.value,
        occurred_at=entry.occurred_at,
        amount=entry.amount,
        currency=entry.currency,
        description=entry.description,
        is_simulated=entry.is_simulated,
        metadata_json=_metadata(entry.metadata),
    )


def _paper_ledger_entry_from_record(
    record: PaperLedgerEntryRecord,
) -> PaperLedgerEntry:
    return PaperLedgerEntry(
        ledger_entry_id=record.ledger_entry_id,
        simulation_run_id=record.simulation_run_id,
        paper_order_id=record.paper_order_id,
        paper_fill_id=record.paper_fill_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        entry_type=PaperLedgerEntryType(record.entry_type),
        occurred_at=record.occurred_at,
        amount=record.amount,
        currency=record.currency,
        description=record.description,
        is_simulated=record.is_simulated,
        metadata=_metadata(record.metadata_json),
    )


def _paper_position_snapshot_to_record(
    snapshot: PaperPositionSnapshot,
) -> PaperPositionSnapshotRecord:
    return PaperPositionSnapshotRecord(
        position_snapshot_id=snapshot.position_snapshot_id,
        simulation_run_id=snapshot.simulation_run_id,
        market_id=snapshot.market_id,
        outcome_id=snapshot.outcome_id,
        venue_id=snapshot.venue_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        position_units=snapshot.position_units,
        average_entry_price=snapshot.average_entry_price,
        cost_basis=snapshot.cost_basis,
        realized_pnl_simulated=snapshot.realized_pnl_simulated,
        unrealized_pnl_simulated=snapshot.unrealized_pnl_simulated,
        mark_price=snapshot.mark_price,
        mark_price_snapshot_id=snapshot.mark_price_snapshot_id,
        is_flat=snapshot.is_flat,
        is_simulated=snapshot.is_simulated,
        metadata_json=_metadata(snapshot.metadata),
    )


def _paper_position_snapshot_from_record(
    record: PaperPositionSnapshotRecord,
) -> PaperPositionSnapshot:
    return PaperPositionSnapshot(
        position_snapshot_id=record.position_snapshot_id,
        simulation_run_id=record.simulation_run_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        position_units=record.position_units,
        average_entry_price=record.average_entry_price,
        cost_basis=record.cost_basis,
        realized_pnl_simulated=record.realized_pnl_simulated,
        unrealized_pnl_simulated=record.unrealized_pnl_simulated,
        mark_price=record.mark_price,
        mark_price_snapshot_id=record.mark_price_snapshot_id,
        is_flat=record.is_flat,
        is_simulated=record.is_simulated,
        metadata=_metadata(record.metadata_json),
    )


def _paper_portfolio_snapshot_to_record(
    snapshot: PaperPortfolioSnapshot,
) -> PaperPortfolioSnapshotRecord:
    return PaperPortfolioSnapshotRecord(
        portfolio_snapshot_id=snapshot.portfolio_snapshot_id,
        simulation_run_id=snapshot.simulation_run_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        cash_balance_simulated=snapshot.cash_balance_simulated,
        gross_exposure_simulated=snapshot.gross_exposure_simulated,
        net_exposure_simulated=snapshot.net_exposure_simulated,
        realized_pnl_simulated=snapshot.realized_pnl_simulated,
        unrealized_pnl_simulated=snapshot.unrealized_pnl_simulated,
        total_fees_simulated=snapshot.total_fees_simulated,
        total_equity_simulated=snapshot.total_equity_simulated,
        open_positions_count=snapshot.open_positions_count,
        closed_positions_count=snapshot.closed_positions_count,
        is_simulated=snapshot.is_simulated,
        metadata_json=_metadata(snapshot.metadata),
    )


def _paper_portfolio_snapshot_from_record(
    record: PaperPortfolioSnapshotRecord,
) -> PaperPortfolioSnapshot:
    return PaperPortfolioSnapshot(
        portfolio_snapshot_id=record.portfolio_snapshot_id,
        simulation_run_id=record.simulation_run_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        cash_balance_simulated=record.cash_balance_simulated,
        gross_exposure_simulated=record.gross_exposure_simulated,
        net_exposure_simulated=record.net_exposure_simulated,
        realized_pnl_simulated=record.realized_pnl_simulated,
        unrealized_pnl_simulated=record.unrealized_pnl_simulated,
        total_fees_simulated=record.total_fees_simulated,
        total_equity_simulated=record.total_equity_simulated,
        open_positions_count=record.open_positions_count,
        closed_positions_count=record.closed_positions_count,
        is_simulated=record.is_simulated,
        metadata=_metadata(record.metadata_json),
    )


def _paper_simulation_run_to_record(run: PaperSimulationRun) -> PaperSimulationRunRecord:
    return PaperSimulationRunRecord(
        simulation_run_id=run.simulation_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        paper_policy_id=run.paper_policy_id,
        start_time=run.start_time,
        end_time=run.end_time,
        interval_seconds=run.interval_seconds,
        market_ids=list(run.market_ids),
        max_orders=run.max_orders,
        initial_cash_simulated=run.initial_cash_simulated,
        config_json=_metadata(run.config),
        metadata_json=_metadata(run.metadata),
        orders_created=run.orders_created,
        fills_created=run.fills_created,
        rejected_orders=run.rejected_orders,
        errors_count=run.errors_count,
    )


def _paper_simulation_run_from_record(
    record: PaperSimulationRunRecord,
) -> PaperSimulationRun:
    return PaperSimulationRun(
        simulation_run_id=record.simulation_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=PaperSimulationRunStatus(record.status),
        paper_policy_id=record.paper_policy_id,
        start_time=record.start_time,
        end_time=record.end_time,
        interval_seconds=record.interval_seconds,
        market_ids=list(record.market_ids),
        max_orders=record.max_orders,
        initial_cash_simulated=record.initial_cash_simulated,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        orders_created=record.orders_created,
        fills_created=record.fills_created,
        rejected_orders=record.rejected_orders,
        errors_count=record.errors_count,
    )


def _paper_simulation_run_summary_to_record(
    summary: PaperSimulationRunSummary,
) -> PaperSimulationRunSummaryRecord:
    return PaperSimulationRunSummaryRecord(
        summary_id=summary.summary_id,
        simulation_run_id=summary.simulation_run_id,
        created_at=summary.created_at,
        total_orders=summary.total_orders,
        filled_orders=summary.filled_orders,
        partially_filled_orders=summary.partially_filled_orders,
        rejected_orders=summary.rejected_orders,
        total_fills=summary.total_fills,
        total_fees_simulated=summary.total_fees_simulated,
        final_cash_simulated=summary.final_cash_simulated,
        final_gross_exposure_simulated=summary.final_gross_exposure_simulated,
        final_net_exposure_simulated=summary.final_net_exposure_simulated,
        final_realized_pnl_simulated=summary.final_realized_pnl_simulated,
        final_unrealized_pnl_simulated=summary.final_unrealized_pnl_simulated,
        final_total_equity_simulated=summary.final_total_equity_simulated,
        fill_rate=summary.fill_rate,
        rejection_rate=summary.rejection_rate,
        metadata_json=_metadata(summary.metadata),
    )


def _paper_simulation_run_summary_from_record(
    record: PaperSimulationRunSummaryRecord,
) -> PaperSimulationRunSummary:
    return PaperSimulationRunSummary(
        summary_id=record.summary_id,
        simulation_run_id=record.simulation_run_id,
        created_at=record.created_at,
        total_orders=record.total_orders,
        filled_orders=record.filled_orders,
        partially_filled_orders=record.partially_filled_orders,
        rejected_orders=record.rejected_orders,
        total_fills=record.total_fills,
        total_fees_simulated=record.total_fees_simulated,
        final_cash_simulated=record.final_cash_simulated,
        final_gross_exposure_simulated=record.final_gross_exposure_simulated,
        final_net_exposure_simulated=record.final_net_exposure_simulated,
        final_realized_pnl_simulated=record.final_realized_pnl_simulated,
        final_unrealized_pnl_simulated=record.final_unrealized_pnl_simulated,
        final_total_equity_simulated=record.final_total_equity_simulated,
        fill_rate=record.fill_rate,
        rejection_rate=record.rejection_rate,
        metadata=_metadata(record.metadata_json),
    )


def _research_strategy_definition_to_record(
    definition: ResearchStrategyDefinition,
) -> ResearchStrategyDefinitionRecord:
    return ResearchStrategyDefinitionRecord(
        strategy_id=definition.strategy_id,
        strategy_name=definition.strategy_name,
        strategy_version=definition.strategy_version,
        created_at=definition.created_at,
        is_active=definition.is_active,
        family=definition.family.value,
        description=definition.description,
        requires_pretrade=definition.requires_pretrade,
        allows_paper_simulation=definition.allows_paper_simulation,
        default_requested_size_units=definition.default_requested_size_units,
        default_intent_type=definition.default_intent_type,
        default_strategy_context=definition.default_strategy_context,
        config_json=_json_metadata(definition.config),
        metadata_json=_json_metadata(definition.metadata),
    )


def _research_strategy_definition_from_record(
    record: ResearchStrategyDefinitionRecord,
) -> ResearchStrategyDefinition:
    return ResearchStrategyDefinition(
        strategy_id=record.strategy_id,
        strategy_name=record.strategy_name,
        strategy_version=record.strategy_version,
        created_at=record.created_at,
        is_active=record.is_active,
        family=ResearchStrategyFamily(record.family),
        description=record.description,
        requires_pretrade=record.requires_pretrade,
        allows_paper_simulation=record.allows_paper_simulation,
        default_requested_size_units=record.default_requested_size_units,
        default_intent_type=record.default_intent_type,
        default_strategy_context=record.default_strategy_context,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
    )


def _research_feature_snapshot_to_record(
    snapshot: ResearchFeatureSnapshot,
) -> ResearchFeatureSnapshotRecord:
    return ResearchFeatureSnapshotRecord(
        research_feature_snapshot_id=snapshot.research_feature_snapshot_id,
        market_id=snapshot.market_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        feature_source=snapshot.feature_source.value,
        feature_family=snapshot.feature_family.value,
        source_ref_ids=list(snapshot.source_ref_ids),
        values_json=_json_metadata(snapshot.values),
        reason_codes=list(snapshot.reason_codes),
        input_hash=snapshot.input_hash,
        output_hash=snapshot.output_hash,
        metadata_json=_json_metadata(snapshot.metadata),
    )


def _research_feature_snapshot_from_record(
    record: ResearchFeatureSnapshotRecord,
) -> ResearchFeatureSnapshot:
    return ResearchFeatureSnapshot(
        research_feature_snapshot_id=record.research_feature_snapshot_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        feature_source=ResearchFeatureSource(record.feature_source),
        feature_family=ResearchFeatureFamily(record.feature_family),
        source_ref_ids=list(record.source_ref_ids),
        values=_metadata(record.values_json),
        reason_codes=list(record.reason_codes),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _research_signal_to_record(signal: ResearchSignal) -> ResearchSignalRecord:
    return ResearchSignalRecord(
        research_signal_id=signal.research_signal_id,
        strategy_id=signal.strategy_id,
        strategy_name=signal.strategy_name,
        strategy_version=signal.strategy_version,
        market_id=signal.market_id,
        asof_timestamp=signal.asof_timestamp,
        generated_at=signal.generated_at,
        available_at=signal.available_at,
        signal_type=signal.signal_type.value,
        signal_strength_score=signal.signal_strength_score,
        confidence_score=signal.confidence_score,
        action_bias=signal.action_bias.value,
        reason_codes=list(signal.reason_codes),
        source_feature_ids=list(signal.source_feature_ids),
        source_ref_ids=list(signal.source_ref_ids),
        input_hash=signal.input_hash,
        output_hash=signal.output_hash,
        metadata_json=_json_metadata(signal.metadata),
    )


def _research_signal_from_record(record: ResearchSignalRecord) -> ResearchSignal:
    return ResearchSignal(
        research_signal_id=record.research_signal_id,
        strategy_id=record.strategy_id,
        strategy_name=record.strategy_name,
        strategy_version=record.strategy_version,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        signal_type=ResearchSignalType(record.signal_type),
        signal_strength_score=record.signal_strength_score,
        confidence_score=record.confidence_score,
        action_bias=ResearchActionBias(record.action_bias),
        reason_codes=list(record.reason_codes),
        source_feature_ids=list(record.source_feature_ids),
        source_ref_ids=list(record.source_ref_ids),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _research_intent_proposal_to_record(
    proposal: ResearchIntentProposal,
) -> ResearchIntentProposalRecord:
    return ResearchIntentProposalRecord(
        proposal_id=proposal.proposal_id,
        strategy_id=proposal.strategy_id,
        strategy_name=proposal.strategy_name,
        strategy_version=proposal.strategy_version,
        research_signal_id=proposal.research_signal_id,
        market_id=proposal.market_id,
        outcome_id=proposal.outcome_id,
        venue_id=proposal.venue_id,
        asof_timestamp=proposal.asof_timestamp,
        generated_at=proposal.generated_at,
        available_at=proposal.available_at,
        side=proposal.side.value,
        intent_type=proposal.intent_type,
        strategy_context=proposal.strategy_context,
        requested_price=proposal.requested_price,
        requested_size_units=proposal.requested_size_units,
        requested_notional_usd=proposal.requested_notional_usd,
        pretrade_required=proposal.pretrade_required,
        paper_simulation_allowed=proposal.paper_simulation_allowed,
        reason_codes=list(proposal.reason_codes),
        source_signal_ids=list(proposal.source_signal_ids),
        input_hash=proposal.input_hash,
        output_hash=proposal.output_hash,
        metadata_json=_json_metadata(proposal.metadata),
    )


def _research_intent_proposal_from_record(
    record: ResearchIntentProposalRecord,
) -> ResearchIntentProposal:
    return ResearchIntentProposal(
        proposal_id=record.proposal_id,
        strategy_id=record.strategy_id,
        strategy_name=record.strategy_name,
        strategy_version=record.strategy_version,
        research_signal_id=record.research_signal_id,
        market_id=record.market_id,
        outcome_id=record.outcome_id,
        venue_id=record.venue_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        side=PreTradeSide(record.side),
        intent_type=record.intent_type,
        strategy_context=record.strategy_context,
        requested_price=record.requested_price,
        requested_size_units=record.requested_size_units,
        requested_notional_usd=record.requested_notional_usd,
        pretrade_required=record.pretrade_required,
        paper_simulation_allowed=record.paper_simulation_allowed,
        reason_codes=list(record.reason_codes),
        source_signal_ids=list(record.source_signal_ids),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _research_decision_trace_to_record(
    trace: ResearchDecisionTrace,
) -> ResearchDecisionTraceRecord:
    return ResearchDecisionTraceRecord(
        trace_id=trace.trace_id,
        research_run_id=trace.research_run_id,
        strategy_id=trace.strategy_id,
        market_id=trace.market_id,
        asof_timestamp=trace.asof_timestamp,
        generated_at=trace.generated_at,
        available_at=trace.available_at,
        research_signal_id=trace.research_signal_id,
        proposal_id=trace.proposal_id,
        trade_intent_id=trace.trade_intent_id,
        pretrade_decision_id=trace.pretrade_decision_id,
        paper_order_id=trace.paper_order_id,
        paper_fill_ids=list(trace.paper_fill_ids),
        paper_position_snapshot_id=trace.paper_position_snapshot_id,
        paper_portfolio_snapshot_id=trace.paper_portfolio_snapshot_id,
        pretrade_action=trace.pretrade_action,
        paper_order_status=trace.paper_order_status,
        filled_size_units_simulated=trace.filled_size_units_simulated,
        avg_fill_price_simulated=trace.avg_fill_price_simulated,
        reason_codes=list(trace.reason_codes),
        input_hash=trace.input_hash,
        output_hash=trace.output_hash,
        metadata_json=_json_metadata(trace.metadata),
    )


def _research_decision_trace_from_record(
    record: ResearchDecisionTraceRecord,
) -> ResearchDecisionTrace:
    return ResearchDecisionTrace(
        trace_id=record.trace_id,
        research_run_id=record.research_run_id,
        strategy_id=record.strategy_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        research_signal_id=record.research_signal_id,
        proposal_id=record.proposal_id,
        trade_intent_id=record.trade_intent_id,
        pretrade_decision_id=record.pretrade_decision_id,
        paper_order_id=record.paper_order_id,
        paper_fill_ids=list(record.paper_fill_ids),
        paper_position_snapshot_id=record.paper_position_snapshot_id,
        paper_portfolio_snapshot_id=record.paper_portfolio_snapshot_id,
        pretrade_action=record.pretrade_action,
        paper_order_status=record.paper_order_status,
        filled_size_units_simulated=record.filled_size_units_simulated,
        avg_fill_price_simulated=record.avg_fill_price_simulated,
        reason_codes=list(record.reason_codes),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _research_run_to_record(run: ResearchRun) -> ResearchRunRecord:
    return ResearchRunRecord(
        research_run_id=run.research_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        start_time=run.start_time,
        end_time=run.end_time,
        interval_seconds=run.interval_seconds,
        strategy_ids=list(run.strategy_ids),
        market_ids=list(run.market_ids),
        max_steps=run.max_steps,
        max_proposals=run.max_proposals,
        enable_paper_simulation=run.enable_paper_simulation,
        paper_policy_id=run.paper_policy_id,
        initial_cash_simulated=run.initial_cash_simulated,
        config_json=_json_metadata(run.config),
        metadata_json=_json_metadata(run.metadata),
        signals_created=run.signals_created,
        proposals_created=run.proposals_created,
        pretrade_checks_created=run.pretrade_checks_created,
        paper_orders_created=run.paper_orders_created,
        paper_fills_created=run.paper_fills_created,
        errors_count=run.errors_count,
    )


def _research_run_from_record(record: ResearchRunRecord) -> ResearchRun:
    return ResearchRun(
        research_run_id=record.research_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=ResearchRunStatus(record.status),
        start_time=record.start_time,
        end_time=record.end_time,
        interval_seconds=record.interval_seconds,
        strategy_ids=list(record.strategy_ids),
        market_ids=list(record.market_ids),
        max_steps=record.max_steps,
        max_proposals=record.max_proposals,
        enable_paper_simulation=record.enable_paper_simulation,
        paper_policy_id=record.paper_policy_id,
        initial_cash_simulated=record.initial_cash_simulated,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        signals_created=record.signals_created,
        proposals_created=record.proposals_created,
        pretrade_checks_created=record.pretrade_checks_created,
        paper_orders_created=record.paper_orders_created,
        paper_fills_created=record.paper_fills_created,
        errors_count=record.errors_count,
    )


def _research_run_summary_to_record(
    summary: ResearchRunSummary,
) -> ResearchRunSummaryRecord:
    return ResearchRunSummaryRecord(
        summary_id=summary.summary_id,
        research_run_id=summary.research_run_id,
        created_at=summary.created_at,
        total_steps=summary.total_steps,
        total_signals=summary.total_signals,
        total_proposals=summary.total_proposals,
        total_pretrade_checks=summary.total_pretrade_checks,
        total_paper_orders=summary.total_paper_orders,
        total_paper_fills=summary.total_paper_fills,
        strategy_counts=dict(summary.strategy_counts),
        signal_type_counts=dict(summary.signal_type_counts),
        pretrade_action_counts=dict(summary.pretrade_action_counts),
        paper_order_status_counts=dict(summary.paper_order_status_counts),
        reason_code_counts=dict(summary.reason_code_counts),
        average_scores={key: str(value) for key, value in summary.average_scores.items()},
        total_requested_size_units=summary.total_requested_size_units,
        total_pretrade_allowed_size_units=summary.total_pretrade_allowed_size_units,
        total_filled_size_units_simulated=summary.total_filled_size_units_simulated,
        final_portfolio_equity_simulated=summary.final_portfolio_equity_simulated,
        final_realized_pnl_simulated=summary.final_realized_pnl_simulated,
        final_unrealized_pnl_simulated=summary.final_unrealized_pnl_simulated,
        proposal_to_pretrade_pass_rate=summary.proposal_to_pretrade_pass_rate,
        paper_fill_rate=summary.paper_fill_rate,
        metadata_json=_json_metadata(summary.metadata),
    )


def _research_run_summary_from_record(
    record: ResearchRunSummaryRecord,
) -> ResearchRunSummary:
    return ResearchRunSummary(
        summary_id=record.summary_id,
        research_run_id=record.research_run_id,
        created_at=record.created_at,
        total_steps=record.total_steps,
        total_signals=record.total_signals,
        total_proposals=record.total_proposals,
        total_pretrade_checks=record.total_pretrade_checks,
        total_paper_orders=record.total_paper_orders,
        total_paper_fills=record.total_paper_fills,
        strategy_counts=dict(record.strategy_counts),
        signal_type_counts=dict(record.signal_type_counts),
        pretrade_action_counts=dict(record.pretrade_action_counts),
        paper_order_status_counts=dict(record.paper_order_status_counts),
        reason_code_counts=dict(record.reason_code_counts),
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        total_requested_size_units=record.total_requested_size_units,
        total_pretrade_allowed_size_units=record.total_pretrade_allowed_size_units,
        total_filled_size_units_simulated=record.total_filled_size_units_simulated,
        final_portfolio_equity_simulated=record.final_portfolio_equity_simulated,
        final_realized_pnl_simulated=record.final_realized_pnl_simulated,
        final_unrealized_pnl_simulated=record.final_unrealized_pnl_simulated,
        proposal_to_pretrade_pass_rate=record.proposal_to_pretrade_pass_rate,
        paper_fill_rate=record.paper_fill_rate,
        metadata=_metadata(record.metadata_json),
    )


def _research_attribution_report_to_record(
    report: ResearchAttributionReport,
) -> ResearchAttributionReportRecord:
    return ResearchAttributionReportRecord(
        attribution_report_id=report.attribution_report_id,
        research_run_id=report.research_run_id,
        created_at=report.created_at,
        by_strategy=_json_metadata(report.by_strategy),
        by_market=_json_metadata(report.by_market),
        by_venue=_json_metadata(report.by_venue),
        by_reason_code=_json_metadata(report.by_reason_code),
        by_signal_type=_json_metadata(report.by_signal_type),
        by_pretrade_action=_json_metadata(report.by_pretrade_action),
        by_paper_order_status=_json_metadata(report.by_paper_order_status),
        simulated_pnl_by_strategy=_json_metadata(report.simulated_pnl_by_strategy),
        simulated_pnl_by_market=_json_metadata(report.simulated_pnl_by_market),
        metadata_json=_json_metadata(report.metadata),
    )


def _research_attribution_report_from_record(
    record: ResearchAttributionReportRecord,
) -> ResearchAttributionReport:
    return ResearchAttributionReport(
        attribution_report_id=record.attribution_report_id,
        research_run_id=record.research_run_id,
        created_at=record.created_at,
        by_strategy=_metadata(record.by_strategy),
        by_market=_metadata(record.by_market),
        by_venue=_metadata(record.by_venue),
        by_reason_code=_metadata(record.by_reason_code),
        by_signal_type=_metadata(record.by_signal_type),
        by_pretrade_action=_metadata(record.by_pretrade_action),
        by_paper_order_status=_metadata(record.by_paper_order_status),
        simulated_pnl_by_strategy=_metadata(record.simulated_pnl_by_strategy),
        simulated_pnl_by_market=_metadata(record.simulated_pnl_by_market),
        metadata=_metadata(record.metadata_json),
    )


def _scenario_seed_bundle_to_record(
    bundle: ScenarioSeedBundle,
) -> ScenarioSeedBundleRecord:
    return ScenarioSeedBundleRecord(
        seed_bundle_id=bundle.seed_bundle_id,
        market_id=bundle.market_id,
        asof_timestamp=bundle.asof_timestamp,
        generated_at=bundle.generated_at,
        available_at=bundle.available_at,
        seed_source=bundle.seed_source.value,
        market_title=bundle.market_title,
        market_description=bundle.market_description,
        rule_snapshot_id=bundle.rule_snapshot_id,
        rule_snapshot_hash=bundle.rule_snapshot_hash,
        resolution_predicate_id=bundle.resolution_predicate_id,
        ambiguity_assessment_id=bundle.ambiguity_assessment_id,
        market_data_quality_report_id=bundle.market_data_quality_report_id,
        integrity_assessment_id=bundle.integrity_assessment_id,
        equivalence_assessment_ids=list(bundle.equivalence_assessment_ids),
        divergence_assessment_ids=list(bundle.divergence_assessment_ids),
        trust_verdict_id=bundle.trust_verdict_id,
        source_ref_ids=list(bundle.source_ref_ids),
        seed_text=bundle.seed_text,
        structured_context=_json_metadata(bundle.structured_context),
        input_hash=bundle.input_hash,
        output_hash=bundle.output_hash,
        metadata_json=_json_metadata(bundle.metadata),
    )


def _scenario_seed_bundle_from_record(
    record: ScenarioSeedBundleRecord,
) -> ScenarioSeedBundle:
    return ScenarioSeedBundle(
        seed_bundle_id=record.seed_bundle_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        seed_source=ScenarioSeedSource(record.seed_source),
        market_title=record.market_title,
        market_description=record.market_description,
        rule_snapshot_id=record.rule_snapshot_id,
        rule_snapshot_hash=record.rule_snapshot_hash,
        resolution_predicate_id=record.resolution_predicate_id,
        ambiguity_assessment_id=record.ambiguity_assessment_id,
        market_data_quality_report_id=record.market_data_quality_report_id,
        integrity_assessment_id=record.integrity_assessment_id,
        equivalence_assessment_ids=list(record.equivalence_assessment_ids),
        divergence_assessment_ids=list(record.divergence_assessment_ids),
        trust_verdict_id=record.trust_verdict_id,
        source_ref_ids=list(record.source_ref_ids),
        seed_text=record.seed_text,
        structured_context=_metadata(record.structured_context),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _scenario_simulation_spec_to_record(
    spec: ScenarioSimulationSpec,
) -> ScenarioSimulationSpecRecord:
    return ScenarioSimulationSpecRecord(
        scenario_spec_id=spec.scenario_spec_id,
        seed_bundle_id=spec.seed_bundle_id,
        market_id=spec.market_id,
        asof_timestamp=spec.asof_timestamp,
        created_at=spec.created_at,
        scenario_engine=spec.scenario_engine.value,
        scenario_goal=spec.scenario_goal,
        horizon_hours=spec.horizon_hours,
        requested_agent_count=spec.requested_agent_count,
        requested_rounds=spec.requested_rounds,
        variables=_json_metadata(spec.variables),
        constraints=_json_metadata(spec.constraints),
        metadata_json=_json_metadata(spec.metadata),
    )


def _scenario_simulation_spec_from_record(
    record: ScenarioSimulationSpecRecord,
) -> ScenarioSimulationSpec:
    return ScenarioSimulationSpec(
        scenario_spec_id=record.scenario_spec_id,
        seed_bundle_id=record.seed_bundle_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        created_at=record.created_at,
        scenario_engine=ScenarioEngine(record.scenario_engine),
        scenario_goal=record.scenario_goal,
        horizon_hours=record.horizon_hours,
        requested_agent_count=record.requested_agent_count,
        requested_rounds=record.requested_rounds,
        variables=_metadata(record.variables),
        constraints=_metadata(record.constraints),
        metadata=_metadata(record.metadata_json),
    )


def _scenario_artifact_to_record(artifact: ScenarioArtifact) -> ScenarioArtifactRecord:
    return ScenarioArtifactRecord(
        scenario_artifact_id=artifact.scenario_artifact_id,
        scenario_spec_id=artifact.scenario_spec_id,
        seed_bundle_id=artifact.seed_bundle_id,
        market_id=artifact.market_id,
        asof_timestamp=artifact.asof_timestamp,
        captured_at=artifact.captured_at,
        available_at=artifact.available_at,
        artifact_type=artifact.artifact_type.value,
        source_type=artifact.source_type.value,
        source_path=artifact.source_path,
        raw_payload=_json_metadata(artifact.raw_payload),
        raw_text=artifact.raw_text,
        payload_hash=artifact.payload_hash,
        schema_version=artifact.schema_version,
        is_simulated=artifact.is_simulated,
        metadata_json=_json_metadata(artifact.metadata),
    )


def _scenario_artifact_from_record(record: ScenarioArtifactRecord) -> ScenarioArtifact:
    return ScenarioArtifact(
        scenario_artifact_id=record.scenario_artifact_id,
        scenario_spec_id=record.scenario_spec_id,
        seed_bundle_id=record.seed_bundle_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        captured_at=record.captured_at,
        available_at=record.available_at,
        artifact_type=ScenarioArtifactType(record.artifact_type),
        source_type=ScenarioArtifactSourceType(record.source_type),
        source_path=record.source_path,
        raw_payload=_metadata(record.raw_payload),
        raw_text=record.raw_text,
        payload_hash=record.payload_hash,
        schema_version=record.schema_version,
        is_simulated=record.is_simulated,
        metadata=_metadata(record.metadata_json),
    )


def _scenario_feature_snapshot_to_record(
    snapshot: ScenarioFeatureSnapshot,
) -> ScenarioFeatureSnapshotRecord:
    return ScenarioFeatureSnapshotRecord(
        scenario_feature_snapshot_id=snapshot.scenario_feature_snapshot_id,
        scenario_artifact_id=snapshot.scenario_artifact_id,
        seed_bundle_id=snapshot.seed_bundle_id,
        market_id=snapshot.market_id,
        asof_timestamp=snapshot.asof_timestamp,
        generated_at=snapshot.generated_at,
        available_at=snapshot.available_at,
        scenario_engine=snapshot.scenario_engine,
        horizon_hours=snapshot.horizon_hours,
        scenario_confidence_score=snapshot.scenario_confidence_score,
        scenario_uncertainty_score=snapshot.scenario_uncertainty_score,
        sentiment_score=snapshot.sentiment_score,
        consensus_score=snapshot.consensus_score,
        polarization_score=snapshot.polarization_score,
        narrative_risk_score=snapshot.narrative_risk_score,
        shock_risk_score=snapshot.shock_risk_score,
        adoption_or_support_score=snapshot.adoption_or_support_score,
        opposition_score=snapshot.opposition_score,
        key_scenario_labels=list(snapshot.key_scenario_labels),
        reason_codes=list(snapshot.reason_codes),
        evidence=_json_metadata(snapshot.evidence),
        source_ref_ids=list(snapshot.source_ref_ids),
        input_hash=snapshot.input_hash,
        output_hash=snapshot.output_hash,
        metadata_json=_json_metadata(snapshot.metadata),
    )


def _scenario_feature_snapshot_from_record(
    record: ScenarioFeatureSnapshotRecord,
) -> ScenarioFeatureSnapshot:
    return ScenarioFeatureSnapshot(
        scenario_feature_snapshot_id=record.scenario_feature_snapshot_id,
        scenario_artifact_id=record.scenario_artifact_id,
        seed_bundle_id=record.seed_bundle_id,
        market_id=record.market_id,
        asof_timestamp=record.asof_timestamp,
        generated_at=record.generated_at,
        available_at=record.available_at,
        scenario_engine=record.scenario_engine,
        horizon_hours=record.horizon_hours,
        scenario_confidence_score=record.scenario_confidence_score,
        scenario_uncertainty_score=record.scenario_uncertainty_score,
        sentiment_score=record.sentiment_score,
        consensus_score=record.consensus_score,
        polarization_score=record.polarization_score,
        narrative_risk_score=record.narrative_risk_score,
        shock_risk_score=record.shock_risk_score,
        adoption_or_support_score=record.adoption_or_support_score,
        opposition_score=record.opposition_score,
        key_scenario_labels=list(record.key_scenario_labels),
        reason_codes=list(record.reason_codes),
        evidence=_metadata(record.evidence),
        source_ref_ids=list(record.source_ref_ids),
        input_hash=record.input_hash,
        output_hash=record.output_hash,
        metadata=_metadata(record.metadata_json),
    )


def _scenario_run_to_record(run: ScenarioRun) -> ScenarioRunRecord:
    return ScenarioRunRecord(
        scenario_run_id=run.scenario_run_id,
        name=run.name,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        asof_timestamp=run.asof_timestamp,
        market_ids=list(run.market_ids),
        mode=run.mode.value,
        max_items=run.max_items,
        config_json=_json_metadata(run.config),
        metadata_json=_json_metadata(run.metadata),
        seed_bundles_created=run.seed_bundles_created,
        specs_created=run.specs_created,
        artifacts_imported=run.artifacts_imported,
        features_created=run.features_created,
        errors_count=run.errors_count,
    )


def _scenario_run_from_record(record: ScenarioRunRecord) -> ScenarioRun:
    return ScenarioRun(
        scenario_run_id=record.scenario_run_id,
        name=record.name,
        created_at=record.created_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        status=ScenarioRunStatus(record.status),
        asof_timestamp=record.asof_timestamp,
        market_ids=list(record.market_ids),
        mode=ScenarioRunMode(record.mode),
        max_items=record.max_items,
        config=_metadata(record.config_json),
        metadata=_metadata(record.metadata_json),
        seed_bundles_created=record.seed_bundles_created,
        specs_created=record.specs_created,
        artifacts_imported=record.artifacts_imported,
        features_created=record.features_created,
        errors_count=record.errors_count,
    )


def _scenario_run_summary_to_record(
    summary: ScenarioRunSummary,
) -> ScenarioRunSummaryRecord:
    return ScenarioRunSummaryRecord(
        summary_id=summary.summary_id,
        scenario_run_id=summary.scenario_run_id,
        created_at=summary.created_at,
        total_seed_bundles=summary.total_seed_bundles,
        total_artifacts=summary.total_artifacts,
        total_features=summary.total_features,
        average_scores={
            key: str(value) for key, value in summary.average_scores.items()
        },
        reason_code_counts=dict(summary.reason_code_counts),
        markets_processed=summary.markets_processed,
        metadata_json=_json_metadata(summary.metadata),
    )


def _scenario_run_summary_from_record(
    record: ScenarioRunSummaryRecord,
) -> ScenarioRunSummary:
    return ScenarioRunSummary(
        summary_id=record.summary_id,
        scenario_run_id=record.scenario_run_id,
        created_at=record.created_at,
        total_seed_bundles=record.total_seed_bundles,
        total_artifacts=record.total_artifacts,
        total_features=record.total_features,
        average_scores={
            key: Decimal(str(value)) for key, value in record.average_scores.items()
        },
        reason_code_counts=dict(record.reason_code_counts),
        markets_processed=record.markets_processed,
        metadata=_metadata(record.metadata_json),
    )


def _evidence_spans_to_json(spans: list[EvidenceSpan]) -> list[dict[str, Any]]:
    return [span.model_dump(mode="json") for span in spans]


def _evidence_spans_from_json(values: list[dict[str, Any]]) -> list[EvidenceSpan]:
    return [EvidenceSpan.model_validate(value) for value in values]


def _price_level_to_json(level: PriceLevel) -> dict[str, str]:
    return {"price": str(level.price), "quantity": str(level.quantity)}


def _price_level_from_json(value: dict[str, str]) -> PriceLevel:
    return PriceLevel(price=Decimal(value["price"]), quantity=Decimal(value["quantity"]))
