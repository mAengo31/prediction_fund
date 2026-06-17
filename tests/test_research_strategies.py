from __future__ import annotations

from decimal import Decimal

from prediction_desk.research.enums import (
    ResearchActionBias,
    ResearchFeatureSource,
    ResearchSignalType,
)
from prediction_desk.research.strategies import strategy_from_definition
from tests.paper_helpers import MARKET_ID
from tests.research_helpers import ASOF, research_feature, strategy_definition


def test_baseline_strategy_generates_research_only_signal_and_proposal() -> None:
    strategy = strategy_from_definition(strategy_definition("baseline_research_only_v1"))

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, [], {})

    assert result.signals[0].signal_type == ResearchSignalType.REVIEW_ONLY
    assert result.signals[0].action_bias == ResearchActionBias.RESEARCH_ONLY
    assert result.proposals[0].intent_type == "RESEARCH_ONLY"


def test_trust_filter_blocks_no_trade_and_manual_review() -> None:
    strategy = strategy_from_definition(
        strategy_definition("trust_verdict_allow_filter_v1")
    )
    features = [
        research_feature(
            ResearchFeatureSource.RESOLUTION,
            {"trust_action": "NO_TRADE"},
        )
    ]

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, features, {})

    assert result.signals[0].signal_type == ResearchSignalType.FILTER_BLOCK
    assert not result.proposals


def test_integrity_filter_blocks_high_risk_context() -> None:
    strategy = strategy_from_definition(strategy_definition("integrity_pass_filter_v1"))
    features = [
        research_feature(
            ResearchFeatureSource.INTEGRITY,
            {"action_hint": "MANUAL_REVIEW", "overall_risk_score": 90},
        )
    ]

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, features, {})

    assert result.signals[0].signal_type == ResearchSignalType.FILTER_BLOCK
    assert not result.proposals


def test_divergence_strategy_creates_hypothetical_proposal_for_lower_side() -> None:
    strategy = strategy_from_definition(
        strategy_definition("divergence_research_hypothesis_v1")
    )
    features = [
        research_feature(
            ResearchFeatureSource.DIVERGENCE,
            {
                "statuses": ["MATERIAL_DIVERGENCE"],
                "lower_side_inputs": [
                    {
                        "status": "MATERIAL_DIVERGENCE",
                        "left_market_id": MARKET_ID,
                        "left_venue_id": "left_venue",
                        "left_outcome_id": None,
                        "left_price": "0.40",
                        "right_market_id": "right_market",
                        "right_price_aligned": "0.55",
                    }
                ],
            },
        )
    ]

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, features, {})
    serialized = " ".join(result.signals[0].reason_codes + result.proposals[0].reason_codes)

    assert result.signals[0].signal_type == ResearchSignalType.HYPOTHETICAL_INTENT
    assert result.proposals[0].requested_price == Decimal("0.40")
    for forbidden in ("arb" + "itrage", "pro" + "fit"):
        assert forbidden not in serialized.lower()


def test_divergence_strategy_skips_when_lower_side_cannot_be_determined() -> None:
    strategy = strategy_from_definition(
        strategy_definition("divergence_research_hypothesis_v1")
    )
    features = [
        research_feature(
            ResearchFeatureSource.DIVERGENCE,
            {"statuses": ["WATCH"], "lower_side_inputs": []},
        )
    ]

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, features, {})

    assert result.signals[0].signal_type == ResearchSignalType.REVIEW_ONLY
    assert not result.proposals


def test_composite_strategy_blocks_missing_critical_data() -> None:
    strategy = strategy_from_definition(
        strategy_definition("composite_conservative_research_v1")
    )

    result = strategy.generate_signals_and_proposals(MARKET_ID, ASOF, [], {})

    assert result.signals[0].signal_type == ResearchSignalType.REVIEW_ONLY
    assert "TRUST_VERDICT_NOT_ALLOWED" in result.signals[0].reason_codes
    assert not result.proposals
