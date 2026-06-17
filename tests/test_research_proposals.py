from __future__ import annotations

from decimal import Decimal

from prediction_desk.divergence.models import CrossVenueDivergenceSnapshot
from prediction_desk.pretrade.enums import TradeIntentType, TradeSide
from prediction_desk.research.proposals import (
    choose_lower_aligned_price_side_from_divergence,
    proposal_to_trade_intent,
    validate_research_proposal,
)
from tests.paper_helpers import MARKET_ID
from tests.research_helpers import ASOF, research_proposal


def test_proposal_converts_to_trade_intent() -> None:
    proposal = research_proposal(
        requested_price=Decimal("0.52"),
        requested_size_units=Decimal("1.5"),
        intent_type=TradeIntentType.AGGRESSIVE_LIMIT.value,
    )
    intent = proposal_to_trade_intent(proposal)

    assert intent.market_id == proposal.market_id
    assert intent.side == TradeSide.BUY
    assert intent.intent_type == TradeIntentType.AGGRESSIVE_LIMIT
    assert intent.requested_price == Decimal("0.52")
    assert intent.metadata["proposal_id"] == proposal.proposal_id


def test_proposal_validation_reports_invalid_constructed_values() -> None:
    proposal = research_proposal().model_copy(
        update={
            "requested_size_units": Decimal("0"),
            "requested_price": Decimal("1.20"),
            "pretrade_required": False,
        }
    )

    assert validate_research_proposal(proposal) == [
        "INVALID_REQUESTED_SIZE",
        "INVALID_REQUESTED_PRICE",
        "PRETRADE_REQUIRED_FOR_RESEARCH_PROPOSAL",
    ]


def test_lower_aligned_side_helper_uses_aligned_prices_only() -> None:
    snapshot = CrossVenueDivergenceSnapshot(
        divergence_snapshot_id="divergence_snapshot_test",
        equivalence_assessment_id="equivalence_assessment_test",
        left_market_id=MARKET_ID,
        right_market_id="right_market",
        left_venue_id="left_venue",
        right_venue_id="right_venue",
        asof_timestamp=ASOF,
        generated_at=ASOF,
        available_at=ASOF,
        equivalence_status="EQUIVALENT",
        comparison_permission="COMPARABLE",
        outcome_relation="SAME",
        left_price=Decimal("0.40"),
        right_price_aligned=Decimal("0.55"),
        left_mid=Decimal("0.40"),
        right_mid_aligned=Decimal("0.55"),
        comparable=True,
        input_hash="input",
        output_hash="output",
    )

    lower = choose_lower_aligned_price_side_from_divergence(snapshot)

    assert lower.market_id == MARKET_ID
    assert lower.reference_price == Decimal("0.40")
    assert lower.reason_codes == ["LEFT_SIDE_LOWER_ALIGNED_PRICE"]

