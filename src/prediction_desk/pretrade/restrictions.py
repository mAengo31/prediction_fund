"""Deterministic market restriction matching."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation

from prediction_desk.domain.models import Event, Market, Venue
from prediction_desk.pretrade.enums import PreTradeAction, RestrictionScopeType, RestrictionType
from prediction_desk.pretrade.models import MarketRestrictionRule

ACTION_RANK: dict[PreTradeAction, int] = {
    PreTradeAction.ALLOW: 0,
    PreTradeAction.ALLOW_SMALLER_SIZE: 1,
    PreTradeAction.PASSIVE_ONLY: 2,
    PreTradeAction.MANUAL_REVIEW: 3,
    PreTradeAction.NO_TRADE: 4,
}


@dataclass(frozen=True)
class RestrictionApplication:
    action: PreTradeAction
    max_allowed_size_units: Decimal
    hard_blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    restriction_ids: list[str] = field(default_factory=list)
    evidence: dict[str, object] = field(default_factory=dict)


def find_applicable_restrictions(
    market: Market,
    event: Event | None,
    venue: Venue | None,
    asof_timestamp: datetime,
    restrictions: list[MarketRestrictionRule],
) -> list[MarketRestrictionRule]:
    """Returns active restrictions that match the market context at the as-of time."""

    applicable = [
        rule
        for rule in restrictions
        if _active_asof(rule, asof_timestamp) and _matches_scope(rule, market, event, venue)
    ]
    return sorted(applicable, key=lambda rule: rule.restriction_id)


def apply_restrictions(
    current_action: PreTradeAction,
    restrictions: list[MarketRestrictionRule],
    requested_size_units: Decimal,
) -> RestrictionApplication:
    """Applies matched restrictions to the current action and requested size."""

    action = current_action
    max_size = requested_size_units
    hard_blockers: list[str] = []
    warnings: list[str] = []
    reason_codes: list[str] = []
    restriction_ids: list[str] = []
    evidence: dict[str, object] = {"applied_restrictions": []}
    applied = evidence["applied_restrictions"]
    assert isinstance(applied, list)
    for rule in sorted(restrictions, key=lambda item: item.restriction_id):
        restriction_ids.append(rule.restriction_id)
        reason_codes.append(rule.reason_code)
        applied.append(
            {
                "restriction_id": rule.restriction_id,
                "restriction_type": rule.restriction_type.value,
                "scope_type": rule.scope_type.value,
                "reason_code": rule.reason_code,
            }
        )
        if rule.restriction_type == RestrictionType.NO_TRADE:
            action = PreTradeAction.NO_TRADE
            hard_blockers.append(rule.reason_code)
        elif rule.restriction_type == RestrictionType.MANUAL_REVIEW:
            action = _max_action(action, PreTradeAction.MANUAL_REVIEW)
            warnings.append(rule.reason_code)
        elif rule.restriction_type == RestrictionType.PASSIVE_ONLY:
            action = _max_action(action, PreTradeAction.PASSIVE_ONLY)
            warnings.append(rule.reason_code)
        elif rule.restriction_type == RestrictionType.SIZE_LIMIT:
            parsed = _parse_size_limit(rule)
            if parsed is not None:
                max_size = min(max_size, parsed)
                if max_size < requested_size_units:
                    action = _max_action(action, PreTradeAction.ALLOW_SMALLER_SIZE)
                    warnings.append(rule.reason_code)
    return RestrictionApplication(
        action=action,
        max_allowed_size_units=max_size,
        hard_blockers=sorted(set(hard_blockers)),
        warnings=sorted(set(warnings)),
        reason_codes=sorted(set(reason_codes)),
        restriction_ids=sorted(set(restriction_ids)),
        evidence=evidence,
    )


def _active_asof(rule: MarketRestrictionRule, asof_timestamp: datetime) -> bool:
    if not rule.is_active:
        return False
    if rule.effective_from is not None and rule.effective_from > asof_timestamp:
        return False
    return not (
        rule.effective_until is not None and rule.effective_until < asof_timestamp
    )


def _matches_scope(
    rule: MarketRestrictionRule,
    market: Market,
    event: Event | None,
    venue: Venue | None,
) -> bool:
    if rule.scope_type == RestrictionScopeType.GLOBAL:
        return True
    if rule.scope_type == RestrictionScopeType.VENUE:
        return (
            (rule.venue_id is not None and rule.venue_id == market.venue_id)
            or (venue is not None and rule.venue_name is not None and rule.venue_name == venue.name)
        )
    if rule.scope_type == RestrictionScopeType.EVENT:
        return rule.event_id is not None and rule.event_id == market.event_id
    if rule.scope_type == RestrictionScopeType.MARKET:
        return rule.market_id is not None and rule.market_id == market.market_id
    if rule.scope_type == RestrictionScopeType.CATEGORY:
        categories = {market.metadata.get("category"), event.category if event else None}
        return rule.category is not None and rule.category in categories
    if rule.scope_type == RestrictionScopeType.TITLE_PATTERN:
        if not rule.title_pattern:
            return False
        target = f"{market.title} {event.title if event else ''}".casefold()
        return rule.title_pattern.casefold() in target
    return False


def _parse_size_limit(rule: MarketRestrictionRule) -> Decimal | None:
    value = rule.metadata.get("max_size_units")
    if value is None:
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return max(Decimal("0"), parsed)


def _max_action(left: PreTradeAction, right: PreTradeAction) -> PreTradeAction:
    return left if ACTION_RANK[left] >= ACTION_RANK[right] else right
