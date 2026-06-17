"""Service layer for pre-trade admissibility checks."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import (
    ExposureSource,
    PreTradeAction,
    StrategyContext,
    TradeIntentType,
)
from prediction_desk.pretrade.gate import (
    PreTradeGateError,
    build_trade_intent_from_defaults,
    evaluate_pretrade_gate,
)
from prediction_desk.pretrade.models import (
    ExposureSnapshot,
    ExposureSnapshotCreate,
    MarketRestrictionRule,
    MarketRestrictionRuleCreate,
    PreTradeCheckResponse,
    PreTradeDecision,
    PreTradePolicy,
    TradeIntent,
    compute_trade_intent_id,
)
from prediction_desk.pretrade.policies import build_default_pretrade_policy


class PreTradeServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class PreTradeService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def check_pretrade_intent(
        self,
        intent: TradeIntent,
        *,
        policy_id: str | None = None,
        force_recompute_context: bool = False,
    ) -> PreTradeCheckResponse:
        if intent.trade_intent_id == "pending":
            intent = intent.model_copy(
                update={"trade_intent_id": compute_trade_intent_id(intent)}
            )
        policy = self._policy(policy_id, intent.asof_timestamp)
        try:
            return evaluate_pretrade_gate(
                intent,
                policy=policy,
                force_recompute_context=force_recompute_context,
                repo=self.repo,
            )
        except PreTradeGateError as exc:
            raise PreTradeServiceError(exc.code, exc.message) from exc

    def check_market_default_intent(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        policy_id: str | None = None,
        strategy_context: StrategyContext = StrategyContext.RESEARCH,
        intent_type: TradeIntentType = TradeIntentType.RESEARCH_ONLY,
        requested_size_units: Decimal = Decimal("1"),
    ) -> PreTradeCheckResponse:
        intent = build_trade_intent_from_defaults(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            strategy_context=strategy_context,
            intent_type=intent_type,
            requested_size_units=requested_size_units,
        )
        return self.check_pretrade_intent(intent, policy_id=policy_id)

    def list_pretrade_decisions(
        self,
        *,
        market_id: str | None = None,
        action: PreTradeAction | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PreTradeDecision]:
        return self.repo.list_pretrade_decisions(
            market_id=market_id,
            action=action,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def get_pretrade_decision(self, pretrade_decision_id: str) -> PreTradeDecision:
        decision = self.repo.get_pretrade_decision(pretrade_decision_id)
        if decision is None:
            raise PreTradeServiceError("pretrade_decision_not_found")
        return decision

    def get_latest_pretrade_decision_asof(
        self,
        market_id: str,
        asof_timestamp: datetime,
    ) -> PreTradeDecision:
        decision = self.repo.get_latest_pretrade_decision_asof(market_id, asof_timestamp)
        if decision is None:
            raise PreTradeServiceError("pretrade_decision_not_found")
        return decision

    def create_default_pretrade_policy_if_missing(self) -> PreTradePolicy:
        existing = self.repo.get_active_pretrade_policy()
        if existing is not None:
            return existing
        return self.repo.save_pretrade_policy(build_default_pretrade_policy())

    def list_policies(self) -> list[PreTradePolicy]:
        return self.repo.list_pretrade_policies()

    def get_policy(self, policy_id: str) -> PreTradePolicy:
        policy = self.repo.get_pretrade_policy(policy_id)
        if policy is None:
            raise PreTradeServiceError("pretrade_policy_not_found")
        return policy

    def save_market_restriction_rule(
        self,
        payload: MarketRestrictionRuleCreate,
    ) -> MarketRestrictionRule:
        now = datetime.now(tz=UTC)
        rule = MarketRestrictionRule(
            restriction_id=f"restriction_{uuid4().hex[:24]}",
            created_at=now,
            **payload.model_dump(),
        )
        return self.repo.save_market_restriction_rule(rule)

    def list_market_restriction_rules(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketRestrictionRule]:
        return self.repo.list_market_restriction_rules(limit=limit, offset=offset)

    def save_exposure_snapshot(
        self,
        payload: ExposureSnapshotCreate,
    ) -> ExposureSnapshot:
        now = datetime.now(tz=UTC)
        snapshot = ExposureSnapshot(
            exposure_snapshot_id=f"exposure_snapshot_{uuid4().hex[:24]}",
            asof_timestamp=payload.asof_timestamp or now,
            created_at=now,
            source=payload.source or ExposureSource.MANUAL,
            market_id=payload.market_id,
            event_id=payload.event_id,
            venue_id=payload.venue_id,
            strategy_context=payload.strategy_context,
            market_exposure_units=payload.market_exposure_units,
            event_exposure_units=payload.event_exposure_units,
            venue_exposure_units=payload.venue_exposure_units,
            strategy_exposure_units=payload.strategy_exposure_units,
            metadata=payload.metadata,
        )
        return self.repo.save_exposure_snapshot(snapshot)

    def list_exposure_snapshots(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ExposureSnapshot]:
        return self.repo.list_exposure_snapshots(limit=limit, offset=offset)

    def _policy(self, policy_id: str | None, asof_timestamp: datetime) -> PreTradePolicy:
        if policy_id is not None:
            policy = self.repo.get_pretrade_policy(policy_id)
            if policy is None:
                raise PreTradeServiceError("pretrade_policy_not_found")
            return policy
        policy = self.repo.get_active_pretrade_policy(asof_timestamp=asof_timestamp)
        if policy is not None:
            return policy
        return self.repo.save_pretrade_policy(build_default_pretrade_policy())


def check_pretrade_intent(
    intent: TradeIntent,
    *,
    policy_id: str | None = None,
    force_recompute_context: bool = False,
    database_url: str | None = None,
) -> PreTradeCheckResponse:
    if intent.trade_intent_id == "pending":
        intent = intent.model_copy(update={"trade_intent_id": compute_trade_intent_id(intent)})
    with session_scope(database_url) as session:
        return PreTradeService(PredictionMarketRepository(session)).check_pretrade_intent(
            intent,
            policy_id=policy_id,
            force_recompute_context=force_recompute_context,
        )
