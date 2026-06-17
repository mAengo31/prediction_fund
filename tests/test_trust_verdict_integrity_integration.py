from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.integrity.enums import IntegrityActionHint, SignalSeverity
from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.scoring.trust_verdict import build_trust_verdict


def test_trust_verdict_unchanged_without_integrity_assessment() -> None:
    clean, *_ = sample_markets()
    asof = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)

    verdict = build_trust_verdict(
        market=clean.market,
        rule_snapshot=clean.rule_snapshot,
        orderbook_snapshot=clean.orderbook_snapshot,
        asof_timestamp=asof,
    )

    assert verdict.action == VerdictAction.ALLOW
    assert "integrity_assessment_id" in verdict.data_versions
    assert verdict.data_versions["integrity_assessment_id"] is None


def test_trust_verdict_incorporates_integrity_assessment() -> None:
    clean, *_ = sample_markets()
    asof = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)

    verdict = build_trust_verdict(
        market=clean.market,
        rule_snapshot=clean.rule_snapshot,
        orderbook_snapshot=clean.orderbook_snapshot,
        asof_timestamp=asof,
        integrity_assessment=_assessment(IntegrityActionHint.NO_TRADE),
    )

    assert verdict.action == VerdictAction.NO_TRADE
    assert "INTEGRITY_WIDE_SPREAD" in verdict.reason_codes
    assert verdict.data_versions["integrity_assessment_id"] == "integrity_assessment_test"
    assert verdict.metadata["integrity"]["overall_risk_score"] == 90
    assert verdict.liquidity_risk_score == 90
    assert verdict.price_integrity_score == 60


def _assessment(action_hint: IntegrityActionHint) -> IntegrityAssessment:
    return IntegrityAssessment(
        integrity_assessment_id="integrity_assessment_test",
        market_id="mkt_test",
        asof_timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        generated_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        available_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        feature_snapshot_id="feature_test",
        signal_ids=[],
        overall_risk_score=90,
        price_anomaly_score=40,
        liquidity_anomaly_score=90,
        freshness_risk_score=20,
        orderbook_structure_score=0,
        rule_change_risk_score=0,
        rule_price_coupling_score=0,
        data_quality_risk_score=0,
        manipulation_proxy_score=65,
        severity=SignalSeverity.ERROR,
        action_hint=action_hint,
        reason_codes=["WIDE_SPREAD"],
        input_hash="input",
        output_hash="output",
        metadata={},
    )
