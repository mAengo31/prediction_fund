from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.replay.policies import (
    AllowAllPolicy,
    ResolutionRiskOnlyPolicy,
    TrustVerdictPolicy,
)
from prediction_desk.resolution.ambiguity import assess_rule_ambiguity
from prediction_desk.resolution.models import ResolutionAnalysis
from prediction_desk.resolution.parser import parse_resolution_predicate
from prediction_desk.scoring.trust_verdict import build_trust_verdict


def test_allow_all_policy_always_allows() -> None:
    clean, *_ = sample_markets()

    decision = AllowAllPolicy().decide(
        market=clean.market,
        rule_snapshot=None,
        orderbook_snapshot=None,
        resolution_analysis=None,
        integrity_assessment=None,
        trust_verdict=None,
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
    )

    assert decision.action == VerdictAction.ALLOW.value
    assert decision.allowed_size_multiplier == Decimal("1.0")
    assert "BASELINE_ALLOW_ALL" in decision.reason_codes


def test_trust_verdict_policy_maps_actions_to_allowed_size() -> None:
    clean, *_ = sample_markets()
    verdict = build_trust_verdict(
        market=clean.market,
        rule_snapshot=clean.rule_snapshot,
        orderbook_snapshot=None,
        asof_timestamp=datetime(2026, 6, 16, tzinfo=UTC),
    )

    decision = TrustVerdictPolicy().decide(
        market=clean.market,
        rule_snapshot=clean.rule_snapshot,
        orderbook_snapshot=None,
        resolution_analysis=None,
        integrity_assessment=None,
        trust_verdict=verdict,
        asof_timestamp=verdict.asof_timestamp,
    )

    assert decision.action == VerdictAction.MANUAL_REVIEW.value
    assert decision.allowed_size_multiplier == Decimal("0.0")
    assert decision.scores["liquidity_risk_score"] == 90


def test_resolution_risk_only_policy_blocks_high_ambiguity() -> None:
    _, ambiguous, *_ = sample_markets()
    predicate = parse_resolution_predicate(ambiguous.market, ambiguous.rule_snapshot)
    assessment = assess_rule_ambiguity(
        ambiguous.market,
        ambiguous.rule_snapshot,
        predicate,
    ).model_copy(update={"overall_score": 90})
    analysis = ResolutionAnalysis(
        market=ambiguous.market,
        rule_snapshot=ambiguous.rule_snapshot,
        predicate=predicate,
        ambiguity_assessment=assessment,
    )

    decision = ResolutionRiskOnlyPolicy().decide(
        market=ambiguous.market,
        rule_snapshot=ambiguous.rule_snapshot,
        orderbook_snapshot=ambiguous.orderbook_snapshot,
        resolution_analysis=analysis,
        integrity_assessment=None,
        trust_verdict=None,
        asof_timestamp=ambiguous.rule_snapshot.captured_at,
    )

    assert decision.action == VerdictAction.NO_TRADE.value
    assert decision.allowed_size_multiplier == Decimal("0.0")
    assert "MISSING_RESOLUTION_SOURCE" in decision.reason_codes
