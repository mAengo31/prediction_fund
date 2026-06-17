"""Service layer for simulated paper execution."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.paper.enums import PaperOrderStatus
from prediction_desk.paper.fills import simulate_order_fill
from prediction_desk.paper.models import (
    PaperExecutionPolicy,
    PaperFill,
    PaperOrder,
    PaperPortfolioSnapshot,
    PaperPositionSnapshot,
    PaperSimulationResult,
    compute_paper_order_id,
)
from prediction_desk.paper.policies import build_default_paper_execution_policy
from prediction_desk.paper.portfolio import compute_portfolio_snapshot
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction, TradeIntentType
from prediction_desk.pretrade.models import TradeIntent, compute_trade_intent_id
from prediction_desk.pretrade.service import PreTradeService, PreTradeServiceError


class PaperServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class PaperExecutionService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def create_default_paper_execution_policy_if_missing(self) -> PaperExecutionPolicy:
        existing = self.repo.get_active_paper_execution_policy()
        if existing is not None:
            return existing
        return self.repo.save_paper_execution_policy(build_default_paper_execution_policy())

    def simulate_trade_intent(
        self,
        intent: TradeIntent,
        *,
        paper_policy_id: str | None = None,
        force_recompute_pretrade: bool = False,
        simulation_run_id: str | None = None,
        initial_cash_simulated: Decimal = Decimal("0"),
    ) -> PaperSimulationResult:
        if intent.trade_intent_id == "pending":
            intent = intent.model_copy(
                update={"trade_intent_id": compute_trade_intent_id(intent)}
            )
        policy = self._policy(paper_policy_id)
        try:
            pretrade = PreTradeService(self.repo).check_pretrade_intent(
                intent,
                force_recompute_context=force_recompute_pretrade,
            )
        except PreTradeServiceError as exc:
            raise PaperServiceError(exc.code, exc.message) from exc

        order = _order_from_pretrade(
            intent=pretrade.trade_intent,
            policy=policy,
            pretrade_decision_id=pretrade.decision.pretrade_decision_id,
            pretrade_action=pretrade.decision.action,
            pretrade_final_size=pretrade.decision.final_allowed_size_units,
            simulation_run_id=simulation_run_id,
        )
        order = self.repo.save_paper_order(order)
        if order.status == PaperOrderStatus.REJECTED:
            portfolio = self._save_portfolio_snapshot(
                simulation_run_id=simulation_run_id,
                asof_timestamp=intent.asof_timestamp,
                initial_cash_simulated=initial_cash_simulated,
            )
            return PaperSimulationResult(
                pretrade=pretrade,
                order=order,
                portfolio_snapshot=portfolio,
            )

        fill_result = simulate_order_fill(
            order,
            policy,
            intent.asof_timestamp,
            repo=self.repo,
        )
        order = self.repo.save_paper_order(fill_result.order)
        fills: list[PaperFill] = []
        for fill in fill_result.fills:
            fills.append(self.repo.save_paper_fill(fill))
        for entry in fill_result.ledger_entries:
            self.repo.save_paper_ledger_entry(entry)
        position_snapshot = None
        if fill_result.position_snapshot is not None:
            position_snapshot = self.repo.save_paper_position_snapshot(
                fill_result.position_snapshot
            )
        portfolio = self._save_portfolio_snapshot(
            simulation_run_id=simulation_run_id,
            asof_timestamp=intent.asof_timestamp,
            initial_cash_simulated=initial_cash_simulated,
        )
        return PaperSimulationResult(
            pretrade=pretrade,
            order=order,
            fills=fills,
            ledger_entries=list(fill_result.ledger_entries),
            position_snapshot=position_snapshot,
            portfolio_snapshot=portfolio,
        )

    def list_paper_orders(
        self,
        *,
        market_id: str | None = None,
        status: PaperOrderStatus | None = None,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperOrder]:
        return self.repo.list_paper_orders(
            market_id=market_id,
            status=status,
            simulation_run_id=simulation_run_id,
            limit=limit,
            offset=offset,
        )

    def get_paper_order(self, paper_order_id: str) -> PaperOrder:
        order = self.repo.get_paper_order(paper_order_id)
        if order is None:
            raise PaperServiceError("paper_order_not_found")
        return order

    def list_paper_fills(
        self,
        *,
        market_id: str | None = None,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperFill]:
        return self.repo.list_paper_fills(
            market_id=market_id,
            simulation_run_id=simulation_run_id,
            limit=limit,
            offset=offset,
        )

    def list_paper_positions(
        self,
        *,
        market_id: str | None = None,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperPositionSnapshot]:
        return self.repo.list_paper_position_snapshots(
            market_id=market_id,
            simulation_run_id=simulation_run_id,
            limit=limit,
            offset=offset,
        )

    def get_latest_paper_position_asof(
        self,
        market_id: str,
        *,
        outcome_id: str | None = None,
        simulation_run_id: str | None = None,
        asof_timestamp: datetime | None = None,
    ) -> PaperPositionSnapshot:
        snapshot = self.repo.get_latest_paper_position_asof(
            market_id,
            outcome_id=outcome_id,
            simulation_run_id=simulation_run_id,
            asof_timestamp=asof_timestamp or datetime.now(tz=UTC),
        )
        if snapshot is None:
            raise PaperServiceError("paper_position_not_found")
        return snapshot

    def get_latest_paper_portfolio_asof(
        self,
        *,
        simulation_run_id: str | None = None,
        asof_timestamp: datetime | None = None,
    ) -> PaperPortfolioSnapshot:
        snapshot = self.repo.get_latest_paper_portfolio_asof(
            simulation_run_id=simulation_run_id,
            asof_timestamp=asof_timestamp or datetime.now(tz=UTC),
        )
        if snapshot is None:
            raise PaperServiceError("paper_portfolio_not_found")
        return snapshot

    def list_paper_portfolio_snapshots(
        self,
        *,
        simulation_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[PaperPortfolioSnapshot]:
        return self.repo.list_paper_portfolio_snapshots(
            simulation_run_id=simulation_run_id,
            limit=limit,
            offset=offset,
        )

    def save_paper_policy(self, policy: PaperExecutionPolicy) -> PaperExecutionPolicy:
        return self.repo.save_paper_execution_policy(policy)

    def list_paper_policies(self) -> list[PaperExecutionPolicy]:
        return self.repo.list_paper_execution_policies()

    def get_paper_policy(self, paper_policy_id: str) -> PaperExecutionPolicy:
        policy = self.repo.get_paper_execution_policy(paper_policy_id)
        if policy is None:
            raise PaperServiceError("paper_policy_not_found")
        return policy

    def _policy(self, paper_policy_id: str | None) -> PaperExecutionPolicy:
        if paper_policy_id is not None:
            policy = self.repo.get_paper_execution_policy(paper_policy_id)
            if policy is None:
                raise PaperServiceError("paper_policy_not_found")
            return policy
        existing = self.repo.get_active_paper_execution_policy()
        if existing is not None:
            return existing
        return self.repo.save_paper_execution_policy(build_default_paper_execution_policy())

    def _save_portfolio_snapshot(
        self,
        *,
        simulation_run_id: str | None,
        asof_timestamp: datetime,
        initial_cash_simulated: Decimal,
    ) -> PaperPortfolioSnapshot:
        snapshot = compute_portfolio_snapshot(
            self.repo,
            simulation_run_id=simulation_run_id,
            asof_timestamp=asof_timestamp,
            initial_cash_simulated=initial_cash_simulated,
        )
        return self.repo.save_paper_portfolio_snapshot(snapshot)


def simulate_trade_intent(
    intent: TradeIntent,
    *,
    paper_policy_id: str | None = None,
    force_recompute_pretrade: bool = False,
    database_url: str | None = None,
) -> PaperSimulationResult:
    with session_scope(database_url) as session:
        return PaperExecutionService(PredictionMarketRepository(session)).simulate_trade_intent(
            intent,
            paper_policy_id=paper_policy_id,
            force_recompute_pretrade=force_recompute_pretrade,
        )


def _order_from_pretrade(
    *,
    intent: TradeIntent,
    policy: PaperExecutionPolicy,
    pretrade_decision_id: str,
    pretrade_action: PreTradeAction,
    pretrade_final_size: Decimal,
    simulation_run_id: str | None,
) -> PaperOrder:
    accepted_size = _accepted_size(intent, policy, pretrade_action, pretrade_final_size)
    rejection_codes = _rejection_codes(intent, policy, pretrade_action, accepted_size)
    status = PaperOrderStatus.REJECTED if rejection_codes else PaperOrderStatus.ACCEPTED
    order = PaperOrder(
        paper_order_id="pending",
        trade_intent_id=intent.trade_intent_id,
        pretrade_decision_id=pretrade_decision_id,
        paper_policy_id=policy.paper_policy_id,
        simulation_run_id=simulation_run_id,
        market_id=intent.market_id,
        outcome_id=intent.outcome_id,
        venue_id=intent.venue_id,
        side=intent.side,
        intent_type=intent.intent_type.value,
        requested_price=intent.requested_price,
        limit_price=intent.requested_price,
        requested_size_units=intent.requested_size_units,
        accepted_size_units=accepted_size,
        filled_size_units=Decimal("0"),
        remaining_size_units=accepted_size,
        status=status,
        rejection_reason_codes=rejection_codes,
        created_at=intent.asof_timestamp,
        asof_timestamp=intent.asof_timestamp,
        available_at=intent.asof_timestamp,
        metadata={
            "source": "paper_order_v1",
            "is_simulated": True,
            "pretrade_action": pretrade_action.value,
        },
    )
    return order.model_copy(update={"paper_order_id": compute_paper_order_id(order)})


def _accepted_size(
    intent: TradeIntent,
    policy: PaperExecutionPolicy,
    pretrade_action: PreTradeAction,
    pretrade_final_size: Decimal,
) -> Decimal:
    if pretrade_action == PreTradeAction.ALLOW:
        return intent.requested_size_units
    if (
        pretrade_action == PreTradeAction.ALLOW_SMALLER_SIZE
        and policy.allow_pretrade_allow_smaller_size
    ):
        return min(intent.requested_size_units, pretrade_final_size)
    if pretrade_action == PreTradeAction.PASSIVE_ONLY and (
        policy.allow_pretrade_passive_only_for_passive_orders
        and intent.intent_type in {TradeIntentType.PASSIVE_LIMIT, TradeIntentType.RESEARCH_ONLY}
    ):
        return min(intent.requested_size_units, pretrade_final_size)
    return Decimal("0")


def _rejection_codes(
    intent: TradeIntent,
    policy: PaperExecutionPolicy,
    pretrade_action: PreTradeAction,
    accepted_size: Decimal,
) -> list[str]:
    codes: list[str] = []
    if pretrade_action == PreTradeAction.NO_TRADE and policy.reject_no_trade:
        codes.append("PRETRADE_NO_TRADE")
    elif pretrade_action == PreTradeAction.MANUAL_REVIEW and policy.reject_manual_review:
        codes.append("PRETRADE_MANUAL_REVIEW")
    elif pretrade_action == PreTradeAction.PASSIVE_ONLY and intent.intent_type in {
        TradeIntentType.AGGRESSIVE_LIMIT,
        TradeIntentType.MARKET_LIKE,
    }:
        codes.append("PRETRADE_PASSIVE_ONLY_BLOCKED_AGGRESSIVE_INTENT")
    elif policy.require_pretrade_allow and accepted_size <= Decimal("0"):
        codes.append("PRETRADE_ACTION_NOT_ACCEPTED")
    return codes

