from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.domain.enums import MarketStatus
from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import (
    ExposureSource,
    PreTradeAction,
    StrategyContext,
    TradeIntentType,
)
from prediction_desk.pretrade.models import ExposureSnapshot
from prediction_desk.pretrade.service import PreTradeService
from tests.equivalence_helpers import KALSHI_RAIN, POLYMARKET_RAIN, ingest_fixture_venues
from tests.test_divergence_service import DIVERGENCE_ASOF

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
CLEAN_MARKET = "mkt_cpi_yoy_at_least_3pct_2026_09"
AMBIGUOUS_MARKET = "mkt_candidate_announcement_vague_2026"


def test_inactive_market_is_blocked_when_policy_requires_active(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path / "inactive.db")
    with repo as current:
        market = current.get_market(CLEAN_MARKET)
        assert market is not None
        current.create_market(market.model_copy(update={"status": MarketStatus.CLOSED}))
        result = PreTradeService(current).check_market_default_intent(CLEAN_MARKET, ASOF)

    assert result.decision.action == PreTradeAction.NO_TRADE
    assert "MARKET_NOT_ACTIVE" in result.decision.hard_blockers


def test_high_resolution_risk_blocks(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'high_resolution_risk.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = PreTradeService(repo).check_market_default_intent(AMBIGUOUS_MARKET, ASOF)

    assert result.decision.action == PreTradeAction.NO_TRADE
    assert "RESOLUTION_RISK_ABOVE_POLICY_LIMIT" in result.decision.reason_codes


def test_cross_venue_strategy_without_context_forces_review(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'cross_venue_missing_context.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        result = PreTradeService(repo).check_market_default_intent(
            CLEAN_MARKET,
            ASOF,
            strategy_context=StrategyContext.CROSS_VENUE_COMPARISON,
        )

    assert result.decision.action == PreTradeAction.MANUAL_REVIEW
    assert "MISSING_EQUIVALENCE_CONTEXT" in result.decision.reason_codes
    assert "MISSING_DIVERGENCE_CONTEXT" in result.decision.reason_codes


def test_exposure_cap_reduces_final_allowed_size(tmp_path: Path) -> None:
    repo = _sample_repo(tmp_path / "exposure_gate.db")
    with repo as current:
        current.save_exposure_snapshot(
            ExposureSnapshot(
                exposure_snapshot_id="gate_exposure",
                asof_timestamp=ASOF,
                created_at=ASOF,
                source=ExposureSource.MANUAL,
                market_id=CLEAN_MARKET,
                event_id="event_cpi_threshold_2026_09",
                venue_id="sample_research_venue",
                strategy_context=StrategyContext.RESEARCH.value,
                market_exposure_units=Decimal("4.5"),
                event_exposure_units=Decimal("0"),
                venue_exposure_units=Decimal("0"),
                strategy_exposure_units=Decimal("0"),
                metadata={},
            )
        )
        result = PreTradeService(current).check_market_default_intent(CLEAN_MARKET, ASOF)

    assert result.decision.action == PreTradeAction.ALLOW_SMALLER_SIZE
    assert result.decision.final_allowed_size_units == Decimal("0.5")
    assert "EXPOSURE_CAP_REDUCED_SIZE" in result.decision.reason_codes


def test_cross_venue_divergence_metadata_is_included_in_input_snapshot(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'pretrade_divergence_context.db'}"
    ingest_fixture_venues(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        from prediction_desk.divergence.service import DivergenceService
        from prediction_desk.equivalence.service import EquivalenceService

        equivalence = EquivalenceService(repo).assess_market_equivalence(
            KALSHI_RAIN,
            POLYMARKET_RAIN,
            DIVERGENCE_ASOF,
        )
        DivergenceService(repo).analyze_equivalence_divergence(
            equivalence.assessment.equivalence_assessment_id,
            asof_timestamp=DIVERGENCE_ASOF,
        )
        result = PreTradeService(repo).check_market_default_intent(
            KALSHI_RAIN,
            DIVERGENCE_ASOF,
            strategy_context=StrategyContext.CROSS_VENUE_COMPARISON,
            intent_type=TradeIntentType.RESEARCH_ONLY,
        )

    assert result.input_snapshot.latest_equivalence_assessment_ids
    assert result.input_snapshot.latest_divergence_assessment_ids
    assert result.input_snapshot.max_divergence_score is not None


class _RepoContext:
    def __init__(self, database_path: Path) -> None:
        self.database_url = f"sqlite:///{database_path}"
        init_db(self.database_url)
        engine = build_engine(self.database_url)
        self.session_factory = build_session_factory(engine)

    def __enter__(self) -> PredictionMarketRepository:
        self.context = self.session_factory.begin()
        session = self.context.__enter__()
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        return repo

    def __exit__(self, *exc: object) -> None:
        self.context.__exit__(*exc)


def _sample_repo(database_path: Path) -> _RepoContext:
    return _RepoContext(database_path)
