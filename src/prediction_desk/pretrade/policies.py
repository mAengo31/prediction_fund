"""Pre-trade policy defaults."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.pretrade.models import (
    DEFAULT_PRETRADE_POLICY_ID,
    DEFAULT_PRETRADE_POLICY_NAME,
    DEFAULT_PRETRADE_POLICY_VERSION,
    PreTradePolicy,
)


def build_default_pretrade_policy(
    *,
    created_at: datetime | None = None,
) -> PreTradePolicy:
    """Returns the deterministic conservative v1 default pre-trade policy."""

    return PreTradePolicy(
        policy_id=DEFAULT_PRETRADE_POLICY_ID,
        policy_name=DEFAULT_PRETRADE_POLICY_NAME,
        policy_version=DEFAULT_PRETRADE_POLICY_VERSION,
        created_at=created_at or datetime.now(tz=UTC),
        effective_from=None,
        effective_until=None,
        is_active=True,
        max_order_size_units=Decimal("1"),
        max_market_exposure_units=Decimal("5"),
        max_event_exposure_units=Decimal("10"),
        max_venue_exposure_units=Decimal("20"),
        max_strategy_exposure_units=None,
        allow_unknown_exposure=True,
        require_active_market=True,
        require_rule_snapshot=True,
        require_trust_verdict=False,
        require_market_data_quality=False,
        min_market_data_quality_score=60,
        max_resolution_risk_score=80,
        max_integrity_risk_score=80,
        max_divergence_score_without_review=70,
        max_staleness_seconds=3600,
        max_spread=Decimal("0.10"),
        max_spread_bps=Decimal("1000"),
        allow_manual_review_markets=False,
        allow_comparable_with_haircut=True,
        metadata={"policy_family": "pretrade_gate_v1"},
    )

