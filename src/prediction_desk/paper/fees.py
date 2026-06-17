"""Deterministic simulated fee helpers."""

from __future__ import annotations

from decimal import Decimal

from prediction_desk.paper.models import PaperExecutionPolicy


def compute_simulated_fee(notional: Decimal, fee_bps: Decimal) -> Decimal:
    """Returns a simulated fee amount from configurable basis points."""

    return (notional * fee_bps / Decimal("10000")).quantize(Decimal("0.0000000001"))


def get_fee_bps_for_venue(
    policy: PaperExecutionPolicy,
    venue_id: str | None = None,
    venue_name: str | None = None,
) -> Decimal:
    """Returns configured simulated fee bps, optionally overridden in metadata."""

    del venue_name
    venue_fee_bps = policy.metadata.get("venue_fee_bps", {})
    if venue_id is not None and isinstance(venue_fee_bps, dict) and venue_id in venue_fee_bps:
        return Decimal(str(venue_fee_bps[venue_id]))
    return policy.default_fee_bps

