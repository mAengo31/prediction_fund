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
