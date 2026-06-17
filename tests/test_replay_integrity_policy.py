from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.enums import VerdictAction
from prediction_desk.examples.sample_markets import load_sample_data, sample_markets
from prediction_desk.integrity.enums import IntegrityActionHint, SignalSeverity
from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.integrity.service import IntegrityService
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import ReplayRunConfig
from prediction_desk.replay.policies import IntegrityGatePolicy
from prediction_desk.replay.runner import run_replay


def test_integrity_gate_policy_maps_action_hints() -> None:
    clean, *_ = sample_markets()
    assessment = _assessment(action_hint=IntegrityActionHint.PASSIVE_ONLY)

    decision = IntegrityGatePolicy().decide(
        market=clean.market,
        rule_snapshot=None,
        orderbook_snapshot=None,
        resolution_analysis=None,
        integrity_assessment=assessment,
        trust_verdict=None,
        asof_timestamp=assessment.asof_timestamp,
    )

    assert decision.action == VerdictAction.PASSIVE_ONLY.value
    assert decision.allowed_size_multiplier == Decimal("0.25")


def test_integrity_gate_policy_manual_reviews_missing_assessment() -> None:
    clean, *_ = sample_markets()

    decision = IntegrityGatePolicy().decide(
        market=clean.market,
        rule_snapshot=None,
        orderbook_snapshot=None,
        resolution_analysis=None,
        integrity_assessment=None,
        trust_verdict=None,
        asof_timestamp=datetime(2026, 6, 16, 13, 0, tzinfo=UTC),
    )

    assert decision.action == VerdictAction.MANUAL_REVIEW.value
    assert "MISSING_INTEGRITY_ASSESSMENT" in decision.reason_codes


def test_replay_includes_integrity_metadata(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'replay_integrity.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    market_id = "mkt_cpi_yoy_at_least_3pct_2026_09"
    asof = datetime(2026, 6, 16, 13, 0, tzinfo=UTC)

    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(market_id)
        IntegrityService(repo).analyze_market_integrity(market_id, asof)
        result = run_replay(
            ReplayRunConfig(
                policy_name="integrity_gate_v1",
                start_time=asof,
                end_time=asof.replace(hour=14),
                interval_seconds=3600,
                market_ids=[market_id],
                max_steps=10,
            ),
            repo=repo,
        )

    assert result.steps[0].metadata["latest_integrity_assessment_id"]
    assert result.steps[0].metadata["integrity_overall_risk_score"] is not None
    assert result.steps[0].action != VerdictAction.MANUAL_REVIEW.value


def _assessment(action_hint: IntegrityActionHint) -> IntegrityAssessment:
    return IntegrityAssessment(
        integrity_assessment_id="integrity_assessment_test",
        market_id="mkt_test",
        asof_timestamp=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        generated_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        available_at=datetime(2026, 6, 16, 12, 0, tzinfo=UTC),
        feature_snapshot_id="feature_test",
        signal_ids=[],
        overall_risk_score=60,
        price_anomaly_score=0,
        liquidity_anomaly_score=60,
        freshness_risk_score=0,
        orderbook_structure_score=0,
        rule_change_risk_score=0,
        rule_price_coupling_score=0,
        data_quality_risk_score=0,
        manipulation_proxy_score=0,
        severity=SignalSeverity.WARNING,
        action_hint=action_hint,
        reason_codes=["TEST"],
        input_hash="input",
        output_hash="output",
        metadata={},
    )
