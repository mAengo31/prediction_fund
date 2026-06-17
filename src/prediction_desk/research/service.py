"""Service layer for deterministic strategy research."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from prediction_desk.paper.service import PaperExecutionService, PaperServiceError
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.pretrade.enums import PreTradeAction
from prediction_desk.pretrade.service import PreTradeService, PreTradeServiceError
from prediction_desk.research.features import build_research_features
from prediction_desk.research.models import (
    ResearchAttributionReport,
    ResearchDecisionTrace,
    ResearchFeatureSnapshot,
    ResearchIntentProposal,
    ResearchRun,
    ResearchRunSummary,
    ResearchSignal,
    ResearchStrategyDefinition,
    compute_trace_input_hash,
    compute_trace_output_hash,
    research_object_id,
)
from prediction_desk.research.proposals import (
    proposal_to_trade_intent,
    validate_research_proposal,
)
from prediction_desk.research.strategies import (
    default_research_strategy_definitions,
    strategy_from_definition,
)


class ResearchServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class ResearchService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def create_default_research_strategies_if_missing(
        self,
    ) -> list[ResearchStrategyDefinition]:
        saved: list[ResearchStrategyDefinition] = []
        for definition in default_research_strategy_definitions():
            existing = self.repo.get_research_strategy_definition(
                definition.strategy_id
            )
            saved.append(
                existing
                if existing is not None
                else self.repo.save_research_strategy_definition(definition)
            )
        return saved

    def list_research_strategies(
        self,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchStrategyDefinition]:
        return self.repo.list_research_strategy_definitions(limit=limit, offset=offset)

    def get_research_strategy(self, strategy_id: str) -> ResearchStrategyDefinition:
        strategy = self.repo.get_research_strategy_definition(strategy_id)
        if strategy is None:
            raise ResearchServiceError("research_strategy_not_found")
        return strategy

    def build_features_for_market(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        include_sources: list[str] | None = None,
        force: bool = False,
    ) -> list[ResearchFeatureSnapshot]:
        return build_research_features(
            market_id,
            asof_timestamp,
            include_sources=include_sources,
            force=force,
            repo=self.repo,
        )

    def generate_research_signals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        strategy_ids: list[str] | None = None,
        force: bool = False,
    ) -> list[ResearchSignal]:
        signals, _ = self._generate(market_id, asof_timestamp, strategy_ids, force)
        return signals

    def generate_research_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        strategy_ids: list[str] | None = None,
        force: bool = False,
    ) -> list[ResearchIntentProposal]:
        _, proposals = self._generate(market_id, asof_timestamp, strategy_ids, force)
        return proposals

    def evaluate_research_proposal(
        self,
        proposal_id: str,
        *,
        enable_paper_simulation: bool = True,
        paper_policy_id: str | None = None,
        research_run_id: str | None = None,
        initial_cash_simulated: Decimal = Decimal("0"),
    ) -> ResearchDecisionTrace:
        proposal = self.repo.get_research_intent_proposal(proposal_id)
        if proposal is None:
            raise ResearchServiceError("research_proposal_not_found")
        validation_codes = validate_research_proposal(proposal)
        if validation_codes:
            raise ResearchServiceError(
                "invalid_research_proposal",
                ",".join(validation_codes),
            )
        intent = proposal_to_trade_intent(proposal)
        try:
            pretrade = PreTradeService(self.repo).check_pretrade_intent(intent)
        except PreTradeServiceError as exc:
            raise ResearchServiceError(exc.code, exc.message) from exc
        paper_result = None
        paper_reason_codes: list[str] = []
        action = pretrade.decision.action
        if (
            enable_paper_simulation
            and proposal.paper_simulation_allowed
            and action
            not in {
                PreTradeAction.NO_TRADE,
                PreTradeAction.MANUAL_REVIEW,
            }
        ):
            try:
                paper_result = PaperExecutionService(self.repo).simulate_trade_intent(
                    intent,
                    paper_policy_id=paper_policy_id,
                    simulation_run_id=research_run_id,
                    initial_cash_simulated=initial_cash_simulated,
                )
            except PaperServiceError as exc:
                paper_reason_codes.append(exc.code)
        trace = _trace_from_evaluation(
            proposal=proposal,
            research_run_id=research_run_id,
            trade_intent_id=intent.trade_intent_id,
            pretrade_decision_id=pretrade.decision.pretrade_decision_id,
            pretrade_action=pretrade.decision.action.value,
            pretrade_final_allowed_size_units=pretrade.decision.final_allowed_size_units,
            paper_result=paper_result,
            paper_reason_codes=paper_reason_codes,
        )
        return self.repo.save_research_decision_trace(trace)

    def list_research_signals(
        self,
        *,
        market_id: str | None = None,
        strategy_id: str | None = None,
        signal_type: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchSignal]:
        return self.repo.list_research_signals(
            market_id=market_id,
            strategy_id=strategy_id,
            signal_type=signal_type,
            limit=limit,
            offset=offset,
        )

    def list_research_proposals(
        self,
        *,
        market_id: str | None = None,
        strategy_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchIntentProposal]:
        return self.repo.list_research_intent_proposals(
            market_id=market_id,
            strategy_id=strategy_id,
            limit=limit,
            offset=offset,
        )

    def list_research_traces(
        self,
        *,
        market_id: str | None = None,
        strategy_id: str | None = None,
        research_run_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[ResearchDecisionTrace]:
        return self.repo.list_research_decision_traces(
            market_id=market_id,
            strategy_id=strategy_id,
            research_run_id=research_run_id,
            limit=limit,
            offset=offset,
        )

    def get_research_run(self, research_run_id: str) -> ResearchRun:
        run = self.repo.get_research_run(research_run_id)
        if run is None:
            raise ResearchServiceError("research_run_not_found")
        return run

    def get_research_run_summary(self, research_run_id: str) -> ResearchRunSummary:
        summary = self.repo.get_research_run_summary(research_run_id)
        if summary is None:
            raise ResearchServiceError("research_run_summary_not_found")
        return summary

    def get_research_attribution_report(
        self,
        research_run_id: str,
    ) -> ResearchAttributionReport:
        report = self.repo.get_research_attribution_report(research_run_id)
        if report is None:
            raise ResearchServiceError("research_attribution_not_found")
        return report

    def _generate(
        self,
        market_id: str,
        asof_timestamp: datetime,
        strategy_ids: list[str] | None,
        force: bool,
    ) -> tuple[list[ResearchSignal], list[ResearchIntentProposal]]:
        features = self.build_features_for_market(
            market_id,
            asof_timestamp,
            force=force,
        )
        definitions = _resolve_strategy_definitions(self.repo, strategy_ids)
        saved_signals: list[ResearchSignal] = []
        saved_proposals: list[ResearchIntentProposal] = []
        for definition in definitions:
            result = strategy_from_definition(definition).generate_signals_and_proposals(
                market_id,
                asof_timestamp,
                features,
                definition.config,
            )
            signal_map: dict[str, ResearchSignal] = {}
            for signal in result.signals:
                existing_signal = self.repo.find_research_signal_by_hash(signal.output_hash)
                saved = (
                    existing_signal
                    if existing_signal is not None and not force
                    else self.repo.save_research_signal(signal)
                )
                signal_map[signal.research_signal_id] = saved
                saved_signals.append(saved)
            for proposal_item in result.proposals:
                proposal = proposal_item
                signal_id = proposal.research_signal_id
                if signal_id in signal_map:
                    proposal = proposal.model_copy(
                        update={"research_signal_id": signal_map[signal_id].research_signal_id}
                    )
                existing_proposal = self.repo.find_research_intent_proposal_by_hash(
                    proposal.output_hash
                )
                saved_proposals.append(
                    existing_proposal
                    if existing_proposal is not None and not force
                    else self.repo.save_research_intent_proposal(proposal)
                )
        return saved_signals, saved_proposals


def create_default_research_strategies_if_missing(
    *,
    database_url: str | None = None,
) -> list[ResearchStrategyDefinition]:
    with session_scope(database_url) as session:
        return ResearchService(
            PredictionMarketRepository(session)
        ).create_default_research_strategies_if_missing()


def _resolve_strategy_definitions(
    repo: PredictionMarketRepository,
    strategy_ids: list[str] | None,
) -> list[ResearchStrategyDefinition]:
    if strategy_ids is None:
        definitions = repo.list_research_strategy_definitions(limit=1000)
        if not definitions:
            service = ResearchService(repo)
            definitions = service.create_default_research_strategies_if_missing()
        return [definition for definition in definitions if definition.is_active]
    definitions = []
    for strategy_id in strategy_ids:
        definition = repo.get_research_strategy_definition(strategy_id)
        if definition is None:
            raise ResearchServiceError("research_strategy_not_found", strategy_id)
        definitions.append(definition)
    return definitions


def _trace_from_evaluation(
    *,
    proposal: ResearchIntentProposal,
    research_run_id: str | None,
    trade_intent_id: str,
    pretrade_decision_id: str,
    pretrade_action: str,
    pretrade_final_allowed_size_units: Decimal,
    paper_result: object | None,
    paper_reason_codes: list[str],
) -> ResearchDecisionTrace:
    paper_order = getattr(paper_result, "order", None) if paper_result else None
    fills = list(getattr(paper_result, "fills", []) if paper_result else [])
    position = getattr(paper_result, "position_snapshot", None) if paper_result else None
    portfolio = getattr(paper_result, "portfolio_snapshot", None) if paper_result else None
    filled_size = sum((fill.size_units for fill in fills), Decimal("0"))
    notional = sum((fill.notional for fill in fills), Decimal("0"))
    avg_fill = notional / filled_size if filled_size > Decimal("0") else None
    input_hash = compute_trace_input_hash(
        proposal,
        pretrade_decision_id,
        paper_order.paper_order_id if paper_order else None,
        [fill.paper_fill_id for fill in fills],
    )
    reason_codes = sorted(
        set(
            list(proposal.reason_codes)
            + paper_reason_codes
            + (list(paper_order.rejection_reason_codes) if paper_order else [])
        )
    )
    trace = ResearchDecisionTrace(
        trace_id=research_object_id("research_trace", {"input_hash": input_hash}),
        research_run_id=research_run_id,
        strategy_id=proposal.strategy_id,
        market_id=proposal.market_id,
        asof_timestamp=proposal.asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=proposal.asof_timestamp,
        research_signal_id=proposal.research_signal_id,
        proposal_id=proposal.proposal_id,
        trade_intent_id=trade_intent_id,
        pretrade_decision_id=pretrade_decision_id,
        paper_order_id=paper_order.paper_order_id if paper_order else None,
        paper_fill_ids=[fill.paper_fill_id for fill in fills],
        paper_position_snapshot_id=(
            position.position_snapshot_id if position is not None else None
        ),
        paper_portfolio_snapshot_id=(
            portfolio.portfolio_snapshot_id if portfolio is not None else None
        ),
        pretrade_action=pretrade_action,
        paper_order_status=paper_order.status.value if paper_order else None,
        filled_size_units_simulated=filled_size,
        avg_fill_price_simulated=avg_fill,
        reason_codes=reason_codes,
        input_hash=input_hash,
        output_hash="pending",
        metadata={
            "pretrade_final_allowed_size_units": str(pretrade_final_allowed_size_units),
            "paper_total_equity_simulated": (
                str(portfolio.total_equity_simulated) if portfolio else None
            ),
            "paper_realized_pnl_simulated": (
                str(portfolio.realized_pnl_simulated) if portfolio else None
            ),
            "paper_unrealized_pnl_simulated": (
                str(portfolio.unrealized_pnl_simulated) if portfolio else None
            ),
        },
    )
    return trace.model_copy(update={"output_hash": compute_trace_output_hash(trace)})
