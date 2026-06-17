from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.pretrade.enums import TradeIntentType, TradeSide
from prediction_desk.research.enums import (
    ResearchActionBias,
    ResearchFeatureFamily,
    ResearchFeatureSource,
    ResearchSignalType,
)
from prediction_desk.research.models import (
    BASELINE_STRATEGY_ID,
    ResearchDecisionTrace,
    ResearchFeatureSnapshot,
    ResearchIntentProposal,
    ResearchSignal,
    ResearchStrategyDefinition,
    hash_payload,
    research_object_id,
)
from prediction_desk.research.strategies import default_research_strategy_definitions
from tests.paper_helpers import MARKET_ID

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)


def strategy_definition(strategy_name: str) -> ResearchStrategyDefinition:
    for definition in default_research_strategy_definitions(created_at=ASOF):
        if definition.strategy_name == strategy_name:
            return definition
    raise AssertionError(f"unknown strategy {strategy_name}")


def research_feature(
    source: ResearchFeatureSource,
    values: dict[str, Any],
    *,
    reason_codes: list[str] | None = None,
    market_id: str = MARKET_ID,
    asof_timestamp: datetime = ASOF,
) -> ResearchFeatureSnapshot:
    input_hash = hash_payload(
        {
            "source": source.value,
            "market_id": market_id,
            "asof_timestamp": asof_timestamp,
            "values": values,
        }
    )
    feature = ResearchFeatureSnapshot(
        research_feature_snapshot_id=research_object_id(
            "research_feature_test",
            {"input_hash": input_hash},
        ),
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=asof_timestamp,
        available_at=asof_timestamp,
        feature_source=source,
        feature_family=_family_for_source(source),
        source_ref_ids=[],
        values=values,
        reason_codes=reason_codes or [],
        input_hash=input_hash,
        output_hash="pending",
        metadata={},
    )
    return feature.model_copy(
        update={"output_hash": hash_payload({"values": values, "source": source.value})}
    )


def research_signal(
    *,
    strategy_id: str = BASELINE_STRATEGY_ID,
    strategy_name: str = "baseline_research_only_v1",
    market_id: str = MARKET_ID,
    asof_timestamp: datetime = ASOF,
) -> ResearchSignal:
    input_hash = hash_payload(
        {"strategy_id": strategy_id, "market_id": market_id, "asof": asof_timestamp}
    )
    signal = ResearchSignal(
        research_signal_id=research_object_id(
            "research_signal_test",
            {"input_hash": input_hash},
        ),
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        strategy_version="v1",
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=asof_timestamp,
        available_at=asof_timestamp,
        signal_type=ResearchSignalType.REVIEW_ONLY,
        signal_strength_score=10,
        confidence_score=50,
        action_bias=ResearchActionBias.RESEARCH_ONLY,
        reason_codes=["TEST_SIGNAL"],
        source_feature_ids=[],
        source_ref_ids=[],
        input_hash=input_hash,
        output_hash="pending",
        metadata={},
    )
    return signal.model_copy(update={"output_hash": hash_payload(signal.model_dump())})


def research_proposal(
    *,
    strategy_id: str = BASELINE_STRATEGY_ID,
    strategy_name: str = "baseline_research_only_v1",
    research_signal_id: str | None = None,
    market_id: str = MARKET_ID,
    requested_price: Decimal | None = None,
    requested_size_units: Decimal = Decimal("1"),
    intent_type: str = TradeIntentType.RESEARCH_ONLY.value,
    asof_timestamp: datetime = ASOF,
) -> ResearchIntentProposal:
    input_hash = hash_payload(
        {
            "strategy_id": strategy_id,
            "market_id": market_id,
            "signal": research_signal_id,
            "asof": asof_timestamp,
            "price": requested_price,
            "size": requested_size_units,
        }
    )
    proposal = ResearchIntentProposal(
        proposal_id=research_object_id(
            "research_proposal_test",
            {"input_hash": input_hash},
        ),
        strategy_id=strategy_id,
        strategy_name=strategy_name,
        strategy_version="v1",
        research_signal_id=research_signal_id,
        market_id=market_id,
        outcome_id=None,
        venue_id=None,
        asof_timestamp=asof_timestamp,
        generated_at=asof_timestamp,
        available_at=asof_timestamp,
        side=TradeSide.BUY,
        intent_type=intent_type,
        strategy_context="RESEARCH",
        requested_price=requested_price,
        requested_size_units=requested_size_units,
        requested_notional_usd=None,
        pretrade_required=True,
        paper_simulation_allowed=True,
        reason_codes=["TEST_PROPOSAL"],
        source_signal_ids=[research_signal_id] if research_signal_id else [],
        input_hash=input_hash,
        output_hash="pending",
        metadata={},
    )
    return proposal.model_copy(update={"output_hash": hash_payload(proposal.model_dump())})


def research_trace(
    *,
    research_run_id: str = "research_run_test",
    strategy_id: str = BASELINE_STRATEGY_ID,
    market_id: str = MARKET_ID,
    research_signal_id: str | None = None,
    proposal_id: str | None = None,
    pretrade_action: str | None = "ALLOW",
    paper_order_status: str | None = None,
    filled_size_units_simulated: Decimal = Decimal("0"),
    asof_timestamp: datetime = ASOF,
) -> ResearchDecisionTrace:
    input_hash = hash_payload(
        {
            "run": research_run_id,
            "strategy": strategy_id,
            "market": market_id,
            "proposal": proposal_id,
            "asof": asof_timestamp,
        }
    )
    trace = ResearchDecisionTrace(
        trace_id=research_object_id("research_trace_test", {"input_hash": input_hash}),
        research_run_id=research_run_id,
        strategy_id=strategy_id,
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=asof_timestamp,
        available_at=asof_timestamp,
        research_signal_id=research_signal_id,
        proposal_id=proposal_id,
        trade_intent_id="trade_intent_test" if proposal_id else None,
        pretrade_decision_id="pretrade_decision_test" if proposal_id else None,
        paper_order_id="paper_order_test" if paper_order_status else None,
        paper_fill_ids=["paper_fill_test"] if filled_size_units_simulated > 0 else [],
        paper_position_snapshot_id=None,
        paper_portfolio_snapshot_id="paper_portfolio_test"
        if paper_order_status
        else None,
        pretrade_action=pretrade_action,
        paper_order_status=paper_order_status,
        filled_size_units_simulated=filled_size_units_simulated,
        avg_fill_price_simulated=Decimal("0.50")
        if filled_size_units_simulated > 0
        else None,
        reason_codes=["TEST_TRACE"],
        input_hash=input_hash,
        output_hash="pending",
        metadata={
            "pretrade_final_allowed_size_units": "1",
            "paper_total_equity_simulated": "1000",
            "paper_realized_pnl_simulated": "0",
            "paper_unrealized_pnl_simulated": "0",
        },
    )
    return trace.model_copy(update={"output_hash": hash_payload(trace.model_dump())})


def _family_for_source(source: ResearchFeatureSource) -> ResearchFeatureFamily:
    if source == ResearchFeatureSource.MARKET_DATA:
        return ResearchFeatureFamily.DATA_QUALITY
    if source == ResearchFeatureSource.RESOLUTION:
        return ResearchFeatureFamily.CONTRACT_RULES
    if source == ResearchFeatureSource.INTEGRITY:
        return ResearchFeatureFamily.RISK
    if source in {ResearchFeatureSource.EQUIVALENCE, ResearchFeatureSource.DIVERGENCE}:
        return ResearchFeatureFamily.CROSS_VENUE
    if source == ResearchFeatureSource.PRETRADE:
        return ResearchFeatureFamily.RISK
    if source == ResearchFeatureSource.PAPER:
        return ResearchFeatureFamily.SIMULATED_EXECUTION
    return ResearchFeatureFamily.OTHER
