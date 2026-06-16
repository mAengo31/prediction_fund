"""Pydantic domain schemas for point-in-time prediction-market data."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from prediction_desk.domain.enums import MarketStatus, MarketType, TradeSide, VenueType


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Venue(DomainModel):
    venue_id: str
    name: str
    jurisdiction: str | None = None
    venue_type: VenueType
    metadata: dict[str, Any] = Field(default_factory=dict)


class Event(DomainModel):
    event_id: str
    venue_id: str
    title: str
    category: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Market(DomainModel):
    market_id: str
    venue_id: str
    event_id: str
    title: str
    description: str | None = None
    market_type: MarketType
    status: MarketStatus
    created_time: datetime | None = None
    close_time: datetime | None = None
    settlement_time: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Outcome(DomainModel):
    outcome_id: str
    market_id: str
    label: str
    payout: Decimal = Field(ge=Decimal("0"))
    metadata: dict[str, Any] = Field(default_factory=dict)


def compute_rule_hash(
    *,
    raw_rule_text: str,
    normalized_rule_text: str | None,
    resolution_source: str | None,
    settlement_authority: str | None,
    time_zone: str | None,
) -> str:
    """Compute a deterministic SHA-256 hash for a market-rule snapshot."""

    payload = {
        "normalized_rule_text": normalized_rule_text,
        "raw_rule_text": raw_rule_text,
        "resolution_source": resolution_source,
        "settlement_authority": settlement_authority,
        "time_zone": time_zone,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class MarketRuleSnapshot(DomainModel):
    rule_snapshot_id: str
    market_id: str
    captured_at: datetime
    raw_rule_text: str
    normalized_rule_text: str | None = None
    resolution_source: str | None = None
    settlement_authority: str | None = None
    time_zone: str | None = None
    rule_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_rule_text(
        cls,
        *,
        rule_snapshot_id: str,
        market_id: str,
        captured_at: datetime,
        raw_rule_text: str,
        normalized_rule_text: str | None = None,
        resolution_source: str | None = None,
        settlement_authority: str | None = None,
        time_zone: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MarketRuleSnapshot:
        rule_hash = compute_rule_hash(
            raw_rule_text=raw_rule_text,
            normalized_rule_text=normalized_rule_text,
            resolution_source=resolution_source,
            settlement_authority=settlement_authority,
            time_zone=time_zone,
        )
        return cls(
            rule_snapshot_id=rule_snapshot_id,
            market_id=market_id,
            captured_at=captured_at,
            raw_rule_text=raw_rule_text,
            normalized_rule_text=normalized_rule_text,
            resolution_source=resolution_source,
            settlement_authority=settlement_authority,
            time_zone=time_zone,
            rule_hash=rule_hash,
            metadata=metadata or {},
        )


class PriceLevel(DomainModel):
    price: Decimal = Field(ge=Decimal("0"))
    quantity: Decimal = Field(gt=Decimal("0"))


class OrderBookSnapshot(DomainModel):
    snapshot_id: str
    market_id: str
    captured_at: datetime
    bids: list[PriceLevel] = Field(default_factory=list)
    asks: list[PriceLevel] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradePrint(DomainModel):
    trade_id: str
    market_id: str
    executed_at: datetime
    price: Decimal = Field(ge=Decimal("0"))
    quantity: Decimal = Field(gt=Decimal("0"))
    side: TradeSide
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolutionEvent(DomainModel):
    resolution_event_id: str
    market_id: str
    resolved_at: datetime
    outcome_id: str | None = None
    result_label: str | None = None
    resolution_source_url: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
