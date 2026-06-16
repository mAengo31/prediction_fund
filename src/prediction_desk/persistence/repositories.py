"""Repository methods for canonical market research objects."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

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
from prediction_desk.persistence.orm import (
    EventRecord,
    MarketRecord,
    MarketRuleSnapshotRecord,
    OrderBookSnapshotRecord,
    OutcomeRecord,
    ResolutionEventRecord,
    TradePrintRecord,
    TrustVerdictRecord,
    VenueRecord,
)


class PredictionMarketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def save_venue(self, venue: Venue) -> Venue:
        self.session.merge(_venue_to_record(venue))
        self.session.flush()
        return venue

    def save_event(self, event: Event) -> Event:
        self.session.merge(_event_to_record(event))
        self.session.flush()
        return event

    def create_market(self, market: Market) -> Market:
        self.session.merge(_market_to_record(market))
        self.session.flush()
        return market

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

    def save_rule_snapshot(self, snapshot: MarketRuleSnapshot) -> MarketRuleSnapshot:
        self.session.merge(_rule_snapshot_to_record(snapshot))
        self.session.flush()
        return snapshot

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


def _metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    return dict(value or {})


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


def _price_level_to_json(level: PriceLevel) -> dict[str, str]:
    return {"price": str(level.price), "quantity": str(level.quantity)}


def _price_level_from_json(value: dict[str, str]) -> PriceLevel:
    return PriceLevel(price=Decimal(value["price"]), quantity=Decimal(value["quantity"]))
