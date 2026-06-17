"""SQLAlchemy ORM mappings."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class VenueRecord(Base):
    __tablename__ = "venues"

    venue_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(128))
    venue_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class EventRecord(Base):
    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.venue_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(128))
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketRecord(Base):
    __tablename__ = "markets"

    market_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.venue_id"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.event_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    market_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    created_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    settlement_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class OutcomeRecord(Base):
    __tablename__ = "outcomes"

    outcome_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    payout: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketRuleSnapshotRecord(Base):
    __tablename__ = "market_rule_snapshots"

    rule_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    raw_rule_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_rule_text: Mapped[str | None] = mapped_column(Text)
    resolution_source: Mapped[str | None] = mapped_column(String(512))
    settlement_authority: Mapped[str | None] = mapped_column(String(512))
    time_zone: Mapped[str | None] = mapped_column(String(128))
    rule_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class OrderBookSnapshotRecord(Base):
    __tablename__ = "orderbook_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    bids: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    asks: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class TradePrintRecord(Base):
    __tablename__ = "trade_prints"

    trade_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResolutionEventRecord(Base):
    __tablename__ = "resolution_events"

    resolution_event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    result_label: Mapped[str | None] = mapped_column(String(256))
    resolution_source_url: Mapped[str | None] = mapped_column(String(1024))
    notes: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class TrustVerdictRecord(Base):
    __tablename__ = "trust_verdicts"

    verdict_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    price_integrity_score: Mapped[int] = mapped_column(nullable=False)
    resolution_risk_score: Mapped[int] = mapped_column(nullable=False)
    liquidity_risk_score: Mapped[int] = mapped_column(nullable=False)
    cross_venue_consistency_score: Mapped[int] = mapped_column(nullable=False)
    information_freshness_score: Mapped[int] = mapped_column(nullable=False)
    manipulation_risk_score: Mapped[int] = mapped_column(nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    model_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    data_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResolutionSourceRecord(Base):
    __tablename__ = "resolution_sources"

    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1024))
    jurisdiction: Mapped[str | None] = mapped_column(String(128))
    reliability_rank: Mapped[int | None] = mapped_column()
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResolutionPredicateRecord(Base):
    __tablename__ = "resolution_predicates"

    predicate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    rule_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    predicate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str | None] = mapped_column(Text)
    condition: Mapped[str | None] = mapped_column(Text)
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    threshold_unit: Mapped[str | None] = mapped_column(String(128))
    comparator: Mapped[str | None] = mapped_column(String(64))
    time_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    time_zone: Mapped[str | None] = mapped_column(String(128))
    resolution_source_id: Mapped[str | None] = mapped_column(
        ForeignKey("resolution_sources.source_id")
    )
    settlement_authority: Mapped[str | None] = mapped_column(String(512))
    confidence_score: Mapped[int] = mapped_column(nullable=False)
    evidence_spans: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    normalized_predicate_text: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class AmbiguityAssessmentRecord(Base):
    __tablename__ = "ambiguity_assessments"

    assessment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    rule_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id"), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    overall_score: Mapped[int] = mapped_column(nullable=False)
    source_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    temporal_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    definition_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    measurement_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    actor_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    threshold_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    dispute_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    exceptional_case_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    venue_adjudication_ambiguity_score: Mapped[int] = mapped_column(nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_spans: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class RuleSnapshotDiffRecord(Base):
    __tablename__ = "rule_snapshot_diffs"

    diff_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    from_rule_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id"), nullable=False, index=True
    )
    to_rule_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    raw_text_changed: Mapped[bool] = mapped_column(nullable=False)
    normalized_text_changed: Mapped[bool] = mapped_column(nullable=False)
    resolution_source_changed: Mapped[bool] = mapped_column(nullable=False)
    settlement_authority_changed: Mapped[bool] = mapped_column(nullable=False)
    time_zone_changed: Mapped[bool] = mapped_column(nullable=False)
    old_rule_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    new_rule_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_terms: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    added_text_fragments: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    removed_text_fragments: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    semantic_change_flags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ReplayRunRecord(Base):
    __tablename__ = "replay_runs"

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(nullable=False)
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_steps: Mapped[int] = mapped_column(nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ReplayStepRecord(Base):
    __tablename__ = "replay_steps"

    step_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("replay_runs.run_id"), nullable=False, index=True
    )
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    market_status: Mapped[str | None] = mapped_column(String(64))
    rule_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id")
    )
    rule_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    orderbook_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("orderbook_snapshots.snapshot_id")
    )
    resolution_predicate_id: Mapped[str | None] = mapped_column(
        ForeignKey("resolution_predicates.predicate_id")
    )
    ambiguity_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("ambiguity_assessments.assessment_id")
    )
    trust_verdict_id: Mapped[str | None] = mapped_column(ForeignKey("trust_verdicts.verdict_id"))
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    allowed_size_multiplier: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    price_integrity_score: Mapped[int | None] = mapped_column()
    resolution_risk_score: Mapped[int | None] = mapped_column()
    liquidity_risk_score: Mapped[int | None] = mapped_column()
    cross_venue_consistency_score: Mapped[int | None] = mapped_column()
    information_freshness_score: Mapped[int | None] = mapped_column()
    manipulation_risk_score: Mapped[int | None] = mapped_column()
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    error_code: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ReplayRunSummaryRecord(Base):
    __tablename__ = "replay_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("replay_runs.run_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_steps: Mapped[int] = mapped_column(nullable=False)
    errored_steps: Mapped[int] = mapped_column(nullable=False)
    action_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    average_scores: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    no_trade_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    manual_review_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    passive_only_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    allow_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    allowed_exposure_units: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    blocked_exposure_units: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    markets_replayed: Mapped[int] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class RawVenuePayloadRecord(Base):
    __tablename__ = "raw_venue_payloads"

    payload_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    endpoint_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(512), index=True)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source_url: Mapped[str | None] = mapped_column(String(2048))
    request_params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class VenueMarketMappingRecord(Base):
    __tablename__ = "venue_market_mappings"

    mapping_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    external_event_id: Mapped[str | None] = mapped_column(String(512))
    external_market_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    external_symbol: Mapped[str | None] = mapped_column(String(512))
    canonical_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("events.event_id"), index=True
    )
    canonical_market_id: Mapped[str | None] = mapped_column(
        ForeignKey("markets.market_id"), index=True
    )
    external_url: Mapped[str | None] = mapped_column(String(2048))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class IngestionRunRecord(Base):
    __tablename__ = "ingestion_runs"

    ingestion_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    endpoint_types: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    markets_seen: Mapped[int] = mapped_column(nullable=False)
    markets_created: Mapped[int] = mapped_column(nullable=False)
    markets_updated: Mapped[int] = mapped_column(nullable=False)
    rule_snapshots_created: Mapped[int] = mapped_column(nullable=False)
    orderbook_snapshots_created: Mapped[int] = mapped_column(nullable=False)
    price_snapshots_created: Mapped[int] = mapped_column(nullable=False, default=0)
    liquidity_snapshots_created: Mapped[int] = mapped_column(nullable=False, default=0)
    quality_reports_created: Mapped[int] = mapped_column(nullable=False, default=0)
    payloads_archived: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class IngestionErrorRecord(Base):
    __tablename__ = "ingestion_errors"

    error_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    ingestion_run_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_runs.ingestion_run_id"), nullable=False, index=True
    )
    venue_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    external_id: Mapped[str | None] = mapped_column(String(512), index=True)
    endpoint_type: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    error_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    payload_id: Mapped[str | None] = mapped_column(ForeignKey("raw_venue_payloads.payload_id"))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketPriceSnapshotRecord(Base):
    __tablename__ = "market_price_snapshots"

    price_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.venue_id"), nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    bid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    ask: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    mid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    last_trade_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    open_interest: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    source_payload_id: Mapped[str | None] = mapped_column(
        ForeignKey("raw_venue_payloads.payload_id")
    )
    orderbook_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("orderbook_snapshots.snapshot_id")
    )
    external_market_id: Mapped[str | None] = mapped_column(String(512), index=True)
    external_outcome_id: Mapped[str | None] = mapped_column(String(512))
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketLiquiditySnapshotRecord(Base):
    __tablename__ = "market_liquidity_snapshots"

    liquidity_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    venue_id: Mapped[str] = mapped_column(ForeignKey("venues.venue_id"), nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    best_bid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    best_ask: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    mid_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread_bps: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    bid_depth: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    ask_depth: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_bid_depth: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_ask_depth: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    book_imbalance: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    is_empty_book: Mapped[bool] = mapped_column(nullable=False)
    is_crossed_book: Mapped[bool] = mapped_column(nullable=False)
    source_payload_id: Mapped[str | None] = mapped_column(
        ForeignKey("raw_venue_payloads.payload_id")
    )
    orderbook_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("orderbook_snapshots.snapshot_id")
    )
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketDataQualityReportRecord(Base):
    __tablename__ = "market_data_quality_reports"

    quality_report_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_price_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_price_snapshots.price_snapshot_id")
    )
    latest_liquidity_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_liquidity_snapshots.liquidity_snapshot_id")
    )
    latest_orderbook_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("orderbook_snapshots.snapshot_id")
    )
    latest_rule_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id")
    )
    freshness_seconds: Mapped[int | None] = mapped_column()
    quality_score: Mapped[int] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    has_recent_price: Mapped[bool] = mapped_column(nullable=False)
    has_recent_orderbook: Mapped[bool] = mapped_column(nullable=False)
    has_rule_snapshot: Mapped[bool] = mapped_column(nullable=False)
    has_venue_mapping: Mapped[bool] = mapped_column(nullable=False)
    stale_market_data: Mapped[bool] = mapped_column(nullable=False)
    crossed_book: Mapped[bool] = mapped_column(nullable=False)
    empty_book: Mapped[bool] = mapped_column(nullable=False)
    wide_spread: Mapped[bool] = mapped_column(nullable=False)
    out_of_bounds_price: Mapped[bool] = mapped_column(nullable=False)
    missing_bid_or_ask: Mapped[bool] = mapped_column(nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class IngestionCursorRecord(Base):
    __tablename__ = "ingestion_cursors"

    cursor_id: Mapped[str] = mapped_column(String(256), primary_key=True)
    venue_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    venue_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    endpoint_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_market_id: Mapped[str | None] = mapped_column(String(512), index=True)
    canonical_market_id: Mapped[str | None] = mapped_column(
        ForeignKey("markets.market_id"), index=True
    )
    cursor_value: Mapped[str | None] = mapped_column(Text)
    last_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_available_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketFeatureSnapshotRecord(Base):
    __tablename__ = "market_feature_snapshots"

    feature_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    latest_price_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_price_snapshots.price_snapshot_id")
    )
    previous_price_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_price_snapshots.price_snapshot_id")
    )
    latest_liquidity_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_liquidity_snapshots.liquidity_snapshot_id")
    )
    previous_liquidity_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_liquidity_snapshots.liquidity_snapshot_id")
    )
    latest_quality_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_data_quality_reports.quality_report_id")
    )
    latest_rule_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id")
    )
    latest_rule_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    latest_rule_diff_id: Mapped[str | None] = mapped_column(
        ForeignKey("rule_snapshot_diffs.diff_id")
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    bid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    ask: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    mid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread_bps: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    total_bid_depth: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    total_ask_depth: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    total_depth: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    book_imbalance: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    is_empty_book: Mapped[bool] = mapped_column(nullable=False)
    is_crossed_book: Mapped[bool] = mapped_column(nullable=False)
    has_missing_bid_or_ask: Mapped[bool] = mapped_column(nullable=False)
    market_data_quality_score: Mapped[int | None] = mapped_column()
    market_data_quality_reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    freshness_seconds: Mapped[int | None] = mapped_column()
    price_change_abs: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    price_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    mid_change_abs: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread_change_abs: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    depth_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    rule_changed_recently: Mapped[bool] = mapped_column(nullable=False)
    rule_change_age_seconds: Mapped[int | None] = mapped_column()
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class IntegritySignalRecord(Base):
    __tablename__ = "integrity_signals"

    integrity_signal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    feature_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("market_feature_snapshots.feature_snapshot_id"),
        nullable=False,
        index=True,
    )
    signal_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signal_version: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[int] = mapped_column(nullable=False)
    action_hint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class IntegrityAssessmentRecord(Base):
    __tablename__ = "integrity_assessments"

    integrity_assessment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    feature_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("market_feature_snapshots.feature_snapshot_id"),
        nullable=False,
        index=True,
    )
    signal_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    overall_risk_score: Mapped[int] = mapped_column(nullable=False)
    price_anomaly_score: Mapped[int] = mapped_column(nullable=False)
    liquidity_anomaly_score: Mapped[int] = mapped_column(nullable=False)
    freshness_risk_score: Mapped[int] = mapped_column(nullable=False)
    orderbook_structure_score: Mapped[int] = mapped_column(nullable=False)
    rule_change_risk_score: Mapped[int] = mapped_column(nullable=False)
    rule_price_coupling_score: Mapped[int] = mapped_column(nullable=False)
    data_quality_risk_score: Mapped[int] = mapped_column(nullable=False)
    manipulation_proxy_score: Mapped[int] = mapped_column(nullable=False)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_hint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class IntegrityRunRecord(Base):
    __tablename__ = "integrity_runs"

    integrity_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interval_seconds: Mapped[int | None] = mapped_column()
    asof_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_steps: Mapped[int] = mapped_column(nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    assessments_created: Mapped[int] = mapped_column(nullable=False)
    signals_created: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)


class IntegrityRunSummaryRecord(Base):
    __tablename__ = "integrity_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    integrity_run_id: Mapped[str] = mapped_column(
        ForeignKey("integrity_runs.integrity_run_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_assessments: Mapped[int] = mapped_column(nullable=False)
    total_signals: Mapped[int] = mapped_column(nullable=False)
    severity_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    category_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    action_hint_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    average_scores: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    no_trade_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    manual_review_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    passive_only_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    allow_smaller_size_rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 6), nullable=False
    )
    markets_scanned: Mapped[int] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class EquivalenceCandidateRecord(Base):
    __tablename__ = "equivalence_candidates"

    candidate_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    left_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    right_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    candidate_score: Mapped[int] = mapped_column(nullable=False, index=True)
    candidate_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    left_venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    right_venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    title_similarity_score: Mapped[int] = mapped_column(nullable=False)
    category_match: Mapped[bool] = mapped_column(nullable=False)
    shared_tokens: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketEquivalenceAssessmentRecord(Base):
    __tablename__ = "market_equivalence_assessments"

    equivalence_assessment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    left_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    right_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    left_rule_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id")
    )
    right_rule_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_rule_snapshots.rule_snapshot_id")
    )
    left_rule_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    right_rule_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    left_resolution_predicate_id: Mapped[str | None] = mapped_column(
        ForeignKey("resolution_predicates.predicate_id")
    )
    right_resolution_predicate_id: Mapped[str | None] = mapped_column(
        ForeignKey("resolution_predicates.predicate_id")
    )
    left_ambiguity_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("ambiguity_assessments.assessment_id")
    )
    right_ambiguity_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("ambiguity_assessments.assessment_id")
    )
    left_venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    right_venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    comparison_permission: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    overall_score: Mapped[int] = mapped_column(nullable=False, index=True)
    confidence_score: Mapped[int] = mapped_column(nullable=False)
    title_similarity_score: Mapped[int] = mapped_column(nullable=False)
    event_identity_score: Mapped[int] = mapped_column(nullable=False)
    outcome_structure_score: Mapped[int] = mapped_column(nullable=False)
    outcome_mapping_score: Mapped[int] = mapped_column(nullable=False)
    predicate_similarity_score: Mapped[int] = mapped_column(nullable=False)
    resolution_source_score: Mapped[int] = mapped_column(nullable=False)
    settlement_authority_score: Mapped[int] = mapped_column(nullable=False)
    temporal_alignment_score: Mapped[int] = mapped_column(nullable=False)
    threshold_alignment_score: Mapped[int] = mapped_column(nullable=False)
    timezone_alignment_score: Mapped[int] = mapped_column(nullable=False)
    ambiguity_compatibility_score: Mapped[int] = mapped_column(nullable=False)
    venue_rule_compatibility_score: Mapped[int] = mapped_column(nullable=False)
    same_venue: Mapped[bool] = mapped_column(nullable=False)
    same_event_likely: Mapped[bool] = mapped_column(nullable=False)
    same_outcome_universe_likely: Mapped[bool] = mapped_column(nullable=False)
    inverse_outcome_likely: Mapped[bool] = mapped_column(nullable=False)
    resolution_source_mismatch: Mapped[bool] = mapped_column(nullable=False)
    settlement_authority_mismatch: Mapped[bool] = mapped_column(nullable=False)
    deadline_mismatch: Mapped[bool] = mapped_column(nullable=False)
    timezone_mismatch: Mapped[bool] = mapped_column(nullable=False)
    threshold_mismatch: Mapped[bool] = mapped_column(nullable=False)
    high_ambiguity: Mapped[bool] = mapped_column(nullable=False)
    insufficient_rule_data: Mapped[bool] = mapped_column(nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class OutcomeEquivalenceMappingRecord(Base):
    __tablename__ = "outcome_equivalence_mappings"

    outcome_mapping_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    equivalence_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("market_equivalence_assessments.equivalence_assessment_id"),
        nullable=False,
        index=True,
    )
    left_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    right_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    left_outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    right_outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    left_label: Mapped[str | None] = mapped_column(String(256))
    right_label: Mapped[str | None] = mapped_column(String(256))
    relation: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[int] = mapped_column(nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class EquivalenceClassRecord(Base):
    __tablename__ = "equivalence_classes"

    equivalence_class_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    representative_title: Mapped[str | None] = mapped_column(String(512))
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    assessment_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    min_pair_score: Mapped[int] = mapped_column(nullable=False)
    average_pair_score: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    confidence_score: Mapped[int] = mapped_column(nullable=False)
    comparison_permission: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class EquivalenceRunRecord(Base):
    __tablename__ = "equivalence_runs"

    equivalence_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    venue_names: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_pairs: Mapped[int] = mapped_column(nullable=False)
    min_candidate_score: Mapped[int] = mapped_column(nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    candidates_created: Mapped[int] = mapped_column(nullable=False)
    assessments_created: Mapped[int] = mapped_column(nullable=False)
    classes_created: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)


class EquivalenceRunSummaryRecord(Base):
    __tablename__ = "equivalence_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    equivalence_run_id: Mapped[str] = mapped_column(
        ForeignKey("equivalence_runs.equivalence_run_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_candidates: Mapped[int] = mapped_column(nullable=False)
    total_assessments: Mapped[int] = mapped_column(nullable=False)
    total_classes: Mapped[int] = mapped_column(nullable=False)
    status_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    permission_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    average_scores: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    comparable_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    manual_review_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    do_not_compare_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    markets_compared: Mapped[int] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class CrossVenueDivergenceSnapshotRecord(Base):
    __tablename__ = "cross_venue_divergence_snapshots"

    divergence_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    equivalence_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("market_equivalence_assessments.equivalence_assessment_id"),
        nullable=False,
        index=True,
    )
    outcome_mapping_id: Mapped[str | None] = mapped_column(
        ForeignKey("outcome_equivalence_mappings.outcome_mapping_id")
    )
    left_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    right_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    left_venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    right_venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    left_outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    right_outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    equivalence_status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    comparison_permission: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    equivalence_score: Mapped[int | None] = mapped_column()
    equivalence_confidence_score: Mapped[int | None] = mapped_column()
    outcome_relation: Mapped[str | None] = mapped_column(String(64), index=True)
    left_price_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_price_snapshots.price_snapshot_id")
    )
    right_price_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_price_snapshots.price_snapshot_id")
    )
    left_liquidity_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_liquidity_snapshots.liquidity_snapshot_id")
    )
    right_liquidity_snapshot_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_liquidity_snapshots.liquidity_snapshot_id")
    )
    left_quality_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_data_quality_reports.quality_report_id")
    )
    right_quality_report_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_data_quality_reports.quality_report_id")
    )
    left_integrity_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("integrity_assessments.integrity_assessment_id")
    )
    right_integrity_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("integrity_assessments.integrity_assessment_id")
    )
    left_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_price_raw: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_price_aligned: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    left_mid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_mid_raw: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_mid_aligned: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    left_bid: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    left_ask: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_bid_raw: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_ask_raw: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_bid_aligned: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_ask_aligned: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    signed_mid_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    absolute_mid_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    signed_price_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    absolute_price_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    gap_bps: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    combined_spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread_adjusted_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    left_spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    left_total_depth: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    right_total_depth: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    min_total_depth: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    left_quality_score: Mapped[int | None] = mapped_column()
    right_quality_score: Mapped[int | None] = mapped_column()
    left_integrity_risk_score: Mapped[int | None] = mapped_column()
    right_integrity_risk_score: Mapped[int | None] = mapped_column()
    stale_side: Mapped[str | None] = mapped_column(String(32))
    weaker_side: Mapped[str | None] = mapped_column(String(32))
    comparable: Mapped[bool] = mapped_column(nullable=False)
    comparable_with_haircut: Mapped[bool] = mapped_column(nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(nullable=False)
    do_not_compare: Mapped[bool] = mapped_column(nullable=False)
    missing_price_data: Mapped[bool] = mapped_column(nullable=False)
    missing_liquidity_data: Mapped[bool] = mapped_column(nullable=False)
    stale_data: Mapped[bool] = mapped_column(nullable=False)
    low_quality_data: Mapped[bool] = mapped_column(nullable=False)
    high_integrity_risk: Mapped[bool] = mapped_column(nullable=False)
    wide_spread: Mapped[bool] = mapped_column(nullable=False)
    one_sided_or_empty_book: Mapped[bool] = mapped_column(nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class CrossVenueDivergenceSignalRecord(Base):
    __tablename__ = "cross_venue_divergence_signals"

    divergence_signal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    divergence_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("cross_venue_divergence_snapshots.divergence_snapshot_id"),
        nullable=False,
        index=True,
    )
    equivalence_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("market_equivalence_assessments.equivalence_assessment_id"),
        nullable=False,
        index=True,
    )
    left_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    right_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    signal_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    signal_version: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[int] = mapped_column(nullable=False)
    action_hint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class CrossVenueDivergenceAssessmentRecord(Base):
    __tablename__ = "cross_venue_divergence_assessments"

    divergence_assessment_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    divergence_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("cross_venue_divergence_snapshots.divergence_snapshot_id"),
        nullable=False,
        index=True,
    )
    equivalence_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("market_equivalence_assessments.equivalence_assessment_id"),
        nullable=False,
        index=True,
    )
    outcome_mapping_id: Mapped[str | None] = mapped_column(
        ForeignKey("outcome_equivalence_mappings.outcome_mapping_id")
    )
    left_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    right_market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    signal_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    overall_divergence_score: Mapped[int] = mapped_column(nullable=False, index=True)
    price_divergence_score: Mapped[int] = mapped_column(nullable=False)
    spread_adjusted_score: Mapped[int] = mapped_column(nullable=False)
    persistence_score: Mapped[int] = mapped_column(nullable=False)
    stale_side_score: Mapped[int] = mapped_column(nullable=False)
    low_liquidity_score: Mapped[int] = mapped_column(nullable=False)
    low_data_quality_score: Mapped[int] = mapped_column(nullable=False)
    integrity_context_score: Mapped[int] = mapped_column(nullable=False)
    equivalence_context_score: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action_hint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    absolute_mid_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    spread_adjusted_gap: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    gap_bps: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    comparison_permission: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    equivalence_score: Mapped[int | None] = mapped_column()
    equivalence_confidence_score: Mapped[int | None] = mapped_column()
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class CrossVenueDivergenceRunRecord(Base):
    __tablename__ = "cross_venue_divergence_runs"

    divergence_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    equivalence_assessment_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_pairs: Mapped[int] = mapped_column(nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    snapshots_created: Mapped[int] = mapped_column(nullable=False)
    signals_created: Mapped[int] = mapped_column(nullable=False)
    assessments_created: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)


class CrossVenueDivergenceRunSummaryRecord(Base):
    __tablename__ = "cross_venue_divergence_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    divergence_run_id: Mapped[str] = mapped_column(
        ForeignKey("cross_venue_divergence_runs.divergence_run_id"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_snapshots: Mapped[int] = mapped_column(nullable=False)
    total_signals: Mapped[int] = mapped_column(nullable=False)
    total_assessments: Mapped[int] = mapped_column(nullable=False)
    status_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    severity_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    action_hint_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    average_scores: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    watch_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    material_divergence_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    needs_review_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    do_not_compare_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    markets_compared: Mapped[int] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class TradeIntentRecord(Base):
    __tablename__ = "trade_intents"

    trade_intent_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    strategy_context: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    intent_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    requested_notional_usd: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PreTradePolicyRecord(Base):
    __tablename__ = "pretrade_policies"

    policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(nullable=False, index=True)
    max_order_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    max_market_exposure_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    max_event_exposure_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    max_venue_exposure_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    max_strategy_exposure_units: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    allow_unknown_exposure: Mapped[bool] = mapped_column(nullable=False)
    require_active_market: Mapped[bool] = mapped_column(nullable=False)
    require_rule_snapshot: Mapped[bool] = mapped_column(nullable=False)
    require_trust_verdict: Mapped[bool] = mapped_column(nullable=False)
    require_market_data_quality: Mapped[bool] = mapped_column(nullable=False)
    min_market_data_quality_score: Mapped[int] = mapped_column(nullable=False)
    max_resolution_risk_score: Mapped[int] = mapped_column(nullable=False)
    max_integrity_risk_score: Mapped[int] = mapped_column(nullable=False)
    max_divergence_score_without_review: Mapped[int] = mapped_column(nullable=False)
    max_staleness_seconds: Mapped[int] = mapped_column(nullable=False)
    max_spread: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    max_spread_bps: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    allow_manual_review_markets: Mapped[bool] = mapped_column(nullable=False)
    allow_comparable_with_haircut: Mapped[bool] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class MarketRestrictionRuleRecord(Base):
    __tablename__ = "market_restriction_rules"

    restriction_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, index=True)
    restriction_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    venue_name: Mapped[str | None] = mapped_column(String(256), index=True)
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.market_id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.event_id"), index=True)
    category: Mapped[str | None] = mapped_column(String(128), index=True)
    title_pattern: Mapped[str | None] = mapped_column(String(512))
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ExposureSnapshotRecord(Base):
    __tablename__ = "exposure_snapshots"

    exposure_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market_id: Mapped[str | None] = mapped_column(ForeignKey("markets.market_id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.event_id"), index=True)
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    strategy_context: Mapped[str | None] = mapped_column(String(64), index=True)
    market_exposure_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    event_exposure_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    venue_exposure_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    strategy_exposure_units: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PreTradeInputSnapshotRecord(Base):
    __tablename__ = "pretrade_input_snapshots"

    input_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trade_intent_id: Mapped[str] = mapped_column(
        ForeignKey("trade_intents.trade_intent_id"), nullable=False, index=True
    )
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    market_status: Mapped[str | None] = mapped_column(String(64))
    event_id: Mapped[str | None] = mapped_column(String(128))
    venue_id: Mapped[str | None] = mapped_column(String(128))
    latest_rule_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    latest_rule_snapshot_hash: Mapped[str | None] = mapped_column(String(64))
    latest_trust_verdict_id: Mapped[str | None] = mapped_column(String(128))
    latest_quality_report_id: Mapped[str | None] = mapped_column(String(128))
    latest_integrity_assessment_id: Mapped[str | None] = mapped_column(String(128))
    latest_equivalence_assessment_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    latest_divergence_assessment_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    latest_price_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    latest_liquidity_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    exposure_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    restriction_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    resolution_risk_score: Mapped[int | None] = mapped_column()
    market_data_quality_score: Mapped[int | None] = mapped_column()
    integrity_risk_score: Mapped[int | None] = mapped_column()
    max_divergence_score: Mapped[int | None] = mapped_column()
    comparable_market_count: Mapped[int] = mapped_column(nullable=False)
    manual_review_equivalence_count: Mapped[int] = mapped_column(nullable=False)
    do_not_compare_equivalence_count: Mapped[int] = mapped_column(nullable=False)
    divergence_watch_count: Mapped[int] = mapped_column(nullable=False)
    material_divergence_count: Mapped[int] = mapped_column(nullable=False)
    divergence_needs_review_count: Mapped[int] = mapped_column(nullable=False)
    divergence_do_not_compare_count: Mapped[int] = mapped_column(nullable=False)
    current_market_exposure_units: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    current_event_exposure_units: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    current_venue_exposure_units: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    current_strategy_exposure_units: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PreTradeDecisionRecord(Base):
    __tablename__ = "pretrade_decisions"

    pretrade_decision_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trade_intent_id: Mapped[str] = mapped_column(
        ForeignKey("trade_intents.trade_intent_id"), nullable=False, index=True
    )
    input_snapshot_id: Mapped[str] = mapped_column(
        ForeignKey("pretrade_input_snapshots.input_snapshot_id"),
        nullable=False,
        index=True,
    )
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    policy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    allowed_size_multiplier: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    max_allowed_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_allowed_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    passive_only: Mapped[bool] = mapped_column(nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(nullable=False)
    hard_blocked: Mapped[bool] = mapped_column(nullable=False, index=True)
    composite_risk_score: Mapped[int] = mapped_column(nullable=False)
    resolution_risk_score: Mapped[int | None] = mapped_column()
    market_data_quality_score: Mapped[int | None] = mapped_column()
    integrity_risk_score: Mapped[int | None] = mapped_column()
    max_divergence_score: Mapped[int | None] = mapped_column()
    exposure_risk_score: Mapped[int | None] = mapped_column()
    hard_blockers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PreTradeRunRecord(Base):
    __tablename__ = "pretrade_runs"

    pretrade_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(String(128))
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_checks: Mapped[int] = mapped_column(nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    decisions_created: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)


class PreTradeRunSummaryRecord(Base):
    __tablename__ = "pretrade_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    pretrade_run_id: Mapped[str] = mapped_column(
        ForeignKey("pretrade_runs.pretrade_run_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_decisions: Mapped[int] = mapped_column(nullable=False)
    action_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    average_scores: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    no_trade_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    manual_review_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    passive_only_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    allow_smaller_size_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    allow_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    hard_block_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    total_requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_final_allowed_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperExecutionPolicyRecord(Base):
    __tablename__ = "paper_execution_policies"

    paper_policy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, index=True)
    allow_simulated_shorts: Mapped[bool] = mapped_column(nullable=False)
    allow_partial_fills: Mapped[bool] = mapped_column(nullable=False)
    default_fee_bps: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    max_slippage_bps: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    require_pretrade_allow: Mapped[bool] = mapped_column(nullable=False)
    allow_pretrade_allow_smaller_size: Mapped[bool] = mapped_column(nullable=False)
    allow_pretrade_passive_only_for_passive_orders: Mapped[bool] = mapped_column(nullable=False)
    reject_manual_review: Mapped[bool] = mapped_column(nullable=False)
    reject_no_trade: Mapped[bool] = mapped_column(nullable=False)
    fill_model: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperOrderRecord(Base):
    __tablename__ = "paper_orders"

    paper_order_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    trade_intent_id: Mapped[str] = mapped_column(
        ForeignKey("trade_intents.trade_intent_id"), nullable=False, index=True
    )
    pretrade_decision_id: Mapped[str | None] = mapped_column(
        ForeignKey("pretrade_decisions.pretrade_decision_id"), index=True
    )
    paper_policy_id: Mapped[str] = mapped_column(
        ForeignKey("paper_execution_policies.paper_policy_id"), nullable=False, index=True
    )
    simulation_run_id: Mapped[str | None] = mapped_column(String(128), index=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    outcome_id: Mapped[str | None] = mapped_column(ForeignKey("outcomes.outcome_id"))
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    intent_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    requested_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    limit_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    accepted_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    filled_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    remaining_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rejection_reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperFillRecord(Base):
    __tablename__ = "paper_fills"

    paper_fill_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    paper_order_id: Mapped[str] = mapped_column(
        ForeignKey("paper_orders.paper_order_id"), nullable=False, index=True
    )
    simulation_run_id: Mapped[str | None] = mapped_column(String(128), index=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    outcome_id: Mapped[str | None] = mapped_column(String(128))
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    filled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    fee_bps: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    liquidity_source: Mapped[str] = mapped_column(String(64), nullable=False)
    source_orderbook_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    source_price_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    source_liquidity_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    fill_reason: Mapped[str] = mapped_column(String(256), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperLedgerEntryRecord(Base):
    __tablename__ = "paper_ledger_entries"

    ledger_entry_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    simulation_run_id: Mapped[str | None] = mapped_column(String(128), index=True)
    paper_order_id: Mapped[str | None] = mapped_column(String(128), index=True)
    paper_fill_id: Mapped[str | None] = mapped_column(String(128), index=True)
    market_id: Mapped[str | None] = mapped_column(String(128), index=True)
    outcome_id: Mapped[str | None] = mapped_column(String(128))
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    entry_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    currency: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    is_simulated: Mapped[bool] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperPositionSnapshotRecord(Base):
    __tablename__ = "paper_position_snapshots"

    position_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    simulation_run_id: Mapped[str | None] = mapped_column(String(128), index=True)
    market_id: Mapped[str] = mapped_column(
        ForeignKey("markets.market_id"), nullable=False, index=True
    )
    outcome_id: Mapped[str | None] = mapped_column(String(128))
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    position_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    average_entry_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    cost_basis: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    realized_pnl_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    unrealized_pnl_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    mark_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    mark_price_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    is_flat: Mapped[bool] = mapped_column(nullable=False, index=True)
    is_simulated: Mapped[bool] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperPortfolioSnapshotRecord(Base):
    __tablename__ = "paper_portfolio_snapshots"

    portfolio_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    simulation_run_id: Mapped[str | None] = mapped_column(String(128), index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    cash_balance_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    gross_exposure_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    net_exposure_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    realized_pnl_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    unrealized_pnl_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_fees_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_equity_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    open_positions_count: Mapped[int] = mapped_column(nullable=False)
    closed_positions_count: Mapped[int] = mapped_column(nullable=False)
    is_simulated: Mapped[bool] = mapped_column(nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class PaperSimulationRunRecord(Base):
    __tablename__ = "paper_simulation_runs"

    simulation_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    paper_policy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(nullable=False)
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_orders: Mapped[int] = mapped_column(nullable=False)
    initial_cash_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    orders_created: Mapped[int] = mapped_column(nullable=False)
    fills_created: Mapped[int] = mapped_column(nullable=False)
    rejected_orders: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)


class PaperSimulationRunSummaryRecord(Base):
    __tablename__ = "paper_simulation_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    simulation_run_id: Mapped[str] = mapped_column(
        ForeignKey("paper_simulation_runs.simulation_run_id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_orders: Mapped[int] = mapped_column(nullable=False)
    filled_orders: Mapped[int] = mapped_column(nullable=False)
    partially_filled_orders: Mapped[int] = mapped_column(nullable=False)
    rejected_orders: Mapped[int] = mapped_column(nullable=False)
    total_fills: Mapped[int] = mapped_column(nullable=False)
    total_fees_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_cash_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_gross_exposure_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_net_exposure_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_realized_pnl_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_unrealized_pnl_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    final_total_equity_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    fill_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    rejection_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchStrategyDefinitionRecord(Base):
    __tablename__ = "research_strategy_definitions"

    strategy_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, index=True)
    family: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    requires_pretrade: Mapped[bool] = mapped_column(nullable=False)
    allows_paper_simulation: Mapped[bool] = mapped_column(nullable=False)
    default_requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    default_intent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    default_strategy_context: Mapped[str] = mapped_column(String(64), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchFeatureSnapshotRecord(Base):
    __tablename__ = "research_feature_snapshots"

    research_feature_snapshot_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    feature_source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    feature_family: Mapped[str] = mapped_column(String(64), nullable=False)
    source_ref_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    values_json: Mapped[dict[str, Any]] = mapped_column("values", JSON, nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchSignalRecord(Base):
    __tablename__ = "research_signals"

    research_signal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    signal_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signal_strength_score: Mapped[int] = mapped_column(nullable=False)
    confidence_score: Mapped[int] = mapped_column(nullable=False)
    action_bias: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_feature_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_ref_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchIntentProposalRecord(Base):
    __tablename__ = "research_intent_proposals"

    proposal_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    strategy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    research_signal_id: Mapped[str | None] = mapped_column(String(128), index=True)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    outcome_id: Mapped[str | None] = mapped_column(String(128))
    venue_id: Mapped[str | None] = mapped_column(String(128), index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    side: Mapped[str] = mapped_column(String(32), nullable=False)
    intent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    strategy_context: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    requested_notional_usd: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    pretrade_required: Mapped[bool] = mapped_column(nullable=False)
    paper_simulation_allowed: Mapped[bool] = mapped_column(nullable=False)
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    source_signal_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchDecisionTraceRecord(Base):
    __tablename__ = "research_decision_traces"

    trace_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    research_run_id: Mapped[str | None] = mapped_column(String(128), index=True)
    strategy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    asof_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    research_signal_id: Mapped[str | None] = mapped_column(String(128), index=True)
    proposal_id: Mapped[str | None] = mapped_column(String(128), index=True)
    trade_intent_id: Mapped[str | None] = mapped_column(String(128))
    pretrade_decision_id: Mapped[str | None] = mapped_column(String(128), index=True)
    paper_order_id: Mapped[str | None] = mapped_column(String(128), index=True)
    paper_fill_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    paper_position_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    paper_portfolio_snapshot_id: Mapped[str | None] = mapped_column(String(128))
    pretrade_action: Mapped[str | None] = mapped_column(String(64), index=True)
    paper_order_status: Mapped[str | None] = mapped_column(String(64), index=True)
    filled_size_units_simulated: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    avg_fill_price_simulated: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    reason_codes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchRunRecord(Base):
    __tablename__ = "research_runs"

    research_run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    interval_seconds: Mapped[int] = mapped_column(nullable=False)
    strategy_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    market_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    max_steps: Mapped[int] = mapped_column(nullable=False)
    max_proposals: Mapped[int] = mapped_column(nullable=False)
    enable_paper_simulation: Mapped[bool] = mapped_column(nullable=False)
    paper_policy_id: Mapped[str | None] = mapped_column(String(128))
    initial_cash_simulated: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    config_json: Mapped[dict[str, Any]] = mapped_column("config", JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
    signals_created: Mapped[int] = mapped_column(nullable=False)
    proposals_created: Mapped[int] = mapped_column(nullable=False)
    pretrade_checks_created: Mapped[int] = mapped_column(nullable=False)
    paper_orders_created: Mapped[int] = mapped_column(nullable=False)
    paper_fills_created: Mapped[int] = mapped_column(nullable=False)
    errors_count: Mapped[int] = mapped_column(nullable=False)


class ResearchRunSummaryRecord(Base):
    __tablename__ = "research_run_summaries"

    summary_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_steps: Mapped[int] = mapped_column(nullable=False)
    total_signals: Mapped[int] = mapped_column(nullable=False)
    total_proposals: Mapped[int] = mapped_column(nullable=False)
    total_pretrade_checks: Mapped[int] = mapped_column(nullable=False)
    total_paper_orders: Mapped[int] = mapped_column(nullable=False)
    total_paper_fills: Mapped[int] = mapped_column(nullable=False)
    strategy_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    signal_type_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    pretrade_action_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    paper_order_status_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    reason_code_counts: Mapped[dict[str, int]] = mapped_column(JSON, nullable=False)
    average_scores: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False)
    total_requested_size_units: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_pretrade_allowed_size_units: Mapped[Decimal] = mapped_column(
        Numeric(30, 10), nullable=False
    )
    total_filled_size_units_simulated: Mapped[Decimal] = mapped_column(
        Numeric(30, 10), nullable=False
    )
    final_portfolio_equity_simulated: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    final_realized_pnl_simulated: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    final_unrealized_pnl_simulated: Mapped[Decimal | None] = mapped_column(Numeric(30, 10))
    proposal_to_pretrade_pass_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    paper_fill_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)


class ResearchAttributionReportRecord(Base):
    __tablename__ = "research_attribution_reports"

    attribution_report_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    research_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    by_strategy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    by_market: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    by_venue: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    by_reason_code: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    by_signal_type: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    by_pretrade_action: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    by_paper_order_status: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    simulated_pnl_by_strategy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    simulated_pnl_by_market: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)
