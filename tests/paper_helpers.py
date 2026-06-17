from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from prediction_desk.examples.sample_markets import load_sample_data
from prediction_desk.marketdata.service import MarketDataService
from prediction_desk.paper.enums import PaperOrderStatus
from prediction_desk.paper.models import PaperOrder, PaperPositionSnapshot
from prediction_desk.paper.policies import build_default_paper_execution_policy
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import TradeIntentType, TradeSide

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
MARKET_ID = "mkt_cpi_yoy_at_least_3pct_2026_09"
VENUE_ID = "sample_research_venue"


def session_factory(tmp_path: Path, name: str):
    database_url = f"sqlite:///{tmp_path / name}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)


def loaded_repo(tmp_path: Path, name: str):
    factory = session_factory(tmp_path, name)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        load_sample_data(repo)
        MarketDataService(repo).derive_market_data_for_market(MARKET_ID)
    return factory


def accepted_order(
    *,
    side: TradeSide = TradeSide.BUY,
    intent_type: TradeIntentType = TradeIntentType.AGGRESSIVE_LIMIT,
    limit_price: Decimal | None = Decimal("0.52"),
    size: Decimal = Decimal("1"),
    asof_timestamp: datetime = ASOF,
) -> PaperOrder:
    return PaperOrder(
        paper_order_id="paper_order_test",
        trade_intent_id="trade_intent_test",
        pretrade_decision_id="pretrade_decision_test",
        paper_policy_id=build_default_paper_execution_policy(created_at=ASOF).paper_policy_id,
        simulation_run_id=None,
        market_id=MARKET_ID,
        outcome_id=None,
        venue_id=VENUE_ID,
        side=side,
        intent_type=intent_type.value,
        requested_price=limit_price,
        limit_price=limit_price,
        requested_size_units=size,
        accepted_size_units=size,
        filled_size_units=Decimal("0"),
        remaining_size_units=size,
        status=PaperOrderStatus.ACCEPTED,
        rejection_reason_codes=[],
        created_at=asof_timestamp,
        asof_timestamp=asof_timestamp,
        available_at=asof_timestamp,
        metadata={"test": True},
    )


def long_position(units: Decimal = Decimal("2")) -> PaperPositionSnapshot:
    return PaperPositionSnapshot(
        position_snapshot_id="paper_position_existing",
        simulation_run_id=None,
        market_id=MARKET_ID,
        outcome_id=None,
        venue_id=VENUE_ID,
        asof_timestamp=ASOF,
        generated_at=ASOF,
        available_at=ASOF,
        position_units=units,
        average_entry_price=Decimal("0.50"),
        cost_basis=units * Decimal("0.50"),
        realized_pnl_simulated=Decimal("0"),
        unrealized_pnl_simulated=Decimal("0"),
        mark_price=Decimal("0.50"),
        mark_price_snapshot_id=None,
        is_flat=units == Decimal("0"),
        is_simulated=True,
        metadata={},
    )

