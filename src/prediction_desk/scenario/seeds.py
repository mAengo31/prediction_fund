"""Deterministic scenario seed-bundle construction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scenario.enums import ScenarioSeedSource
from prediction_desk.scenario.models import (
    ScenarioSeedBundle,
    compute_seed_input_hash,
    compute_seed_output_hash,
    scenario_object_id,
)


def build_scenario_seed_bundle(
    market_id: str,
    asof_timestamp: datetime,
    seed_source: str = ScenarioSeedSource.MARKET_CONTEXT.value,
    force: bool = False,
    repo: PredictionMarketRepository | None = None,
) -> ScenarioSeedBundle:
    if repo is not None:
        return _build_scenario_seed_bundle(
            repo,
            market_id,
            asof_timestamp,
            ScenarioSeedSource(seed_source),
            force=force,
        )
    with session_scope() as session:
        return _build_scenario_seed_bundle(
            PredictionMarketRepository(session),
            market_id,
            asof_timestamp,
            ScenarioSeedSource(seed_source),
            force=force,
        )


def _build_scenario_seed_bundle(
    repo: PredictionMarketRepository,
    market_id: str,
    asof_timestamp: datetime,
    seed_source: ScenarioSeedSource,
    *,
    force: bool,
) -> ScenarioSeedBundle:
    market = repo.get_market(market_id)
    if market is None:
        raise ValueError("scenario_seed_market_not_found")
    rule = repo.get_latest_rule_snapshot_asof(market_id, asof_timestamp)
    analysis = repo.get_latest_resolution_analysis_asof(market_id, asof_timestamp)
    quality = repo.get_latest_quality_report_asof(market_id, asof_timestamp)
    integrity = repo.get_latest_integrity_assessment_asof(market_id, asof_timestamp)
    equivalence = repo.list_latest_equivalence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
    )
    divergence = repo.list_latest_divergence_assessments_for_market_asof(
        market_id,
        asof_timestamp,
    )
    trust = repo.get_latest_trust_verdict_asof(market_id, asof_timestamp)
    source_ref_ids = [
        value
        for value in [
            rule.rule_snapshot_id if rule else None,
            analysis.predicate.predicate_id if analysis else None,
            analysis.ambiguity_assessment.assessment_id if analysis else None,
            quality.quality_report_id if quality else None,
            integrity.integrity_assessment_id if integrity else None,
            trust.verdict_id if trust else None,
            *[item.equivalence_assessment_id for item in equivalence],
            *[item.divergence_assessment_id for item in divergence],
        ]
        if value
    ]
    structured_context = _structured_context(
        market=market.model_dump(mode="json"),
        rule=rule.model_dump(mode="json") if rule else None,
        predicate=analysis.predicate.model_dump(mode="json") if analysis else None,
        ambiguity=(
            analysis.ambiguity_assessment.model_dump(mode="json") if analysis else None
        ),
        quality=quality.model_dump(mode="json") if quality else None,
        integrity=integrity.model_dump(mode="json") if integrity else None,
        equivalence=[item.model_dump(mode="json") for item in equivalence],
        divergence=[item.model_dump(mode="json") for item in divergence],
        trust=trust.model_dump(mode="json") if trust else None,
    )
    seed_text = _seed_text(structured_context)
    provisional = ScenarioSeedBundle(
        seed_bundle_id="pending",
        market_id=market_id,
        asof_timestamp=asof_timestamp,
        generated_at=datetime.now(tz=UTC),
        available_at=asof_timestamp,
        seed_source=seed_source,
        market_title=market.title,
        market_description=market.description,
        rule_snapshot_id=rule.rule_snapshot_id if rule else None,
        rule_snapshot_hash=rule.rule_hash if rule else None,
        resolution_predicate_id=analysis.predicate.predicate_id if analysis else None,
        ambiguity_assessment_id=(
            analysis.ambiguity_assessment.assessment_id if analysis else None
        ),
        market_data_quality_report_id=quality.quality_report_id if quality else None,
        integrity_assessment_id=(
            integrity.integrity_assessment_id if integrity else None
        ),
        equivalence_assessment_ids=sorted(
            item.equivalence_assessment_id for item in equivalence
        ),
        divergence_assessment_ids=sorted(
            item.divergence_assessment_id for item in divergence
        ),
        trust_verdict_id=trust.verdict_id if trust else None,
        source_ref_ids=sorted(source_ref_ids),
        seed_text=seed_text,
        structured_context=structured_context,
        input_hash="pending",
        output_hash="pending",
        metadata={"seed_version": "scenario_seed_builder_v1"},
    )
    input_hash = compute_seed_input_hash(provisional)
    existing = repo.find_scenario_seed_bundle_by_hash(input_hash)
    if existing is not None and not force:
        return existing
    bundle = provisional.model_copy(
        update={
            "seed_bundle_id": scenario_object_id(
                "scenario_seed",
                {"input_hash": input_hash},
            ),
            "input_hash": input_hash,
        }
    )
    bundle = bundle.model_copy(update={"output_hash": compute_seed_output_hash(bundle)})
    return repo.save_scenario_seed_bundle(bundle)


def _structured_context(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def _seed_text(context: dict[str, Any]) -> str:
    market = context["market"]
    lines = [
        f"Market: {market.get('title')}",
        f"Market ID: {market.get('market_id')}",
        f"Status: {market.get('status')}",
    ]
    if market.get("description"):
        lines.append(f"Description: {market.get('description')}")
    rule = context.get("rule")
    if rule:
        lines.append(f"Rule snapshot: {rule.get('rule_snapshot_id')}")
        lines.append(f"Rule text: {rule.get('normalized_rule_text') or rule.get('raw_rule_text')}")
        if rule.get("resolution_source"):
            lines.append(f"Resolution source: {rule.get('resolution_source')}")
        if rule.get("time_zone"):
            lines.append(f"Time zone: {rule.get('time_zone')}")
    predicate = context.get("predicate")
    if predicate:
        lines.append(f"Predicate: {predicate.get('normalized_predicate_text')}")
        lines.append(f"Predicate status: {predicate.get('parse_status')}")
    ambiguity = context.get("ambiguity")
    if ambiguity:
        lines.append(f"Ambiguity score: {ambiguity.get('overall_score')}")
    quality = context.get("quality")
    if quality:
        lines.append(f"Market-data quality score: {quality.get('quality_score')}")
    integrity = context.get("integrity")
    if integrity:
        lines.append(f"Integrity risk score: {integrity.get('overall_risk_score')}")
    trust = context.get("trust")
    if trust:
        lines.append(f"Trust action: {trust.get('action')}")
    return "\n".join(lines)
