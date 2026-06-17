from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from prediction_desk.divergence.enums import (
    DivergenceActionHint,
    DivergenceSignalSeverity,
    DivergenceStatus,
)
from prediction_desk.divergence.models import CrossVenueDivergenceAssessment
from prediction_desk.integrity.enums import IntegrityActionHint, SignalSeverity
from prediction_desk.integrity.models import IntegrityAssessment
from prediction_desk.paper.models import PaperPortfolioSnapshot
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction
from prediction_desk.pretrade.models import PreTradeDecision
from prediction_desk.research.enums import ResearchFeatureSource
from prediction_desk.research.features import build_research_features
from tests.paper_helpers import MARKET_ID, loaded_repo, long_position
from tests.research_helpers import ASOF, research_feature


def test_feature_builder_uses_only_asof_safe_objects(tmp_path: Path) -> None:
    factory = loaded_repo(tmp_path, "research_features.db")
    future = ASOF + timedelta(days=1)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        current_price = repo.get_latest_price_snapshot_asof(MARKET_ID, ASOF)
        assert current_price is not None
        repo.save_market_price_snapshot(
            current_price.model_copy(
                update={
                    "price_snapshot_id": "future_research_price",
                    "available_at": future,
                    "price": Decimal("0.99"),
                    "mid": Decimal("0.99"),
                    "data_hash": "future_research_price_hash",
                }
            )
        )
        repo.save_integrity_assessment(_future_integrity(future))
        repo.save_divergence_assessment(_future_divergence(future))
        repo.save_pretrade_decision(_future_pretrade_decision(future))
        repo.save_paper_position_snapshot(
            long_position().model_copy(
                update={
                    "position_snapshot_id": "future_paper_position",
                    "available_at": future,
                    "position_units": Decimal("9"),
                }
            )
        )
        repo.save_paper_portfolio_snapshot(_future_portfolio(future))

        features = build_research_features(
            MARKET_ID,
            ASOF,
            include_sources=[
                "MARKET_DATA",
                "INTEGRITY",
                "DIVERGENCE",
                "PRETRADE",
                "PAPER",
            ],
            force=True,
            repo=repo,
        )

    values = {feature.feature_source: feature.values for feature in features}
    assert (
        values[ResearchFeatureSource.MARKET_DATA]["price_snapshot_id"]
        == current_price.price_snapshot_id
    )
    assert values[ResearchFeatureSource.INTEGRITY]["integrity_assessment_id"] is None
    assert values[ResearchFeatureSource.DIVERGENCE]["assessment_ids"] == []
    assert values[ResearchFeatureSource.PRETRADE]["pretrade_decision_id"] is None
    assert values[ResearchFeatureSource.PAPER]["position_snapshot_id"] is None
    assert values[ResearchFeatureSource.PAPER]["portfolio_snapshot_id"] is None


def test_research_feature_repository_asof_filter_excludes_future_rows(
    tmp_path: Path,
) -> None:
    factory = loaded_repo(tmp_path, "research_feature_repo_asof.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        current = repo.save_research_feature_snapshot(
            research_feature(ResearchFeatureSource.MARKET_DATA, {"price_snapshot_id": "now"})
        )
        repo.save_research_feature_snapshot(
            research_feature(
                ResearchFeatureSource.MARKET_DATA,
                {"price_snapshot_id": "future"},
            ).model_copy(
                update={
                    "research_feature_snapshot_id": "future_research_feature",
                    "available_at": ASOF + timedelta(days=1),
                    "input_hash": "future_research_feature_input",
                }
            )
        )

        features = repo.list_research_feature_snapshots(
            market_id=MARKET_ID,
            asof_timestamp=ASOF,
        )

    assert [feature.research_feature_snapshot_id for feature in features] == [
        current.research_feature_snapshot_id
    ]


def _future_integrity(available_at) -> IntegrityAssessment:
    return IntegrityAssessment(
        integrity_assessment_id="future_integrity_assessment",
        market_id=MARKET_ID,
        asof_timestamp=ASOF,
        generated_at=ASOF,
        available_at=available_at,
        feature_snapshot_id="feature_future",
        signal_ids=[],
        overall_risk_score=99,
        price_anomaly_score=0,
        liquidity_anomaly_score=0,
        freshness_risk_score=0,
        orderbook_structure_score=0,
        rule_change_risk_score=0,
        rule_price_coupling_score=0,
        data_quality_risk_score=0,
        manipulation_proxy_score=0,
        severity=SignalSeverity.ERROR,
        action_hint=IntegrityActionHint.MANUAL_REVIEW,
        reason_codes=["FUTURE_INTEGRITY"],
        input_hash="future_integrity_input",
        output_hash="future_integrity_output",
        metadata={},
    )


def _future_divergence(available_at) -> CrossVenueDivergenceAssessment:
    return CrossVenueDivergenceAssessment(
        divergence_assessment_id="future_divergence_assessment",
        divergence_snapshot_id="future_divergence_snapshot",
        equivalence_assessment_id="future_equivalence",
        left_market_id=MARKET_ID,
        right_market_id="right_market",
        asof_timestamp=ASOF,
        generated_at=ASOF,
        available_at=available_at,
        signal_ids=[],
        overall_divergence_score=80,
        price_divergence_score=80,
        spread_adjusted_score=0,
        persistence_score=0,
        stale_side_score=0,
        low_liquidity_score=0,
        low_data_quality_score=0,
        integrity_context_score=0,
        equivalence_context_score=0,
        status=DivergenceStatus.MATERIAL_DIVERGENCE,
        severity=DivergenceSignalSeverity.ERROR,
        action_hint=DivergenceActionHint.RESEARCH,
        reason_codes=["FUTURE_DIVERGENCE"],
        absolute_mid_gap=Decimal("0.08"),
        spread_adjusted_gap=Decimal("0.04"),
        gap_bps=Decimal("100"),
        comparison_permission="COMPARABLE",
        equivalence_score=90,
        equivalence_confidence_score=90,
        input_hash="future_divergence_input",
        output_hash="future_divergence_output",
        metadata={},
    )


def _future_pretrade_decision(available_at) -> PreTradeDecision:
    return PreTradeDecision(
        pretrade_decision_id="future_pretrade_decision",
        trade_intent_id="future_trade_intent",
        input_snapshot_id="future_input_snapshot",
        market_id=MARKET_ID,
        asof_timestamp=ASOF,
        generated_at=ASOF,
        available_at=available_at,
        policy_id="policy",
        policy_name="policy",
        policy_version="v1",
        action=PreTradeAction.NO_TRADE,
        allowed_size_multiplier=Decimal("0"),
        requested_size_units=Decimal("1"),
        max_allowed_size_units=Decimal("0"),
        final_allowed_size_units=Decimal("0"),
        passive_only=False,
        manual_review_required=False,
        hard_blocked=True,
        composite_risk_score=100,
        hard_blockers=["FUTURE_PRETRADE"],
        warnings=[],
        reason_codes=["FUTURE_PRETRADE"],
        evidence={},
        input_hash="future_pretrade_input",
        output_hash="future_pretrade_output",
        metadata={},
    )


def _future_portfolio(available_at) -> PaperPortfolioSnapshot:
    return PaperPortfolioSnapshot(
        portfolio_snapshot_id="future_paper_portfolio",
        simulation_run_id=None,
        asof_timestamp=ASOF,
        generated_at=ASOF,
        available_at=available_at,
        cash_balance_simulated=Decimal("1000"),
        gross_exposure_simulated=Decimal("9"),
        net_exposure_simulated=Decimal("9"),
        realized_pnl_simulated=Decimal("0"),
        unrealized_pnl_simulated=Decimal("0"),
        total_fees_simulated=Decimal("0"),
        total_equity_simulated=Decimal("1000"),
        open_positions_count=1,
        closed_positions_count=0,
        is_simulated=True,
        metadata={},
    )
