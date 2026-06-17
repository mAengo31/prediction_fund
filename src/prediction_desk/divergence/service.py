"""Service layer for replay-safe cross-venue divergence analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from prediction_desk.divergence.aggregation import aggregate_divergence_signals
from prediction_desk.divergence.enums import (
    DivergenceStatus,
)
from prediction_desk.divergence.models import (
    CrossVenueDivergenceAnalysis,
    CrossVenueDivergenceAssessment,
    CrossVenueDivergenceSignal,
    CrossVenueDivergenceSnapshot,
    compute_snapshot_input_hash,
    compute_snapshot_output_hash,
)
from prediction_desk.divergence.pricing import (
    align_right_bid_ask_for_outcome_relation,
    align_right_price_for_outcome_relation,
    compute_gap_bps,
    compute_spread_adjusted_gap,
    determine_stale_side,
    determine_weaker_side,
    integrity_risk_score,
    quality_score,
    total_depth,
)
from prediction_desk.divergence.signals import generate_divergence_signals
from prediction_desk.equivalence.enums import ComparisonPermission, OutcomeRelation
from prediction_desk.equivalence.models import (
    MarketEquivalenceAssessment,
    OutcomeEquivalenceMapping,
)
from prediction_desk.marketdata.models import MarketLiquiditySnapshot, MarketPriceSnapshot
from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository


class DivergenceServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class DivergenceService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def analyze_equivalence_divergence(
        self,
        equivalence_assessment_id: str,
        *,
        asof_timestamp: datetime | None = None,
        outcome_mapping_id: str | None = None,
        force: bool = False,
        config: dict[str, Any] | None = None,
    ) -> CrossVenueDivergenceAnalysis:
        asof = asof_timestamp or datetime.now(tz=UTC)
        snapshot = self.build_divergence_snapshot(
            equivalence_assessment_id=equivalence_assessment_id,
            outcome_mapping_id=outcome_mapping_id,
            asof_timestamp=asof,
            force=force,
            config=config,
        )
        previous = self.repo.list_divergence_assessments(
            market_id=snapshot.left_market_id,
            limit=1000,
        )
        previous = [
            item
            for item in previous
            if {item.left_market_id, item.right_market_id}
            == {snapshot.left_market_id, snapshot.right_market_id}
            and _as_utc(item.available_at) <= _as_utc(asof)
            and item.divergence_snapshot_id != snapshot.divergence_snapshot_id
        ]
        signals = []
        for signal in generate_divergence_signals(
            snapshot,
            previous_assessments=previous,
            config=config,
        ):
            existing_signal = self.repo.find_divergence_signal_by_hash(signal.output_hash)
            signals.append(
                existing_signal
                if existing_signal is not None and not force
                else self.repo.save_divergence_signal(signal)
            )
        assessment = aggregate_divergence_signals(snapshot, signals)
        existing_assessment = self.repo.find_divergence_assessment_by_hash(
            assessment.output_hash
        )
        if existing_assessment is not None and not force:
            return CrossVenueDivergenceAnalysis(
                snapshot=snapshot,
                signals=signals,
                assessment=existing_assessment,
            )
        saved_assessment = self.repo.save_divergence_assessment(assessment)
        return CrossVenueDivergenceAnalysis(
            snapshot=snapshot,
            signals=signals,
            assessment=saved_assessment,
        )

    def build_divergence_snapshot(
        self,
        *,
        equivalence_assessment_id: str,
        outcome_mapping_id: str | None,
        asof_timestamp: datetime,
        force: bool = False,
        config: dict[str, Any] | None = None,
    ) -> CrossVenueDivergenceSnapshot:
        assessment = self.repo.get_market_equivalence_assessment(equivalence_assessment_id)
        if assessment is None:
            raise DivergenceServiceError("equivalence_assessment_not_found")
        if _as_utc(assessment.available_at) > _as_utc(asof_timestamp):
            raise DivergenceServiceError("equivalence_assessment_not_available_asof")
        mapping = self._outcome_mapping(assessment, outcome_mapping_id)

        left_price = self.repo.get_latest_price_snapshot_asof(
            assessment.left_market_id,
            asof_timestamp,
        )
        right_price = self.repo.get_latest_price_snapshot_asof(
            assessment.right_market_id,
            asof_timestamp,
        )
        left_liquidity = self.repo.get_latest_liquidity_snapshot_asof(
            assessment.left_market_id,
            asof_timestamp,
        )
        right_liquidity = self.repo.get_latest_liquidity_snapshot_asof(
            assessment.right_market_id,
            asof_timestamp,
        )
        left_quality = self.repo.get_latest_quality_report_asof(
            assessment.left_market_id,
            asof_timestamp,
        )
        right_quality = self.repo.get_latest_quality_report_asof(
            assessment.right_market_id,
            asof_timestamp,
        )
        left_integrity = self.repo.get_latest_integrity_assessment_asof(
            assessment.left_market_id,
            asof_timestamp,
        )
        right_integrity = self.repo.get_latest_integrity_assessment_asof(
            assessment.right_market_id,
            asof_timestamp,
        )

        relation = mapping.relation.value if mapping is not None else None
        left_price_value = _price_value(left_price)
        right_price_raw = _price_value(right_price)
        right_price_aligned = align_right_price_for_outcome_relation(
            right_price_raw,
            relation,
        )
        left_mid = _mid_value(left_price, left_liquidity)
        right_mid_raw = _mid_value(right_price, right_liquidity)
        right_mid_aligned = align_right_price_for_outcome_relation(
            right_mid_raw,
            relation,
        )
        right_bid_aligned, right_ask_aligned = align_right_bid_ask_for_outcome_relation(
            _bid_value(right_price, right_liquidity),
            _ask_value(right_price, right_liquidity),
            relation,
        )
        signed_mid_gap = (
            left_mid - right_mid_aligned
            if left_mid is not None and right_mid_aligned is not None
            else None
        )
        absolute_mid_gap = abs(signed_mid_gap) if signed_mid_gap is not None else None
        signed_price_gap = (
            left_price_value - right_price_aligned
            if left_price_value is not None and right_price_aligned is not None
            else None
        )
        absolute_price_gap = (
            abs(signed_price_gap) if signed_price_gap is not None else None
        )
        left_spread = _spread_value(left_price, left_liquidity)
        right_spread = _spread_value(right_price, right_liquidity)
        combined_spread = (
            left_spread + right_spread
            if left_spread is not None and right_spread is not None
            else None
        )
        comparable = assessment.comparison_permission == ComparisonPermission.COMPARABLE
        comparable_with_haircut = (
            assessment.comparison_permission
            == ComparisonPermission.COMPARABLE_WITH_HAIRCUT
        )
        manual_review = (
            assessment.comparison_permission == ComparisonPermission.MANUAL_REVIEW
        )
        do_not_compare = (
            assessment.comparison_permission == ComparisonPermission.DO_NOT_COMPARE
        )
        missing_price_data = (
            left_price_value is None
            or right_price_raw is None
            or right_price_aligned is None
            or relation not in {OutcomeRelation.SAME.value, OutcomeRelation.INVERSE.value}
        )
        missing_liquidity_data = left_liquidity is None or right_liquidity is None
        left_quality_score = quality_score(left_quality)
        right_quality_score = quality_score(right_quality)
        left_integrity_risk = integrity_risk_score(left_integrity)
        right_integrity_risk = integrity_risk_score(right_integrity)
        quality_threshold = int((config or {}).get("quality_score_threshold", 70))
        integrity_threshold = int((config or {}).get("integrity_risk_threshold", 70))
        wide_spread_threshold = Decimal(str((config or {}).get("wide_spread_threshold", "0.10")))
        stale_side = determine_stale_side(left_quality, right_quality)
        stale_data = stale_side is not None
        low_quality = (
            (left_quality_score is not None and left_quality_score < quality_threshold)
            or (right_quality_score is not None and right_quality_score < quality_threshold)
        )
        high_integrity = (
            (left_integrity_risk is not None and left_integrity_risk >= integrity_threshold)
            or (
                right_integrity_risk is not None
                and right_integrity_risk >= integrity_threshold
            )
        )
        left_total_depth = total_depth(left_liquidity)
        right_total_depth = total_depth(right_liquidity)
        wide_spread = (
            (left_spread is not None and left_spread >= wide_spread_threshold)
            or (right_spread is not None and right_spread >= wide_spread_threshold)
        )
        one_sided_or_empty = (
            _one_sided_or_empty(left_liquidity)
            or _one_sided_or_empty(right_liquidity)
        )
        snapshot = CrossVenueDivergenceSnapshot(
            divergence_snapshot_id="pending",
            equivalence_assessment_id=assessment.equivalence_assessment_id,
            outcome_mapping_id=mapping.outcome_mapping_id if mapping else None,
            left_market_id=assessment.left_market_id,
            right_market_id=assessment.right_market_id,
            left_venue_id=assessment.left_venue_id,
            right_venue_id=assessment.right_venue_id,
            left_outcome_id=mapping.left_outcome_id if mapping else None,
            right_outcome_id=mapping.right_outcome_id if mapping else None,
            asof_timestamp=asof_timestamp,
            generated_at=datetime.now(tz=UTC),
            available_at=asof_timestamp,
            equivalence_status=assessment.status.value,
            comparison_permission=assessment.comparison_permission.value,
            equivalence_score=assessment.overall_score,
            equivalence_confidence_score=assessment.confidence_score,
            outcome_relation=relation,
            left_price_snapshot_id=left_price.price_snapshot_id if left_price else None,
            right_price_snapshot_id=right_price.price_snapshot_id if right_price else None,
            left_liquidity_snapshot_id=(
                left_liquidity.liquidity_snapshot_id if left_liquidity else None
            ),
            right_liquidity_snapshot_id=(
                right_liquidity.liquidity_snapshot_id if right_liquidity else None
            ),
            left_quality_report_id=left_quality.quality_report_id if left_quality else None,
            right_quality_report_id=right_quality.quality_report_id if right_quality else None,
            left_integrity_assessment_id=(
                left_integrity.integrity_assessment_id if left_integrity else None
            ),
            right_integrity_assessment_id=(
                right_integrity.integrity_assessment_id if right_integrity else None
            ),
            left_price=left_price_value,
            right_price_raw=right_price_raw,
            right_price_aligned=right_price_aligned,
            left_mid=left_mid,
            right_mid_raw=right_mid_raw,
            right_mid_aligned=right_mid_aligned,
            left_bid=_bid_value(left_price, left_liquidity),
            left_ask=_ask_value(left_price, left_liquidity),
            right_bid_raw=_bid_value(right_price, right_liquidity),
            right_ask_raw=_ask_value(right_price, right_liquidity),
            right_bid_aligned=right_bid_aligned,
            right_ask_aligned=right_ask_aligned,
            signed_mid_gap=signed_mid_gap,
            absolute_mid_gap=absolute_mid_gap,
            signed_price_gap=signed_price_gap,
            absolute_price_gap=absolute_price_gap,
            gap_bps=compute_gap_bps(absolute_mid_gap, left_mid),
            combined_spread=combined_spread,
            spread_adjusted_gap=compute_spread_adjusted_gap(
                absolute_mid_gap,
                left_spread,
                right_spread,
            ),
            left_spread=left_spread,
            right_spread=right_spread,
            left_total_depth=left_total_depth,
            right_total_depth=right_total_depth,
            min_total_depth=_min_depth(left_total_depth, right_total_depth),
            left_quality_score=left_quality_score,
            right_quality_score=right_quality_score,
            left_integrity_risk_score=left_integrity_risk,
            right_integrity_risk_score=right_integrity_risk,
            stale_side=stale_side,
            weaker_side=determine_weaker_side(
                left_quality_score=left_quality_score,
                right_quality_score=right_quality_score,
                left_integrity_risk_score=left_integrity_risk,
                right_integrity_risk_score=right_integrity_risk,
                left_liquidity=left_liquidity,
                right_liquidity=right_liquidity,
            ),
            comparable=comparable,
            comparable_with_haircut=comparable_with_haircut,
            manual_review_required=manual_review,
            do_not_compare=do_not_compare,
            missing_price_data=missing_price_data,
            missing_liquidity_data=missing_liquidity_data,
            stale_data=stale_data,
            low_quality_data=low_quality,
            high_integrity_risk=high_integrity,
            wide_spread=wide_spread,
            one_sided_or_empty_book=one_sided_or_empty,
            input_hash="pending",
            output_hash="pending",
            metadata={
                "builder": "divergence_snapshot_v1",
                "quality_score_threshold": quality_threshold,
                "integrity_risk_threshold": integrity_threshold,
                "wide_spread_threshold": str(wide_spread_threshold),
            },
        )
        input_hash = compute_snapshot_input_hash(snapshot)
        output_hash = compute_snapshot_output_hash(
            snapshot.model_copy(update={"input_hash": input_hash})
        )
        snapshot = snapshot.model_copy(
            update={
                "divergence_snapshot_id": f"divergence_snapshot_{output_hash[:24]}",
                "input_hash": input_hash,
                "output_hash": output_hash,
            }
        )
        existing = self.repo.find_divergence_snapshot_by_hash(snapshot.input_hash)
        if existing is not None and not force:
            return existing
        return self.repo.save_divergence_snapshot(snapshot)

    def analyze_market_divergence(
        self,
        market_id: str,
        *,
        asof_timestamp: datetime | None = None,
        force: bool = False,
        config: dict[str, Any] | None = None,
    ) -> list[CrossVenueDivergenceAnalysis]:
        if self.repo.get_market(market_id) is None:
            raise DivergenceServiceError("market_not_found")
        asof = asof_timestamp or datetime.now(tz=UTC)
        assessments = self.repo.list_latest_equivalence_assessments_for_market_asof(
            market_id,
            asof,
        )
        return [
            self.analyze_equivalence_divergence(
                assessment.equivalence_assessment_id,
                asof_timestamp=asof,
                force=force,
                config=config,
            )
            for assessment in assessments
        ]

    def analyze_divergence_for_equivalence_run(
        self,
        equivalence_run_id: str,
        *,
        asof_timestamp: datetime | None = None,
        force: bool = False,
        config: dict[str, Any] | None = None,
    ) -> list[CrossVenueDivergenceAnalysis]:
        run = self.repo.get_equivalence_run(equivalence_run_id)
        if run is None:
            raise DivergenceServiceError("equivalence_run_not_found")
        asof = asof_timestamp or run.asof_timestamp
        assessments = _dedupe_assessments(
            [
                assessment
                for market_id in run.market_ids
                for assessment in self.repo.list_latest_equivalence_assessments_for_market_asof(
                    market_id,
                    asof,
                )
            ]
        )
        if not assessments:
            assessments = [
                assessment
                for assessment in self.repo.list_equivalence_assessments(limit=500)
                if _as_utc(assessment.available_at) <= _as_utc(asof)
            ]
        return [
            self.analyze_equivalence_divergence(
                assessment.equivalence_assessment_id,
                asof_timestamp=asof,
                force=force,
                config=config,
            )
            for assessment in assessments
        ]

    def get_latest_divergence_assessment(
        self,
        left_market_id: str,
        right_market_id: str,
        asof_timestamp: datetime | None = None,
    ) -> CrossVenueDivergenceAssessment:
        assessment = self.repo.get_latest_divergence_assessment_asof(
            left_market_id,
            right_market_id,
            asof_timestamp or datetime.now(tz=UTC),
        )
        if assessment is None:
            raise DivergenceServiceError("divergence_assessment_not_found")
        return assessment

    def get_latest_market_divergence_assessment(
        self,
        market_id: str,
        asof_timestamp: datetime | None = None,
    ) -> CrossVenueDivergenceAssessment:
        assessments = self.repo.list_latest_divergence_assessments_for_market_asof(
            market_id,
            asof_timestamp or datetime.now(tz=UTC),
            limit=1,
        )
        if not assessments:
            raise DivergenceServiceError("divergence_assessment_not_found")
        return assessments[0]

    def list_divergence_snapshots(
        self,
        *,
        market_id: str | None = None,
        equivalence_assessment_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceSnapshot]:
        return self.repo.list_divergence_snapshots(
            market_id=market_id,
            equivalence_assessment_id=equivalence_assessment_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def list_divergence_signals(
        self,
        *,
        market_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceSignal]:
        return self.repo.list_divergence_signals(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def list_divergence_assessments(
        self,
        *,
        market_id: str | None = None,
        status: DivergenceStatus | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[CrossVenueDivergenceAssessment]:
        return self.repo.list_divergence_assessments(
            market_id=market_id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def _outcome_mapping(
        self,
        assessment: MarketEquivalenceAssessment,
        outcome_mapping_id: str | None,
    ) -> OutcomeEquivalenceMapping | None:
        mappings = self.repo.list_outcome_equivalence_mappings(
            assessment.equivalence_assessment_id
        )
        if outcome_mapping_id is not None:
            for mapping in mappings:
                if mapping.outcome_mapping_id == outcome_mapping_id:
                    return mapping
            raise DivergenceServiceError("outcome_mapping_not_found")
        eligible = [
            mapping
            for mapping in mappings
            if mapping.relation in {OutcomeRelation.SAME, OutcomeRelation.INVERSE}
        ]
        if not eligible:
            return None
        return sorted(
            eligible,
            key=lambda item: (
                -item.score,
                item.relation.value,
                item.left_outcome_id or "",
                item.right_outcome_id or "",
            ),
        )[0]


def analyze_equivalence_divergence(
    equivalence_assessment_id: str,
    *,
    asof_timestamp: datetime | None = None,
    outcome_mapping_id: str | None = None,
    force: bool = False,
    config: dict[str, Any] | None = None,
    repo: PredictionMarketRepository | None = None,
    database_url: str | None = None,
) -> CrossVenueDivergenceAnalysis:
    if repo is not None:
        return DivergenceService(repo).analyze_equivalence_divergence(
            equivalence_assessment_id,
            asof_timestamp=asof_timestamp,
            outcome_mapping_id=outcome_mapping_id,
            force=force,
            config=config,
        )
    with session_scope(database_url) as session:
        service = DivergenceService(PredictionMarketRepository(session))
        return service.analyze_equivalence_divergence(
            equivalence_assessment_id,
            asof_timestamp=asof_timestamp,
            outcome_mapping_id=outcome_mapping_id,
            force=force,
            config=config,
        )


def _price_value(snapshot: MarketPriceSnapshot | None) -> Decimal | None:
    if snapshot is None:
        return None
    return getattr(snapshot, "price", None) or getattr(snapshot, "mid", None)


def _mid_value(
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
) -> Decimal | None:
    if price_snapshot is not None and price_snapshot.mid is not None:
        return price_snapshot.mid
    if liquidity_snapshot is not None and liquidity_snapshot.mid_price is not None:
        return liquidity_snapshot.mid_price
    return _price_value(price_snapshot)


def _bid_value(
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
) -> Decimal | None:
    if price_snapshot is not None and price_snapshot.bid is not None:
        return price_snapshot.bid
    if liquidity_snapshot is not None:
        return liquidity_snapshot.best_bid
    return None


def _ask_value(
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
) -> Decimal | None:
    if price_snapshot is not None and price_snapshot.ask is not None:
        return price_snapshot.ask
    if liquidity_snapshot is not None:
        return liquidity_snapshot.best_ask
    return None


def _spread_value(
    price_snapshot: MarketPriceSnapshot | None,
    liquidity_snapshot: MarketLiquiditySnapshot | None,
) -> Decimal | None:
    if price_snapshot is not None and price_snapshot.spread is not None:
        return price_snapshot.spread
    if liquidity_snapshot is not None:
        return liquidity_snapshot.spread
    return None


def _min_depth(left_depth: Decimal | None, right_depth: Decimal | None) -> Decimal | None:
    if left_depth is None or right_depth is None:
        return None
    return min(left_depth, right_depth)


def _one_sided_or_empty(liquidity: MarketLiquiditySnapshot | None) -> bool:
    if liquidity is None:
        return False
    return bool(
        liquidity.is_empty_book
        or liquidity.best_bid is None
        or liquidity.best_ask is None
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _dedupe_assessments(
    assessments: list[MarketEquivalenceAssessment],
) -> list[MarketEquivalenceAssessment]:
    by_id = {assessment.equivalence_assessment_id: assessment for assessment in assessments}
    return [by_id[key] for key in sorted(by_id)]
