from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from prediction_desk.domain.enums import MarketStatus, MarketType, VenueType
from prediction_desk.domain.models import (
    Market,
    MarketRuleSnapshot,
    Outcome,
    PriceLevel,
    Venue,
    compute_rule_hash,
)


def test_rule_hash_is_deterministic() -> None:
    fields = {
        "raw_rule_text": "Resolve from source A on 2026-09-01.",
        "normalized_rule_text": "source A, 2026-09-01",
        "resolution_source": "source A",
        "settlement_authority": "committee",
        "time_zone": "UTC",
    }

    first = compute_rule_hash(**fields)
    second = compute_rule_hash(**dict(reversed(list(fields.items()))))
    changed = compute_rule_hash(**{**fields, "time_zone": "America/New_York"})

    assert first == second
    assert first != changed
    assert len(first) == 64


def test_rule_snapshot_factory_uses_canonical_hash() -> None:
    snapshot = MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id="rule_1",
        market_id="market_1",
        captured_at=datetime(2026, 6, 16, tzinfo=UTC),
        raw_rule_text="Resolve YES on a precise source.",
        normalized_rule_text=None,
        resolution_source="Precise source",
        settlement_authority="Research desk",
        time_zone="UTC",
    )

    assert snapshot.rule_hash == compute_rule_hash(
        raw_rule_text=snapshot.raw_rule_text,
        normalized_rule_text=snapshot.normalized_rule_text,
        resolution_source=snapshot.resolution_source,
        settlement_authority=snapshot.settlement_authority,
        time_zone=snapshot.time_zone,
    )


def test_domain_model_validation() -> None:
    venue = Venue(
        venue_id="venue_1",
        name="Venue",
        venue_type=VenueType.OTHER,
    )
    market = Market(
        market_id="market_1",
        venue_id=venue.venue_id,
        event_id="event_1",
        title="Will a clearly defined event occur?",
        market_type=MarketType.BINARY,
        status=MarketStatus.ACTIVE,
    )
    outcome = Outcome(
        outcome_id="outcome_1",
        market_id=market.market_id,
        label="YES",
        payout=Decimal("1"),
    )
    level = PriceLevel(price=Decimal("0.50"), quantity=Decimal("10"))

    assert market.status is MarketStatus.ACTIVE
    assert outcome.payout == Decimal("1")
    assert level.quantity == Decimal("10")

    with pytest.raises(ValidationError):
        PriceLevel(price=Decimal("0.50"), quantity=Decimal("0"))
