"""Service layer for deterministic cross-venue equivalence."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.domain.models import MarketRuleSnapshot
from prediction_desk.equivalence.aggregation import aggregate_equivalence_dimensions
from prediction_desk.equivalence.dimensions import (
    map_outcomes,
    score_ambiguity_compatibility,
    score_event_identity,
    score_outcome_structure,
    score_predicate_similarity,
    score_resolution_source_alignment,
    score_settlement_authority_alignment,
    score_temporal_alignment,
    score_threshold_alignment,
    score_timezone_alignment,
    score_title_similarity,
    score_venue_rule_compatibility,
)
from prediction_desk.equivalence.enums import (
    ComparisonPermission,
    EquivalenceClassStatus,
    EquivalenceStatus,
)
from prediction_desk.equivalence.matching import generate_equivalence_candidates
from prediction_desk.equivalence.models import (
    EquivalenceAssessmentResponse,
    EquivalenceCandidate,
    EquivalenceClass,
    MarketEquivalenceAssessment,
    OutcomeEquivalenceMapping,
    compute_class_id_payload,
    hash_payload,
)
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.resolution.models import ResolutionAnalysis
from prediction_desk.resolution.service import ResolutionCorpusError, ResolutionCorpusService


class EquivalenceServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class EquivalenceService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def assess_market_equivalence(
        self,
        left_market_id: str,
        right_market_id: str,
        asof_timestamp: datetime,
        *,
        force: bool = False,
        config: dict[str, Any] | None = None,
    ) -> EquivalenceAssessmentResponse:
        if left_market_id == right_market_id:
            raise EquivalenceServiceError("same_market_pair")
        left_market = self.repo.get_market(left_market_id)
        right_market = self.repo.get_market(right_market_id)
        if left_market is None or right_market is None:
            raise EquivalenceServiceError("market_not_found")

        left_rule = self.repo.get_latest_rule_snapshot_asof(left_market_id, asof_timestamp)
        right_rule = self.repo.get_latest_rule_snapshot_asof(right_market_id, asof_timestamp)
        left_analysis = self._resolution_analysis_asof(left_market_id, left_rule, asof_timestamp)
        right_analysis = self._resolution_analysis_asof(right_market_id, right_rule, asof_timestamp)
        left_outcomes = self.repo.list_outcomes(left_market_id)
        right_outcomes = self.repo.list_outcomes(right_market_id)
        outcome_mappings = map_outcomes(left_outcomes, right_outcomes, left_market, right_market)

        dimensions = {
            "title_similarity": score_title_similarity(left_market, right_market),
            "event_identity": score_event_identity(
                self.repo.get_event(left_market.event_id),
                self.repo.get_event(right_market.event_id),
                left_market,
                right_market,
            ),
            "outcome_structure": score_outcome_structure(
                left_market,
                right_market,
                left_outcomes,
                right_outcomes,
            ),
            "predicate_similarity": score_predicate_similarity(
                left_analysis.predicate if left_analysis else None,
                right_analysis.predicate if right_analysis else None,
            ),
            "resolution_source": score_resolution_source_alignment(
                left_rule,
                right_rule,
                left_analysis.predicate if left_analysis else None,
                right_analysis.predicate if right_analysis else None,
            ),
            "settlement_authority": score_settlement_authority_alignment(
                left_rule,
                right_rule,
                left_analysis.predicate if left_analysis else None,
                right_analysis.predicate if right_analysis else None,
            ),
            "temporal_alignment": score_temporal_alignment(
                left_analysis.predicate if left_analysis else None,
                right_analysis.predicate if right_analysis else None,
                left_rule,
                right_rule,
            ),
            "threshold_alignment": score_threshold_alignment(
                left_analysis.predicate if left_analysis else None,
                right_analysis.predicate if right_analysis else None,
            ),
            "timezone_alignment": score_timezone_alignment(
                left_analysis.predicate if left_analysis else None,
                right_analysis.predicate if right_analysis else None,
                left_rule,
                right_rule,
            ),
            "ambiguity_compatibility": score_ambiguity_compatibility(
                left_analysis.ambiguity_assessment if left_analysis else None,
                right_analysis.ambiguity_assessment if right_analysis else None,
            ),
            "venue_rule_compatibility": score_venue_rule_compatibility(left_rule, right_rule),
        }
        assessment = aggregate_equivalence_dimensions(
            left_market=left_market,
            right_market=right_market,
            asof_timestamp=asof_timestamp,
            dimensions=dimensions,
            outcome_mappings=outcome_mappings,
            left_rule_snapshot=left_rule,
            right_rule_snapshot=right_rule,
            left_predicate=left_analysis.predicate if left_analysis else None,
            right_predicate=right_analysis.predicate if right_analysis else None,
            left_ambiguity=left_analysis.ambiguity_assessment if left_analysis else None,
            right_ambiguity=right_analysis.ambiguity_assessment if right_analysis else None,
            metadata=config or {},
        )
        existing = self.repo.find_equivalence_assessment_by_hash(assessment.output_hash)
        if existing is not None and not force:
            mappings = self.repo.list_outcome_equivalence_mappings(
                existing.equivalence_assessment_id
            )
            return EquivalenceAssessmentResponse(assessment=existing, outcome_mappings=mappings)

        saved = self.repo.save_market_equivalence_assessment(assessment)
        saved_mappings = [
            self.repo.save_outcome_equivalence_mapping(
                _mapping_for_assessment(mapping, saved.equivalence_assessment_id)
            )
            for mapping in outcome_mappings
        ]
        return EquivalenceAssessmentResponse(assessment=saved, outcome_mappings=saved_mappings)

    def generate_candidates(
        self,
        asof_timestamp: datetime,
        *,
        market_ids: list[str] | None = None,
        venue_names: list[str] | None = None,
        min_candidate_score: int = 40,
        max_pairs: int = 10000,
        force: bool = False,
    ) -> list[EquivalenceCandidate]:
        return generate_equivalence_candidates(
            repo=self.repo,
            market_ids=market_ids,
            asof_timestamp=asof_timestamp,
            venue_names=venue_names,
            min_candidate_score=min_candidate_score,
            max_pairs=max_pairs,
            force=force,
        )

    def assess_candidates(
        self,
        candidate_ids: list[str],
        *,
        force: bool = False,
    ) -> list[EquivalenceAssessmentResponse]:
        responses: list[EquivalenceAssessmentResponse] = []
        for candidate_id in candidate_ids:
            candidate = self.repo.get_equivalence_candidate(candidate_id)
            if candidate is None:
                raise EquivalenceServiceError("equivalence_candidate_not_found")
            responses.append(
                self.assess_market_equivalence(
                    candidate.left_market_id,
                    candidate.right_market_id,
                    candidate.asof_timestamp,
                    force=force,
                )
            )
        return responses

    def build_equivalence_classes(
        self,
        asof_timestamp: datetime,
        *,
        min_score: int = 85,
        market_ids: list[str] | None = None,
        force: bool = False,
    ) -> list[EquivalenceClass]:
        del force
        assessments = self.repo.list_equivalence_assessments(
            market_id=None,
            limit=10000,
            offset=0,
        )
        eligible = [
            assessment
            for assessment in assessments
            if _as_utc(assessment.available_at) <= _as_utc(asof_timestamp)
            and assessment.overall_score >= min_score
            and assessment.comparison_permission
            in {
                ComparisonPermission.COMPARABLE,
                ComparisonPermission.COMPARABLE_WITH_HAIRCUT,
            }
            and (market_ids is None or _pair_intersects(assessment, market_ids))
        ]
        components = _connected_components(eligible)
        classes: list[EquivalenceClass] = []
        for component_markets, component_assessments in components:
            if len(component_markets) < 2:
                continue
            scores = [assessment.overall_score for assessment in component_assessments]
            permissions = {assessment.comparison_permission for assessment in component_assessments}
            status = (
                EquivalenceClassStatus.ACTIVE
                if permissions == {ComparisonPermission.COMPARABLE}
                else EquivalenceClassStatus.NEEDS_REVIEW
            )
            permission = (
                ComparisonPermission.COMPARABLE
                if permissions == {ComparisonPermission.COMPARABLE}
                else ComparisonPermission.COMPARABLE_WITH_HAIRCUT
            )
            average = sum(Decimal(score) for score in scores) / Decimal(len(scores))
            representative_title = self._representative_title(component_markets)
            equivalence_class = EquivalenceClass(
                equivalence_class_id="pending",
                asof_timestamp=asof_timestamp,
                created_at=datetime.now(tz=UTC),
                status=status,
                representative_title=representative_title,
                market_ids=sorted(component_markets),
                assessment_ids=sorted(
                    assessment.equivalence_assessment_id
                    for assessment in component_assessments
                ),
                min_pair_score=min(scores),
                average_pair_score=average,
                confidence_score=round(
                    sum(assessment.confidence_score for assessment in component_assessments)
                    / len(component_assessments)
                ),
                comparison_permission=permission,
                reason_codes=sorted(
                    {
                        code
                        for assessment in component_assessments
                        for code in assessment.reason_codes
                    }
                ),
                metadata={"class_builder": "connected_components_v1"},
            )
            digest = hash_payload(compute_class_id_payload(equivalence_class))
            saved = self.repo.save_equivalence_class(
                equivalence_class.model_copy(
                    update={"equivalence_class_id": f"equivalence_class_{digest[:24]}"}
                )
            )
            classes.append(saved)
        return classes

    def get_latest_equivalence_assessment(
        self,
        left_market_id: str,
        right_market_id: str,
        asof_timestamp: datetime | None = None,
    ) -> MarketEquivalenceAssessment:
        assessment = self.repo.get_latest_equivalence_assessment_asof(
            left_market_id,
            right_market_id,
            asof_timestamp or datetime.now(tz=UTC),
        )
        if assessment is None:
            raise EquivalenceServiceError("equivalence_assessment_not_found")
        return assessment

    def list_equivalence_assessments(
        self,
        *,
        market_id: str | None = None,
        status: EquivalenceStatus | None = None,
        permission: ComparisonPermission | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketEquivalenceAssessment]:
        return self.repo.list_equivalence_assessments(
            market_id=market_id,
            status=status,
            permission=permission,
            limit=limit,
            offset=offset,
        )

    def list_equivalence_candidates(
        self,
        *,
        market_id: str | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[EquivalenceCandidate]:
        return self.repo.list_equivalence_candidates(
            market_id=market_id,
            limit=limit,
            offset=offset,
        )

    def list_equivalence_classes(
        self,
        *,
        asof_timestamp: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[EquivalenceClass]:
        return self.repo.list_equivalence_classes(
            asof_timestamp=asof_timestamp,
            limit=limit,
            offset=offset,
        )

    def _resolution_analysis_asof(
        self,
        market_id: str,
        rule_snapshot: MarketRuleSnapshot | None,
        asof_timestamp: datetime,
    ) -> ResolutionAnalysis | None:
        if rule_snapshot is None:
            return None
        existing = self.repo.get_latest_resolution_analysis_asof(market_id, asof_timestamp)
        if (
            existing is not None
            and existing.rule_snapshot.rule_snapshot_id == rule_snapshot.rule_snapshot_id
        ):
            return existing
        try:
            return ResolutionCorpusService(self.repo).analyze_rule_snapshot(
                market_id,
                rule_snapshot.rule_snapshot_id,
            )
        except ResolutionCorpusError:
            return None

    def _representative_title(self, market_ids: set[str]) -> str | None:
        markets = [self.repo.get_market(market_id) for market_id in sorted(market_ids)]
        titles = [market.title for market in markets if market is not None]
        return min(titles, key=lambda title: (len(title), title)) if titles else None


def _mapping_for_assessment(
    mapping: OutcomeEquivalenceMapping,
    assessment_id: str,
) -> OutcomeEquivalenceMapping:
    digest = hash_payload(
        {
            "assessment_id": assessment_id,
            "left_outcome_id": mapping.left_outcome_id,
            "relation": mapping.relation.value,
            "right_outcome_id": mapping.right_outcome_id,
        }
    )
    return mapping.model_copy(
        update={
            "equivalence_assessment_id": assessment_id,
            "outcome_mapping_id": f"outcome_mapping_{digest[:24]}",
        }
    )


def _pair_intersects(
    assessment: MarketEquivalenceAssessment,
    market_ids: list[str],
) -> bool:
    allowed = set(market_ids)
    return assessment.left_market_id in allowed or assessment.right_market_id in allowed


def _connected_components(
    assessments: list[MarketEquivalenceAssessment],
) -> list[tuple[set[str], list[MarketEquivalenceAssessment]]]:
    adjacency: dict[str, set[str]] = {}
    by_edge: dict[frozenset[str], MarketEquivalenceAssessment] = {}
    for assessment in assessments:
        left = assessment.left_market_id
        right = assessment.right_market_id
        adjacency.setdefault(left, set()).add(right)
        adjacency.setdefault(right, set()).add(left)
        by_edge[frozenset({left, right})] = assessment

    components: list[tuple[set[str], list[MarketEquivalenceAssessment]]] = []
    seen: set[str] = set()
    for market_id in sorted(adjacency):
        if market_id in seen:
            continue
        stack = [market_id]
        markets: set[str] = set()
        while stack:
            current = stack.pop()
            if current in markets:
                continue
            markets.add(current)
            stack.extend(sorted(adjacency.get(current, set()) - markets))
        seen |= markets
        component_assessments = [
            assessment
            for edge, assessment in by_edge.items()
            if edge.issubset(markets)
        ]
        components.append((markets, component_assessments))
    return components


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
