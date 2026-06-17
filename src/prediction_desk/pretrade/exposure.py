"""Abstract exposure checks for the pre-trade gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction
from prediction_desk.pretrade.models import ExposureSnapshot, PreTradePolicy, TradeIntent


@dataclass(frozen=True)
class ExposureEvaluation:
    action: PreTradeAction
    max_allowed_size_units: Decimal
    exposure_risk_score: int
    hard_blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    evidence: dict[str, object] = field(default_factory=dict)


def get_latest_exposure_asof(
    repo: PredictionMarketRepository,
    *,
    market_id: str | None,
    event_id: str | None,
    venue_id: str | None,
    strategy_context: str | None,
    asof_timestamp: datetime,
) -> ExposureSnapshot | None:
    return repo.get_latest_exposure_snapshot_asof(
        market_id=market_id,
        event_id=event_id,
        venue_id=venue_id,
        strategy_context=strategy_context,
        asof_timestamp=asof_timestamp,
    )


def evaluate_exposure_limits(
    intent: TradeIntent,
    policy: PreTradePolicy,
    exposure_snapshot: ExposureSnapshot | None,
) -> ExposureEvaluation:
    requested = intent.requested_size_units
    max_allowed = min(requested, policy.max_order_size_units)
    action = PreTradeAction.ALLOW
    warnings: list[str] = []
    hard_blockers: list[str] = []
    reason_codes: list[str] = []
    evidence: dict[str, object] = {
        "requested_size_units": str(requested),
        "max_order_size_units": str(policy.max_order_size_units),
    }
    exposure_risk = 0
    if max_allowed < requested:
        action = PreTradeAction.ALLOW_SMALLER_SIZE
        warnings.append("MAX_ORDER_SIZE_REDUCED")
        reason_codes.append("MAX_ORDER_SIZE_REDUCED")
        exposure_risk = max(exposure_risk, 40)

    if exposure_snapshot is None:
        if policy.allow_unknown_exposure:
            warnings.append("UNKNOWN_EXPOSURE_ALLOWED_BY_POLICY")
            reason_codes.append("UNKNOWN_EXPOSURE_ALLOWED_BY_POLICY")
            exposure_risk = max(exposure_risk, 20)
            return ExposureEvaluation(
                action=action,
                max_allowed_size_units=max_allowed,
                exposure_risk_score=exposure_risk,
                hard_blockers=hard_blockers,
                warnings=sorted(set(warnings)),
                reason_codes=sorted(set(reason_codes)),
                evidence=evidence,
            )
        return ExposureEvaluation(
            action=PreTradeAction.MANUAL_REVIEW,
            max_allowed_size_units=Decimal("0"),
            exposure_risk_score=70,
            hard_blockers=[],
            warnings=["MISSING_EXPOSURE_SNAPSHOT"],
            reason_codes=["MISSING_EXPOSURE_SNAPSHOT"],
            evidence=evidence,
        )

    capacities = {
        "market": policy.max_market_exposure_units - exposure_snapshot.market_exposure_units,
        "event": policy.max_event_exposure_units - exposure_snapshot.event_exposure_units,
        "venue": policy.max_venue_exposure_units - exposure_snapshot.venue_exposure_units,
    }
    if (
        policy.max_strategy_exposure_units is not None
        and exposure_snapshot.strategy_exposure_units is not None
    ):
        capacities["strategy"] = (
            policy.max_strategy_exposure_units - exposure_snapshot.strategy_exposure_units
        )
    evidence["remaining_capacity_units"] = {
        key: str(value) for key, value in sorted(capacities.items())
    }
    positive_capacities = [max(Decimal("0"), value) for value in capacities.values()]
    remaining = min(positive_capacities) if positive_capacities else Decimal("0")
    if remaining <= Decimal("0"):
        hard_blockers.append("EXPOSURE_LIMIT_BREACH")
        reason_codes.append("EXPOSURE_LIMIT_BREACH")
        return ExposureEvaluation(
            action=PreTradeAction.NO_TRADE,
            max_allowed_size_units=Decimal("0"),
            exposure_risk_score=100,
            hard_blockers=hard_blockers,
            warnings=warnings,
            reason_codes=reason_codes,
            evidence=evidence,
        )
    if remaining < max_allowed:
        max_allowed = remaining
        action = PreTradeAction.ALLOW_SMALLER_SIZE
        warnings.append("EXPOSURE_CAP_REDUCED_SIZE")
        reason_codes.append("EXPOSURE_CAP_REDUCED_SIZE")
        exposure_risk = max(exposure_risk, 60)
    if max_allowed < requested and "MAX_ORDER_SIZE_REDUCED" not in reason_codes:
        action = PreTradeAction.ALLOW_SMALLER_SIZE
    return ExposureEvaluation(
        action=action,
        max_allowed_size_units=max_allowed,
        exposure_risk_score=exposure_risk,
        hard_blockers=sorted(set(hard_blockers)),
        warnings=sorted(set(warnings)),
        reason_codes=sorted(set(reason_codes)),
        evidence=evidence,
    )

