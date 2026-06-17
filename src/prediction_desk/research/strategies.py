"""Deterministic v1 research strategies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol, cast

from prediction_desk.pretrade.enums import TradeIntentType, TradeSide
from prediction_desk.research.enums import (
    ResearchActionBias,
    ResearchFeatureSource,
    ResearchSignalType,
    ResearchStrategyFamily,
)
from prediction_desk.research.models import (
    BASELINE_STRATEGY_ID,
    COMPOSITE_STRATEGY_ID,
    DIVERGENCE_STRATEGY_ID,
    INTEGRITY_PASS_STRATEGY_ID,
    TRUST_ALLOW_STRATEGY_ID,
    ResearchFeatureSnapshot,
    ResearchIntentProposal,
    ResearchSignal,
    ResearchStrategyDefinition,
    compute_proposal_input_hash,
    compute_proposal_output_hash,
    compute_signal_input_hash,
    compute_signal_output_hash,
    research_object_id,
)


@dataclass(frozen=True)
class StrategyResult:
    signals: list[ResearchSignal]
    proposals: list[ResearchIntentProposal]


class ResearchStrategy(Protocol):
    definition: ResearchStrategyDefinition

    def generate_signals_and_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        config: dict[str, Any] | None = None,
    ) -> StrategyResult:
        """Generates deterministic research signals and hypothetical proposals."""


def default_research_strategy_definitions(
    created_at: datetime | None = None,
) -> list[ResearchStrategyDefinition]:
    now = created_at or datetime.now(tz=UTC)
    return [
        ResearchStrategyDefinition(
            strategy_id=BASELINE_STRATEGY_ID,
            strategy_name="baseline_research_only_v1",
            strategy_version="v1",
            created_at=now,
            family=ResearchStrategyFamily.BASELINE,
            description="Baseline plumbing strategy that creates research-only proposals.",
            requires_pretrade=True,
            allows_paper_simulation=True,
            default_requested_size_units=Decimal("1"),
            default_intent_type=TradeIntentType.RESEARCH_ONLY.value,
            default_strategy_context="RESEARCH",
            config={},
        ),
        ResearchStrategyDefinition(
            strategy_id=TRUST_ALLOW_STRATEGY_ID,
            strategy_name="trust_verdict_allow_filter_v1",
            strategy_version="v1",
            created_at=now,
            family=ResearchStrategyFamily.TRUST_VERDICT_FILTER,
            description="Allows research proposals only when trust verdict action permits.",
            requires_pretrade=True,
            allows_paper_simulation=True,
            default_requested_size_units=Decimal("1"),
            default_intent_type=TradeIntentType.RESEARCH_ONLY.value,
            default_strategy_context="RESEARCH",
            config={},
        ),
        ResearchStrategyDefinition(
            strategy_id=INTEGRITY_PASS_STRATEGY_ID,
            strategy_name="integrity_pass_filter_v1",
            strategy_version="v1",
            created_at=now,
            family=ResearchStrategyFamily.INTEGRITY_FILTER,
            description="Allows research proposals when integrity risk context passes.",
            requires_pretrade=True,
            allows_paper_simulation=True,
            default_requested_size_units=Decimal("1"),
            default_intent_type=TradeIntentType.RESEARCH_ONLY.value,
            default_strategy_context="RESEARCH",
            config={"max_integrity_risk": 50},
        ),
        ResearchStrategyDefinition(
            strategy_id=DIVERGENCE_STRATEGY_ID,
            strategy_name="divergence_research_hypothesis_v1",
            strategy_version="v1",
            created_at=now,
            family=ResearchStrategyFamily.DIVERGENCE_RESEARCH,
            description="Creates hypothetical research proposals from reviewed divergence context.",
            requires_pretrade=True,
            allows_paper_simulation=True,
            default_requested_size_units=Decimal("1"),
            default_intent_type=TradeIntentType.RESEARCH_ONLY.value,
            default_strategy_context="CROSS_VENUE_COMPARISON",
            config={},
        ),
        ResearchStrategyDefinition(
            strategy_id=COMPOSITE_STRATEGY_ID,
            strategy_name="composite_conservative_research_v1",
            strategy_version="v1",
            created_at=now,
            family=ResearchStrategyFamily.COMPOSITE_RULE_BASED,
            description="Conservative composite filter across trust, quality, and integrity.",
            requires_pretrade=True,
            allows_paper_simulation=True,
            default_requested_size_units=Decimal("1"),
            default_intent_type=TradeIntentType.RESEARCH_ONLY.value,
            default_strategy_context="RESEARCH",
            config={"min_quality_score": 70, "max_integrity_risk": 50},
        ),
    ]


def strategy_from_definition(definition: ResearchStrategyDefinition) -> ResearchStrategy:
    strategies: dict[str, type[_BaseStrategy]] = {
        "baseline_research_only_v1": BaselineResearchOnlyStrategy,
        "trust_verdict_allow_filter_v1": TrustVerdictAllowFilterStrategy,
        "integrity_pass_filter_v1": IntegrityPassFilterStrategy,
        "divergence_research_hypothesis_v1": DivergenceResearchHypothesisStrategy,
        "composite_conservative_research_v1": CompositeConservativeResearchStrategy,
    }
    return cast(
        ResearchStrategy,
        strategies.get(definition.strategy_name, BaselineResearchOnlyStrategy)(definition),
    )


class _BaseStrategy:
    def __init__(self, definition: ResearchStrategyDefinition) -> None:
        self.definition = definition

    def _signal(
        self,
        *,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        signal_type: ResearchSignalType,
        action_bias: ResearchActionBias,
        reason_codes: list[str],
        strength: int,
        confidence: int,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchSignal:
        generated_at = datetime.now(tz=UTC)
        feature_hashes = [feature.output_hash for feature in features]
        input_hash = compute_signal_input_hash(
            self.definition,
            market_id,
            asof_timestamp,
            feature_hashes,
            signal_type,
        )
        signal = ResearchSignal(
            research_signal_id=research_object_id(
                "research_signal",
                {"input_hash": input_hash, "reason_codes": sorted(reason_codes)},
            ),
            strategy_id=self.definition.strategy_id,
            strategy_name=self.definition.strategy_name,
            strategy_version=self.definition.strategy_version,
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            generated_at=generated_at,
            available_at=asof_timestamp,
            signal_type=signal_type,
            signal_strength_score=strength,
            confidence_score=confidence,
            action_bias=action_bias,
            reason_codes=sorted(set(reason_codes)),
            source_feature_ids=[
                feature.research_feature_snapshot_id for feature in features
            ],
            source_ref_ids=sorted(
                {
                    ref_id
                    for feature in features
                    for ref_id in feature.source_ref_ids
                }
            ),
            input_hash=input_hash,
            output_hash="pending",
            metadata=metadata or {},
        )
        return signal.model_copy(update={"output_hash": compute_signal_output_hash(signal)})

    def _proposal(
        self,
        *,
        signal: ResearchSignal,
        market_id: str,
        asof_timestamp: datetime,
        side: TradeSide = TradeSide.BUY,
        outcome_id: str | None = None,
        venue_id: str | None = None,
        requested_price: Decimal | None = None,
        intent_type: str | None = None,
        strategy_context: str | None = None,
        reason_codes: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ResearchIntentProposal:
        generated_at = datetime.now(tz=UTC)
        reason_codes = sorted(set(reason_codes or []))
        input_hash = compute_proposal_input_hash(
            self.definition,
            signal,
            market_id,
            asof_timestamp,
            [signal.research_signal_id],
        )
        proposal = ResearchIntentProposal(
            proposal_id=research_object_id(
                "research_proposal",
                {"input_hash": input_hash, "reason_codes": reason_codes},
            ),
            strategy_id=self.definition.strategy_id,
            strategy_name=self.definition.strategy_name,
            strategy_version=self.definition.strategy_version,
            research_signal_id=signal.research_signal_id,
            market_id=market_id,
            outcome_id=outcome_id,
            venue_id=venue_id,
            asof_timestamp=asof_timestamp,
            generated_at=generated_at,
            available_at=asof_timestamp,
            side=side,
            intent_type=intent_type or self.definition.default_intent_type,
            strategy_context=strategy_context or self.definition.default_strategy_context,
            requested_price=requested_price,
            requested_size_units=self.definition.default_requested_size_units,
            requested_notional_usd=None,
            pretrade_required=self.definition.requires_pretrade,
            paper_simulation_allowed=self.definition.allows_paper_simulation,
            reason_codes=reason_codes,
            source_signal_ids=[signal.research_signal_id],
            input_hash=input_hash,
            output_hash="pending",
            metadata=metadata or {},
        )
        return proposal.model_copy(
            update={"output_hash": compute_proposal_output_hash(proposal)}
        )


class BaselineResearchOnlyStrategy(_BaseStrategy):
    def generate_signals_and_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        config: dict[str, Any] | None = None,
    ) -> StrategyResult:
        del config
        signal = self._signal(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            features=features,
            signal_type=ResearchSignalType.REVIEW_ONLY,
            action_bias=ResearchActionBias.RESEARCH_ONLY,
            reason_codes=["BASELINE_RESEARCH_ONLY"],
            strength=10,
            confidence=50,
        )
        proposal = self._proposal(
            signal=signal,
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            reason_codes=["BASELINE_RESEARCH_ONLY"],
        )
        return StrategyResult(signals=[signal], proposals=[proposal])


class TrustVerdictAllowFilterStrategy(_BaseStrategy):
    def generate_signals_and_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        config: dict[str, Any] | None = None,
    ) -> StrategyResult:
        del config
        trust_action = _values(features, ResearchFeatureSource.RESOLUTION).get(
            "trust_action"
        )
        if trust_action in {"ALLOW", "ALLOW_SMALLER_SIZE"}:
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.FILTER_ALLOW,
                action_bias=ResearchActionBias.RESEARCH_ONLY,
                reason_codes=["TRUST_VERDICT_ALLOWED"],
                strength=60,
                confidence=70,
            )
            return StrategyResult(
                signals=[signal],
                proposals=[
                    self._proposal(
                        signal=signal,
                        market_id=market_id,
                        asof_timestamp=asof_timestamp,
                        reason_codes=["TRUST_VERDICT_ALLOWED"],
                    )
                ],
            )
        if trust_action == "PASSIVE_ONLY":
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.WATCH,
                action_bias=ResearchActionBias.RESEARCH_ONLY,
                reason_codes=["TRUST_VERDICT_PASSIVE_ONLY"],
                strength=40,
                confidence=65,
            )
            return StrategyResult(
                signals=[signal],
                proposals=[
                    self._proposal(
                        signal=signal,
                        market_id=market_id,
                        asof_timestamp=asof_timestamp,
                        intent_type=TradeIntentType.PASSIVE_LIMIT.value,
                        reason_codes=["TRUST_VERDICT_PASSIVE_ONLY"],
                    )
                ],
            )
        reason = "NO_TRUST_VERDICT" if trust_action is None else "TRUST_VERDICT_BLOCKED"
        signal = self._signal(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            features=features,
            signal_type=ResearchSignalType.FILTER_BLOCK
            if trust_action in {"NO_TRADE", "MANUAL_REVIEW"}
            else ResearchSignalType.REVIEW_ONLY,
            action_bias=ResearchActionBias.BLOCK
            if trust_action in {"NO_TRADE", "MANUAL_REVIEW"}
            else ResearchActionBias.REVIEW_ONLY,
            reason_codes=[reason],
            strength=80,
            confidence=70 if trust_action else 30,
        )
        return StrategyResult(signals=[signal], proposals=[])


class IntegrityPassFilterStrategy(_BaseStrategy):
    def generate_signals_and_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        config: dict[str, Any] | None = None,
    ) -> StrategyResult:
        values = _values(features, ResearchFeatureSource.INTEGRITY)
        action_hint = values.get("action_hint")
        risk = values.get("overall_risk_score")
        max_risk = int((config or self.definition.config).get("max_integrity_risk", 50))
        if action_hint is None:
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.REVIEW_ONLY,
                action_bias=ResearchActionBias.REVIEW_ONLY,
                reason_codes=["MISSING_INTEGRITY_ASSESSMENT"],
                strength=50,
                confidence=25,
            )
            return StrategyResult(signals=[signal], proposals=[])
        if action_hint in {"NO_TRADE", "MANUAL_REVIEW"}:
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.FILTER_BLOCK,
                action_bias=ResearchActionBias.BLOCK,
                reason_codes=["INTEGRITY_ACTION_HINT_BLOCKED"],
                strength=85,
                confidence=75,
            )
            return StrategyResult(signals=[signal], proposals=[])
        signal = self._signal(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            features=features,
            signal_type=ResearchSignalType.FILTER_ALLOW
            if risk is not None and int(risk) < max_risk
            else ResearchSignalType.WATCH,
            action_bias=ResearchActionBias.RESEARCH_ONLY,
            reason_codes=["INTEGRITY_CONTEXT_PASSED"],
            strength=55,
            confidence=70,
        )
        proposal = self._proposal(
            signal=signal,
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            intent_type=TradeIntentType.PASSIVE_LIMIT.value
            if action_hint == "PASSIVE_ONLY"
            else self.definition.default_intent_type,
            reason_codes=["INTEGRITY_CONTEXT_PASSED"],
        )
        return StrategyResult(signals=[signal], proposals=[proposal])


class DivergenceResearchHypothesisStrategy(_BaseStrategy):
    def generate_signals_and_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        config: dict[str, Any] | None = None,
    ) -> StrategyResult:
        del config
        values = _values(features, ResearchFeatureSource.DIVERGENCE)
        statuses = set(values.get("statuses", []))
        if "DO_NOT_COMPARE" in statuses or "NEEDS_REVIEW" in statuses:
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.REVIEW_ONLY,
                action_bias=ResearchActionBias.REVIEW_ONLY,
                reason_codes=["DIVERGENCE_CONTEXT_REQUIRES_REVIEW"],
                strength=70,
                confidence=55,
            )
            return StrategyResult(signals=[signal], proposals=[])
        if not statuses.intersection({"WATCH", "MATERIAL_DIVERGENCE"}):
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.PASS,
                action_bias=ResearchActionBias.NONE,
                reason_codes=["NO_RESEARCH_DIVERGENCE_CONTEXT"],
                strength=5,
                confidence=50,
            )
            return StrategyResult(signals=[signal], proposals=[])
        lower = _lower_side_from_feature(values, market_id)
        if lower is None:
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.REVIEW_ONLY,
                action_bias=ResearchActionBias.REVIEW_ONLY,
                reason_codes=["LOWER_SIDE_UNDETERMINED"],
                strength=45,
                confidence=35,
            )
            return StrategyResult(signals=[signal], proposals=[])
        signal = self._signal(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            features=features,
            signal_type=ResearchSignalType.HYPOTHETICAL_INTENT,
            action_bias=ResearchActionBias.HYPOTHETICAL_BUY,
            reason_codes=["DIVERGENCE_RESEARCH_HYPOTHESIS"],
            strength=65,
            confidence=60,
            metadata={"lower_side_market_id": lower["market_id"]},
        )
        proposal = self._proposal(
            signal=signal,
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            side=TradeSide.BUY,
            venue_id=lower.get("venue_id"),
            outcome_id=lower.get("outcome_id"),
            requested_price=lower.get("reference_price"),
            reason_codes=["DIVERGENCE_RESEARCH_HYPOTHESIS"],
            metadata={"lower_side": lower},
        )
        return StrategyResult(signals=[signal], proposals=[proposal])


class CompositeConservativeResearchStrategy(_BaseStrategy):
    def generate_signals_and_proposals(
        self,
        market_id: str,
        asof_timestamp: datetime,
        features: list[ResearchFeatureSnapshot],
        config: dict[str, Any] | None = None,
    ) -> StrategyResult:
        cfg = {**self.definition.config, **(config or {})}
        trust = _values(features, ResearchFeatureSource.RESOLUTION)
        market_data = _values(features, ResearchFeatureSource.MARKET_DATA)
        integrity = _values(features, ResearchFeatureSource.INTEGRITY)
        divergence = _values(features, ResearchFeatureSource.DIVERGENCE)
        pretrade = _values(features, ResearchFeatureSource.PRETRADE)
        blockers: list[str] = []
        if trust.get("trust_action") not in {"ALLOW", "ALLOW_SMALLER_SIZE"}:
            blockers.append("TRUST_VERDICT_NOT_ALLOWED")
        quality = market_data.get("quality_score")
        if quality is not None and int(quality) < int(cfg.get("min_quality_score", 70)):
            blockers.append("MARKET_DATA_QUALITY_BELOW_THRESHOLD")
        risk = integrity.get("overall_risk_score")
        if risk is not None and int(risk) >= int(cfg.get("max_integrity_risk", 50)):
            blockers.append("INTEGRITY_RISK_ABOVE_THRESHOLD")
        if pretrade.get("action") == "NO_TRADE":
            blockers.append("LATEST_PRETRADE_NO_TRADE")
        if divergence.get("needs_review_count", 0) or divergence.get(
            "do_not_compare_count",
            0,
        ):
            blockers.append("DIVERGENCE_CONTEXT_BLOCKED")
        if blockers:
            signal = self._signal(
                market_id=market_id,
                asof_timestamp=asof_timestamp,
                features=features,
                signal_type=ResearchSignalType.REVIEW_ONLY,
                action_bias=ResearchActionBias.REVIEW_ONLY,
                reason_codes=blockers,
                strength=70,
                confidence=60,
            )
            return StrategyResult(signals=[signal], proposals=[])
        signal = self._signal(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            features=features,
            signal_type=ResearchSignalType.FILTER_ALLOW,
            action_bias=ResearchActionBias.RESEARCH_ONLY,
            reason_codes=["COMPOSITE_CONSERVATIVE_PASSED"],
            strength=55,
            confidence=75,
        )
        proposal = self._proposal(
            signal=signal,
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            reason_codes=["COMPOSITE_CONSERVATIVE_PASSED"],
        )
        return StrategyResult(signals=[signal], proposals=[proposal])


def _values(
    features: list[ResearchFeatureSnapshot],
    source: ResearchFeatureSource,
) -> dict[str, Any]:
    for feature in features:
        if feature.feature_source == source:
            return dict(feature.values)
    return {}


def _lower_side_from_feature(
    values: dict[str, Any],
    market_id: str,
) -> dict[str, Any] | None:
    for item in values.get("lower_side_inputs", []):
        if item.get("status") not in {"WATCH", "MATERIAL_DIVERGENCE"}:
            continue
        left = item.get("left_price")
        right = item.get("right_price_aligned")
        if left is None or right is None:
            continue
        left_dec = Decimal(str(left))
        right_dec = Decimal(str(right))
        if left_dec < right_dec and item.get("left_market_id") == market_id:
            return {
                "market_id": item.get("left_market_id"),
                "venue_id": item.get("left_venue_id"),
                "outcome_id": item.get("left_outcome_id"),
                "reference_price": left_dec,
            }
        if right_dec < left_dec and item.get("right_market_id") == market_id:
            return {
                "market_id": item.get("right_market_id"),
                "venue_id": item.get("right_venue_id"),
                "outcome_id": item.get("right_outcome_id"),
                "reference_price": right_dec,
            }
    return None
