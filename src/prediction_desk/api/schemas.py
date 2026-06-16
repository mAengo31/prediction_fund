"""API response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from prediction_desk.domain.enums import MarketStatus, MarketType
from prediction_desk.domain.models import Market

SERVICE_NAME = "prediction-desk"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str


class ReadinessResponse(HealthResponse):
    database: str
    migrated: bool


class VersionResponse(BaseModel):
    service: str
    version: str
    commit: str | None
    environment: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class MarketSummary(BaseModel):
    market_id: str
    venue_id: str
    event_id: str
    title: str
    market_type: MarketType
    status: MarketStatus
    close_time: datetime | None
    settlement_time: datetime | None

    @classmethod
    def from_market(cls, market: Market) -> MarketSummary:
        return cls(
            market_id=market.market_id,
            venue_id=market.venue_id,
            event_id=market.event_id,
            title=market.title,
            market_type=market.market_type,
            status=market.status,
            close_time=market.close_time,
            settlement_time=market.settlement_time,
        )
