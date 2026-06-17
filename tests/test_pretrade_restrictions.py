from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.pretrade.enums import (
    PreTradeAction,
    RestrictionScopeType,
    RestrictionType,
)
from prediction_desk.pretrade.models import MarketRestrictionRule
from prediction_desk.pretrade.restrictions import (
    apply_restrictions,
    find_applicable_restrictions,
)

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def test_no_trade_restriction_hard_blocks() -> None:
    rule = _rule(RestrictionType.NO_TRADE, RestrictionScopeType.GLOBAL, "GLOBAL_BLOCK")

    result = apply_restrictions(PreTradeAction.ALLOW, [rule], Decimal("1"))

    assert result.action == PreTradeAction.NO_TRADE
    assert "GLOBAL_BLOCK" in result.hard_blockers


def test_manual_review_and_passive_only_restrictions_force_actions() -> None:
    manual = _rule(
        RestrictionType.MANUAL_REVIEW,
        RestrictionScopeType.GLOBAL,
        "GLOBAL_REVIEW",
    )
    passive = _rule(
        RestrictionType.PASSIVE_ONLY,
        RestrictionScopeType.GLOBAL,
        "GLOBAL_PASSIVE",
    )

    assert (
        apply_restrictions(PreTradeAction.ALLOW, [manual], Decimal("1")).action
        == PreTradeAction.MANUAL_REVIEW
    )
    assert (
        apply_restrictions(PreTradeAction.ALLOW, [passive], Decimal("1")).action
        == PreTradeAction.PASSIVE_ONLY
    )


def test_size_limit_restriction_reduces_size() -> None:
    rule = _rule(
        RestrictionType.SIZE_LIMIT,
        RestrictionScopeType.GLOBAL,
        "GLOBAL_SIZE_LIMIT",
        metadata={"max_size_units": "0.25"},
    )

    result = apply_restrictions(PreTradeAction.ALLOW, [rule], Decimal("1"))

    assert result.action == PreTradeAction.ALLOW_SMALLER_SIZE
    assert result.max_allowed_size_units == Decimal("0.25")


def test_find_applicable_restrictions_respects_scope_and_effective_time() -> None:
    clean, *_ = sample_markets()
    active = _rule(
        RestrictionType.NO_TRADE,
        RestrictionScopeType.MARKET,
        "MARKET_BLOCK",
        market_id=clean.market.market_id,
    )
    future = _rule(
        RestrictionType.NO_TRADE,
        RestrictionScopeType.MARKET,
        "FUTURE_BLOCK",
        market_id=clean.market.market_id,
        effective_from=datetime(2026, 6, 17, tzinfo=UTC),
    )

    applicable = find_applicable_restrictions(
        clean.market,
        clean.event,
        clean.venue,
        ASOF,
        [active, future],
    )

    assert [rule.reason_code for rule in applicable] == ["MARKET_BLOCK"]


def _rule(
    restriction_type: RestrictionType,
    scope_type: RestrictionScopeType,
    reason_code: str,
    *,
    market_id: str | None = None,
    effective_from: datetime | None = None,
    metadata: dict[str, object] | None = None,
) -> MarketRestrictionRule:
    return MarketRestrictionRule(
        restriction_id=f"restriction_{reason_code}",
        created_at=ASOF,
        is_active=True,
        restriction_type=restriction_type,
        scope_type=scope_type,
        market_id=market_id,
        reason_code=reason_code,
        effective_from=effective_from,
        metadata=metadata or {},
    )
