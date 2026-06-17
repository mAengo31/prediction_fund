from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import (
    ExposureSource,
    PreTradeAction,
    StrategyContext,
    TradeIntentType,
    TradeSide,
)
from prediction_desk.pretrade.exposure import (
    evaluate_exposure_limits,
    get_latest_exposure_asof,
)
from prediction_desk.pretrade.models import ExposureSnapshot, TradeIntent
from prediction_desk.pretrade.policies import build_default_pretrade_policy

ASOF = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
DECIMAL_ZERO = Decimal("0")


def test_missing_exposure_allowed_by_default_policy_emits_warning() -> None:
    result = evaluate_exposure_limits(
        _intent(),
        build_default_pretrade_policy(created_at=ASOF),
        None,
    )

    assert result.action == PreTradeAction.ALLOW
    assert "UNKNOWN_EXPOSURE_ALLOWED_BY_POLICY" in result.warnings


def test_missing_exposure_blocked_when_policy_disallows_unknown_exposure() -> None:
    policy = build_default_pretrade_policy(created_at=ASOF).model_copy(
        update={"allow_unknown_exposure": False}
    )

    result = evaluate_exposure_limits(_intent(), policy, None)

    assert result.action == PreTradeAction.MANUAL_REVIEW
    assert "MISSING_EXPOSURE_SNAPSHOT" in result.warnings


def test_max_order_size_reduces_allowed_size() -> None:
    policy = build_default_pretrade_policy(created_at=ASOF).model_copy(
        update={"max_order_size_units": Decimal("0.25")}
    )

    result = evaluate_exposure_limits(_intent(), policy, _exposure())

    assert result.action == PreTradeAction.ALLOW_SMALLER_SIZE
    assert result.max_allowed_size_units == Decimal("0.25")


def test_market_exposure_cap_reduces_or_blocks() -> None:
    policy = build_default_pretrade_policy(created_at=ASOF)
    reduced = evaluate_exposure_limits(
        _intent(),
        policy,
        _exposure(market_exposure_units=Decimal("4.75")),
    )
    blocked = evaluate_exposure_limits(
        _intent(),
        policy,
        _exposure(market_exposure_units=Decimal("5")),
    )

    assert reduced.action == PreTradeAction.ALLOW_SMALLER_SIZE
    assert reduced.max_allowed_size_units == Decimal("0.25")
    assert blocked.action == PreTradeAction.NO_TRADE
    assert "EXPOSURE_LIMIT_BREACH" in blocked.hard_blockers


def test_exposure_snapshot_asof_lookup_does_not_use_future_snapshot(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'pretrade_exposure.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    session_factory = build_session_factory(engine)
    with session_factory.begin() as session:
        repo = PredictionMarketRepository(session)
        current = _exposure(exposure_snapshot_id="current_exposure")
        future = _exposure(
            exposure_snapshot_id="future_exposure",
            asof_timestamp=ASOF + timedelta(days=1),
            market_exposure_units=Decimal("5"),
        )
        repo.save_exposure_snapshot(current)
        repo.save_exposure_snapshot(future)
        found = get_latest_exposure_asof(
            repo,
            market_id="mkt_test",
            event_id="event_test",
            venue_id="venue_test",
            strategy_context="RESEARCH",
            asof_timestamp=ASOF + timedelta(hours=1),
        )

    assert found is not None
    assert found.exposure_snapshot_id == "current_exposure"


def _intent() -> TradeIntent:
    return TradeIntent(
        trade_intent_id="intent",
        market_id="mkt_test",
        venue_id="venue_test",
        strategy_context=StrategyContext.RESEARCH,
        side=TradeSide.BUY,
        intent_type=TradeIntentType.RESEARCH_ONLY,
        requested_size_units=Decimal("1"),
        asof_timestamp=ASOF,
    )


def _exposure(
    *,
    exposure_snapshot_id: str = "exposure",
    asof_timestamp: datetime = ASOF,
    market_exposure_units: Decimal = DECIMAL_ZERO,
) -> ExposureSnapshot:
    return ExposureSnapshot(
        exposure_snapshot_id=exposure_snapshot_id,
        asof_timestamp=asof_timestamp,
        created_at=asof_timestamp,
        source=ExposureSource.MANUAL,
        market_id="mkt_test",
        event_id="event_test",
        venue_id="venue_test",
        strategy_context="RESEARCH",
        market_exposure_units=market_exposure_units,
        event_exposure_units=DECIMAL_ZERO,
        venue_exposure_units=DECIMAL_ZERO,
        strategy_exposure_units=DECIMAL_ZERO,
        metadata={},
    )
