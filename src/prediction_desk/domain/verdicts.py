"""Trust verdict domain schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.domain.models import DomainModel


class TrustVerdict(DomainModel):
    verdict_id: str
    market_id: str
    asof_timestamp: datetime
    price_integrity_score: int = Field(ge=0, le=100)
    resolution_risk_score: int = Field(ge=0, le=100)
    liquidity_risk_score: int = Field(ge=0, le=100)
    cross_venue_consistency_score: int = Field(ge=0, le=100)
    information_freshness_score: int = Field(ge=0, le=100)
    manipulation_risk_score: int = Field(ge=0, le=100)
    action: VerdictAction
    reason_codes: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    model_versions: dict[str, Any] = Field(default_factory=dict)
    data_versions: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
