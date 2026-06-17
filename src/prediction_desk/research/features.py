"""As-of-safe research feature construction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.research.enums import ResearchFeatureFamily, ResearchFeatureSource
from prediction_desk.research.models import (
    ResearchFeatureSnapshot,
    compute_feature_input_hash,
    compute_feature_output_hash,
    research_object_id,
)


def build_research_features(
    market_id: str,
    asof_timestamp: datetime,
    include_sources: list[str] | None = None,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> list[ResearchFeatureSnapshot]:
    if repo is not None:
        return _build_research_features(
            market_id,
            asof_timestamp,
            include_sources=include_sources,
            force=force,
            repo=repo,
        )
    with session_scope() as session:
        return _build_research_features(
            market_id,
            asof_timestamp,
            include_sources=include_sources,
            force=force,
            repo=PredictionMarketRepository(session),
        )


def _build_research_features(
    market_id: str,
    asof_timestamp: datetime,
    *,
    include_sources: list[str] | None,
    force: bool,
    repo: PredictionMarketRepository,
) -> list[ResearchFeatureSnapshot]:
    selected = _selected_sources(include_sources)
    builders = {
        ResearchFeatureSource.MARKET_DATA: _market_data_feature,
        ResearchFeatureSource.RESOLUTION: _resolution_feature,
        ResearchFeatureSource.INTEGRITY: _integrity_feature,
        ResearchFeatureSource.EQUIVALENCE: _equivalence_feature,
        ResearchFeatureSource.DIVERGENCE: _divergence_feature,
        ResearchFeatureSource.PRETRADE: _pretrade_feature,
        ResearchFeatureSource.PAPER: _paper_feature,
    }
    features: list[ResearchFeatureSnapshot] = []
    for source in selected:
        builder = builders.get(source)
        if builder is None:
            continue
        feature = builder(repo, market_id, asof_timestamp)
        existing = repo.find_research_feature_snapshot_by_hash(feature.input_hash)
        if existing is not None and not force:
            features.append(existing)
        else:
            features.append(repo.save_research_feature_snapshot(feature))
    return features


def _selected_sources(
    include_sources: list[str] | None,
) -> list[ResearchFeatureSource]:
    if include_sources is None:
        return [
            ResearchFeatureSource.MARKET_DATA,
            ResearchFeatureSource.RESOLUTION,
            ResearchFeatureSource.INTEGRITY,
            ResearchFeatureSource.EQUIVALENCE,
            ResearchFeatureSource.DIVERGENCE,
            ResearchFeatureSource.PRETRADE,
            ResearchFeatureSource.PAPER,
        ]
    return [ResearchFeatureSource(str(source)) for source in include_sources]


def _market_data_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    quality = repo.get_latest_quality_report_asof(market_id, asof_timestamp)
    price = repo.get_latest_price_snapshot_asof(market_id, asof_timestamp)
    liquidity = repo.get_latest_liquidity_snapshot_asof(market_id, asof_timestamp)
    refs = [
        value
        for value in [
            quality.quality_report_id if quality else None,
            price.price_snapshot_id if price else None,
            liquidity.liquidity_snapshot_id if liquidity else None,
        ]
        if value
    ]
    values: dict[str, Any] = {
        "quality_report_id": quality.quality_report_id if quality else None,
        "quality_score": quality.quality_score if quality else None,
        "quality_reason_codes": list(quality.reason_codes) if quality else [],
        "price_snapshot_id": price.price_snapshot_id if price else None,
        "price": price.price if price else None,
        "mid": price.mid if price else None,
        "bid": price.bid if price else None,
        "ask": price.ask if price else None,
        "liquidity_snapshot_id": (
            liquidity.liquidity_snapshot_id if liquidity else None
        ),
        "spread": liquidity.spread if liquidity else None,
        "spread_bps": liquidity.spread_bps if liquidity else None,
        "total_depth": (
            liquidity.total_bid_depth + liquidity.total_ask_depth if liquidity else None
        ),
        "is_empty_book": liquidity.is_empty_book if liquidity else None,
        "is_crossed_book": liquidity.is_crossed_book if liquidity else None,
    }
    reason_codes = []
    if quality is None:
        reason_codes.append("NO_MARKET_DATA_QUALITY_REPORT")
    if price is None:
        reason_codes.append("NO_PRICE_SNAPSHOT")
    if liquidity is None:
        reason_codes.append("NO_LIQUIDITY_SNAPSHOT")
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.MARKET_DATA,
        family=ResearchFeatureFamily.DATA_QUALITY,
        source_ref_ids=refs,
        values=values,
        reason_codes=reason_codes,
    )


def _resolution_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    verdict = repo.get_latest_trust_verdict_asof(market_id, asof_timestamp)
    rule = repo.get_latest_rule_snapshot_asof(market_id, asof_timestamp)
    refs = [
        value
        for value in [
            verdict.verdict_id if verdict else None,
            rule.rule_snapshot_id if rule else None,
        ]
        if value
    ]
    values = {
        "trust_verdict_id": verdict.verdict_id if verdict else None,
        "trust_action": verdict.action.value if verdict else None,
        "resolution_risk_score": verdict.resolution_risk_score if verdict else None,
        "trust_reason_codes": list(verdict.reason_codes) if verdict else [],
        "rule_snapshot_id": rule.rule_snapshot_id if rule else None,
        "rule_snapshot_hash": rule.rule_hash if rule else None,
    }
    reason_codes = []
    if verdict is None:
        reason_codes.append("NO_TRUST_VERDICT")
    if rule is None:
        reason_codes.append("NO_RULE_SNAPSHOT")
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.RESOLUTION,
        family=ResearchFeatureFamily.CONTRACT_RULES,
        source_ref_ids=refs,
        values=values,
        reason_codes=reason_codes,
    )


def _integrity_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    assessment = repo.get_latest_integrity_assessment_asof(market_id, asof_timestamp)
    values = {
        "integrity_assessment_id": (
            assessment.integrity_assessment_id if assessment else None
        ),
        "overall_risk_score": assessment.overall_risk_score if assessment else None,
        "action_hint": assessment.action_hint.value if assessment else None,
        "severity": assessment.severity.value if assessment else None,
        "reason_codes": list(assessment.reason_codes) if assessment else [],
    }
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.INTEGRITY,
        family=ResearchFeatureFamily.RISK,
        source_ref_ids=[assessment.integrity_assessment_id] if assessment else [],
        values=values,
        reason_codes=[] if assessment else ["NO_INTEGRITY_ASSESSMENT"],
    )


def _equivalence_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    assessments = repo.list_latest_equivalence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
    )
    values = {
        "assessment_ids": [
            assessment.equivalence_assessment_id for assessment in assessments
        ],
        "permissions": [assessment.comparison_permission.value for assessment in assessments],
        "statuses": [assessment.status.value for assessment in assessments],
        "comparable_count": sum(
            1
            for assessment in assessments
            if assessment.comparison_permission.value
            in {"COMPARABLE", "COMPARABLE_WITH_HAIRCUT"}
        ),
        "manual_review_count": sum(
            1
            for assessment in assessments
            if assessment.comparison_permission.value == "MANUAL_REVIEW"
        ),
        "do_not_compare_count": sum(
            1
            for assessment in assessments
            if assessment.comparison_permission.value == "DO_NOT_COMPARE"
        ),
    }
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.EQUIVALENCE,
        family=ResearchFeatureFamily.CROSS_VENUE,
        source_ref_ids=[assessment.equivalence_assessment_id for assessment in assessments],
        values=values,
        reason_codes=[] if assessments else ["NO_EQUIVALENCE_ASSESSMENTS"],
    )


def _divergence_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    assessments = repo.list_latest_divergence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
    )
    max_score = max(
        (assessment.overall_divergence_score for assessment in assessments),
        default=None,
    )
    snapshots = repo.list_divergence_snapshots(
        market_id=market_id,
        end_time=asof_timestamp,
        limit=100,
    )
    snapshots_by_id = {
        snapshot.divergence_snapshot_id: snapshot
        for snapshot in snapshots
        if snapshot.available_at <= asof_timestamp
    }
    lower_side_payloads: list[dict[str, Any]] = []
    for assessment in assessments:
        snapshot = snapshots_by_id.get(assessment.divergence_snapshot_id)
        if snapshot is None:
            continue
        lower_side_payloads.append(
            {
                "divergence_snapshot_id": snapshot.divergence_snapshot_id,
                "divergence_assessment_id": assessment.divergence_assessment_id,
                "left_market_id": snapshot.left_market_id,
                "right_market_id": snapshot.right_market_id,
                "left_venue_id": snapshot.left_venue_id,
                "right_venue_id": snapshot.right_venue_id,
                "left_outcome_id": snapshot.left_outcome_id,
                "right_outcome_id": snapshot.right_outcome_id,
                "left_price": snapshot.left_mid or snapshot.left_price,
                "right_price_aligned": (
                    snapshot.right_mid_aligned or snapshot.right_price_aligned
                ),
                "status": assessment.status.value,
                "comparison_permission": assessment.comparison_permission,
            }
        )
    values = {
        "assessment_ids": [
            assessment.divergence_assessment_id for assessment in assessments
        ],
        "statuses": [assessment.status.value for assessment in assessments],
        "max_divergence_score": max_score,
        "watch_count": sum(
            1 for assessment in assessments if assessment.status.value == "WATCH"
        ),
        "material_count": sum(
            1
            for assessment in assessments
            if assessment.status.value == "MATERIAL_DIVERGENCE"
        ),
        "needs_review_count": sum(
            1
            for assessment in assessments
            if assessment.status.value == "NEEDS_REVIEW"
        ),
        "do_not_compare_count": sum(
            1
            for assessment in assessments
            if assessment.status.value == "DO_NOT_COMPARE"
        ),
        "lower_side_inputs": lower_side_payloads,
    }
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.DIVERGENCE,
        family=ResearchFeatureFamily.CROSS_VENUE,
        source_ref_ids=[assessment.divergence_assessment_id for assessment in assessments],
        values=values,
        reason_codes=[] if assessments else ["NO_DIVERGENCE_ASSESSMENTS"],
    )


def _pretrade_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    decision = repo.get_latest_pretrade_decision_asof(market_id, asof_timestamp)
    values = {
        "pretrade_decision_id": decision.pretrade_decision_id if decision else None,
        "action": decision.action.value if decision else None,
        "final_allowed_size_units": (
            decision.final_allowed_size_units if decision else None
        ),
        "hard_blockers": list(decision.hard_blockers) if decision else [],
        "warnings": list(decision.warnings) if decision else [],
        "reason_codes": list(decision.reason_codes) if decision else [],
    }
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.PRETRADE,
        family=ResearchFeatureFamily.RISK,
        source_ref_ids=[decision.pretrade_decision_id] if decision else [],
        values=values,
        reason_codes=[] if decision else ["NO_PRETRADE_DECISION"],
    )


def _paper_feature(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
) -> ResearchFeatureSnapshot:
    position = repo.get_latest_paper_position_asof(market_id, asof_timestamp=asof_timestamp)
    portfolio = repo.get_latest_paper_portfolio_asof(asof_timestamp=asof_timestamp)
    refs = [
        value
        for value in [
            position.position_snapshot_id if position else None,
            portfolio.portfolio_snapshot_id if portfolio else None,
        ]
        if value
    ]
    values = {
        "position_snapshot_id": position.position_snapshot_id if position else None,
        "position_units": position.position_units if position else None,
        "unrealized_pnl_simulated": (
            position.unrealized_pnl_simulated if position else None
        ),
        "portfolio_snapshot_id": portfolio.portfolio_snapshot_id if portfolio else None,
        "total_equity_simulated": portfolio.total_equity_simulated if portfolio else None,
        "total_fees_simulated": portfolio.total_fees_simulated if portfolio else None,
    }
    reason_codes = []
    if position is None:
        reason_codes.append("NO_PAPER_POSITION")
    if portfolio is None:
        reason_codes.append("NO_PAPER_PORTFOLIO")
    return _feature(
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        source=ResearchFeatureSource.PAPER,
        family=ResearchFeatureFamily.SIMULATED_EXECUTION,
        source_ref_ids=refs,
        values=values,
        reason_codes=reason_codes,
    )


def _feature(
    *,
    market_id: str,
    asof_timestamp: datetime,
    source: ResearchFeatureSource,
    family: ResearchFeatureFamily,
    source_ref_ids: list[str],
    values: dict[str, Any],
    reason_codes: list[str],
) -> ResearchFeatureSnapshot:
    generated_at = datetime.now(tz=UTC)
    provisional = ResearchFeatureSnapshot(
        research_feature_snapshot_id="pending",
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=generated_at,
        available_at=asof_timestamp,
        feature_source=source,
        feature_family=family,
        source_ref_ids=sorted(source_ref_ids),
        values=values,
        reason_codes=sorted(set(reason_codes)),
        input_hash="pending",
        output_hash="pending",
    )
    input_hash = compute_feature_input_hash(provisional)
    feature = provisional.model_copy(
        update={
            "research_feature_snapshot_id": research_object_id(
                "research_feature", {"input_hash": input_hash}
            ),
            "input_hash": input_hash,
        }
    )
    return feature.model_copy(update={"output_hash": compute_feature_output_hash(feature)})
