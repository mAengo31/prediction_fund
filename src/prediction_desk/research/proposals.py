"""Research proposal utilities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from prediction_desk.divergence.models import CrossVenueDivergenceSnapshot
from prediction_desk.pretrade.enums import StrategyContext, TradeIntentType, TradeSide
from prediction_desk.pretrade.models import TradeIntent, compute_trade_intent_id
from prediction_desk.research.models import ResearchIntentProposal


@dataclass(frozen=True)
class LowerAlignedSide:
    market_id: str | None
    venue_id: str | None
    outcome_id: str | None
    side: TradeSide
    reference_price: Decimal | None
    reason_codes: list[str]


def proposal_to_trade_intent(proposal: ResearchIntentProposal) -> TradeIntent:
    intent = TradeIntent(
        trade_intent_id="pending",
        market_id=proposal.market_id,
        outcome_id=proposal.outcome_id,
        venue_id=proposal.venue_id,
        strategy_context=StrategyContext(proposal.strategy_context),
        side=proposal.side,
        intent_type=TradeIntentType(proposal.intent_type),
        requested_price=proposal.requested_price,
        requested_size_units=proposal.requested_size_units,
        requested_notional_usd=proposal.requested_notional_usd,
        asof_timestamp=proposal.asof_timestamp,
        metadata={
            "source": "research_intent_proposal_v1",
            "proposal_id": proposal.proposal_id,
            "strategy_id": proposal.strategy_id,
            **proposal.metadata,
        },
    )
    return intent.model_copy(update={"trade_intent_id": compute_trade_intent_id(intent)})


def validate_research_proposal(proposal: ResearchIntentProposal) -> list[str]:
    reason_codes: list[str] = []
    if proposal.requested_size_units <= Decimal("0"):
        reason_codes.append("INVALID_REQUESTED_SIZE")
    if proposal.requested_price is not None and not (
        Decimal("0") <= proposal.requested_price <= Decimal("1")
    ):
        reason_codes.append("INVALID_REQUESTED_PRICE")
    if not proposal.pretrade_required:
        reason_codes.append("PRETRADE_REQUIRED_FOR_RESEARCH_PROPOSAL")
    return reason_codes


def choose_lower_aligned_price_side_from_divergence(
    snapshot: CrossVenueDivergenceSnapshot,
) -> LowerAlignedSide:
    left = snapshot.left_mid if snapshot.left_mid is not None else snapshot.left_price
    right = (
        snapshot.right_mid_aligned
        if snapshot.right_mid_aligned is not None
        else snapshot.right_price_aligned
    )
    if left is None or right is None:
        return LowerAlignedSide(
            market_id=None,
            venue_id=None,
            outcome_id=None,
            side=TradeSide.UNKNOWN,
            reference_price=None,
            reason_codes=["LOWER_SIDE_UNDETERMINED"],
        )
    if left < right:
        return LowerAlignedSide(
            market_id=snapshot.left_market_id,
            venue_id=snapshot.left_venue_id,
            outcome_id=snapshot.left_outcome_id,
            side=TradeSide.BUY,
            reference_price=left,
            reason_codes=["LEFT_SIDE_LOWER_ALIGNED_PRICE"],
        )
    if right < left:
        return LowerAlignedSide(
            market_id=snapshot.right_market_id,
            venue_id=snapshot.right_venue_id,
            outcome_id=snapshot.right_outcome_id,
            side=TradeSide.BUY,
            reference_price=right,
            reason_codes=["RIGHT_SIDE_LOWER_ALIGNED_PRICE"],
        )
    return LowerAlignedSide(
        market_id=None,
        venue_id=None,
        outcome_id=None,
        side=TradeSide.UNKNOWN,
        reference_price=None,
        reason_codes=["ALIGNED_PRICES_TIED"],
    )
