"""Dimension-level deterministic equivalence scoring."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from prediction_desk.domain.models import Event, Market, MarketRuleSnapshot, Outcome
from prediction_desk.equivalence.enums import OutcomeRelation
from prediction_desk.equivalence.models import (
    DimensionScore,
    OutcomeEquivalenceMapping,
    hash_payload,
)
from prediction_desk.equivalence.text import (
    contains_negation_or_inverse,
    extract_key_terms,
    normalize_outcome_label,
    normalize_text,
    token_jaccard_score,
    tokenize,
)
from prediction_desk.resolution.models import AmbiguityAssessment, ResolutionPredicate


def score_title_similarity(left_market: Market, right_market: Market) -> DimensionScore:
    left_terms = set(extract_key_terms(left_market.title))
    right_terms = set(extract_key_terms(right_market.title))
    shared = sorted(left_terms & right_terms)
    score = token_jaccard_score(left_market.title, right_market.title)
    if score >= 80:
        reasons = ["TITLE_HIGH_SIMILARITY"]
    elif score >= 50:
        reasons = ["TITLE_PARTIAL_SIMILARITY"]
    else:
        reasons = ["TITLE_LOW_SIMILARITY"]
    return DimensionScore(
        score=score,
        reason_codes=reasons,
        evidence={
            "left_title": left_market.title,
            "right_title": right_market.title,
            "shared_terms": shared,
        },
    )


def score_event_identity(
    left_event: Event | None,
    right_event: Event | None,
    left_market: Market,
    right_market: Market,
) -> DimensionScore:
    if left_event is None or right_event is None:
        return DimensionScore(
            score=30,
            reason_codes=["EVENT_DATA_MISSING"],
            evidence={
                "left_event_missing": left_event is None,
                "right_event_missing": right_event is None,
            },
        )
    title_score = token_jaccard_score(left_event.title, right_event.title)
    market_title_score = token_jaccard_score(left_market.title, right_market.title)
    category_match = (
        left_event.category is not None
        and right_event.category is not None
        and normalize_text(left_event.category) == normalize_text(right_event.category)
    )
    score = round((title_score * 0.7) + (market_title_score * 0.2) + (10 if category_match else 0))
    score = _clamp(score)
    reasons = ["EVENT_TITLE_ALIGNED"] if score >= 70 else ["EVENT_IDENTITY_WEAK"]
    if category_match:
        reasons.append("EVENT_CATEGORY_MATCH")
    return DimensionScore(
        score=score,
        reason_codes=sorted(set(reasons)),
        evidence={
            "category_match": category_match,
            "left_event_title": left_event.title,
            "right_event_title": right_event.title,
            "market_title_score": market_title_score,
            "title_score": title_score,
        },
    )


def score_outcome_structure(
    left_market: Market,
    right_market: Market,
    left_outcomes: list[Outcome],
    right_outcomes: list[Outcome],
) -> DimensionScore:
    left_labels = _normalized_labels(left_outcomes)
    right_labels = _normalized_labels(right_outcomes)
    left_binary = _is_binary_yes_no(left_labels)
    right_binary = _is_binary_yes_no(right_labels)
    if left_market.market_type != right_market.market_type:
        score = 45 if left_binary and right_binary else 20
        reasons = ["MARKET_TYPE_MISMATCH"]
    elif left_binary and right_binary:
        score = 95
        reasons = ["BINARY_YES_NO_OUTCOMES_ALIGNED"]
    else:
        overlap = _label_overlap_score(left_labels, right_labels)
        score = overlap
        reasons = ["OUTCOME_LABEL_OVERLAP"] if overlap >= 60 else ["OUTCOME_STRUCTURE_WEAK"]
    return DimensionScore(
        score=score,
        reason_codes=reasons,
        evidence={
            "left_labels": left_labels,
            "right_labels": right_labels,
            "left_market_type": left_market.market_type.value,
            "right_market_type": right_market.market_type.value,
        },
        hard_flags={"same_outcome_universe_likely": score >= 70},
    )


def map_outcomes(
    left_outcomes: list[Outcome],
    right_outcomes: list[Outcome],
    left_market: Market,
    right_market: Market,
) -> list[OutcomeEquivalenceMapping]:
    left_by_label = {normalize_outcome_label(outcome.label): outcome for outcome in left_outcomes}
    right_by_label = {normalize_outcome_label(outcome.label): outcome for outcome in right_outcomes}
    mappings: list[OutcomeEquivalenceMapping] = []
    inverse_titles = contains_negation_or_inverse(
        left_market.title
    ) != contains_negation_or_inverse(right_market.title)

    if _is_binary_yes_no(list(left_by_label)) and _is_binary_yes_no(list(right_by_label)):
        pairs = [("yes", "no"), ("no", "yes")] if inverse_titles else [("yes", "yes"), ("no", "no")]
        relation = OutcomeRelation.INVERSE if inverse_titles else OutcomeRelation.SAME
        score = 90 if inverse_titles else 100
        for left_label, right_label in pairs:
            mappings.append(
                _mapping(
                    left_by_label[left_label],
                    right_by_label[right_label],
                    left_market.market_id,
                    right_market.market_id,
                    relation,
                    score,
                    {"binary_yes_no": True, "inverse_titles": inverse_titles},
                )
            )
        return mappings

    for left_outcome in left_outcomes:
        left_label = normalize_outcome_label(left_outcome.label)
        best: tuple[Outcome | None, int] = (None, 0)
        for candidate_right_outcome in right_outcomes:
            score = token_jaccard_score(
                left_label,
                normalize_outcome_label(candidate_right_outcome.label),
            )
            if score > best[1]:
                best = (candidate_right_outcome, score)
        selected_right_outcome = best[0]
        score = best[1]
        relation = OutcomeRelation.PARTIAL if score >= 50 else OutcomeRelation.UNKNOWN
        mappings.append(
            _mapping(
                left_outcome,
                selected_right_outcome,
                left_market.market_id,
                right_market.market_id,
                relation,
                score,
                {"label_similarity": score},
            )
        )
    return mappings


def score_predicate_similarity(
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
) -> DimensionScore:
    if left_predicate is None or right_predicate is None:
        return DimensionScore(
            score=25,
            reason_codes=["PREDICATE_MISSING"],
            evidence={
                "left_predicate_missing": left_predicate is None,
                "right_predicate_missing": right_predicate is None,
            },
        )
    type_score = 35 if left_predicate.predicate_type == right_predicate.predicate_type else 0
    comparator_score = 20 if left_predicate.comparator == right_predicate.comparator else 0
    subject_score = round(
        token_jaccard_score(left_predicate.subject, right_predicate.subject) * 0.2
    )
    condition_score = round(
        token_jaccard_score(left_predicate.condition, right_predicate.condition) * 0.25
    )
    score = _clamp(type_score + comparator_score + subject_score + condition_score)
    return DimensionScore(
        score=score,
        reason_codes=["PREDICATE_ALIGNED"] if score >= 70 else ["PREDICATE_WEAK_ALIGNMENT"],
        evidence={
            "left_predicate_type": left_predicate.predicate_type.value,
            "right_predicate_type": right_predicate.predicate_type.value,
            "left_comparator": (
                left_predicate.comparator.value if left_predicate.comparator else None
            ),
            "right_comparator": (
                right_predicate.comparator.value if right_predicate.comparator else None
            ),
            "subject_score": subject_score,
            "condition_score": condition_score,
        },
    )


def score_resolution_source_alignment(
    left_rule_snapshot: MarketRuleSnapshot | None,
    right_rule_snapshot: MarketRuleSnapshot | None,
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
) -> DimensionScore:
    left_source = _source_text(left_rule_snapshot, left_predicate)
    right_source = _source_text(right_rule_snapshot, right_predicate)
    return _score_text_alignment(
        left_source,
        right_source,
        exact_reason="RESOLUTION_SOURCE_ALIGNED",
        weak_reason="RESOLUTION_SOURCE_MISSING_OR_WEAK",
        mismatch_reason="RESOLUTION_SOURCE_MISMATCH",
        mismatch_flag="resolution_source_mismatch",
    )


def score_settlement_authority_alignment(
    left_rule_snapshot: MarketRuleSnapshot | None,
    right_rule_snapshot: MarketRuleSnapshot | None,
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
) -> DimensionScore:
    left_authority = _authority_text(left_rule_snapshot, left_predicate)
    right_authority = _authority_text(right_rule_snapshot, right_predicate)
    if _venue_specific_authority_pair(left_authority, right_authority):
        return DimensionScore(
            score=65,
            reason_codes=["VENUE_SPECIFIC_SETTLEMENT_AUTHORITY"],
            evidence={"left_text": left_authority, "right_text": right_authority},
        )
    return _score_text_alignment(
        left_authority,
        right_authority,
        exact_reason="SETTLEMENT_AUTHORITY_ALIGNED",
        weak_reason="SETTLEMENT_AUTHORITY_MISSING_OR_WEAK",
        mismatch_reason="SETTLEMENT_AUTHORITY_MISMATCH",
        mismatch_flag="settlement_authority_mismatch",
    )


def score_temporal_alignment(
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
    left_rule_snapshot: MarketRuleSnapshot | None,
    right_rule_snapshot: MarketRuleSnapshot | None,
) -> DimensionScore:
    left_end = _deadline(left_predicate)
    right_end = _deadline(right_predicate)
    if left_end is None or right_end is None:
        return DimensionScore(
            score=35,
            reason_codes=["TEMPORAL_DATA_MISSING"],
            evidence={"left_deadline": _iso(left_end), "right_deadline": _iso(right_end)},
            hard_flags={"insufficient_rule_data": True},
        )
    left_date = left_end.date()
    right_date = right_end.date()
    left_tz = _timezone(left_predicate, left_rule_snapshot)
    right_tz = _timezone(right_predicate, right_rule_snapshot)
    if left_end == right_end:
        score = 100
        reasons = ["DEADLINE_EXACT_MATCH"]
        mismatch = False
    elif left_date == right_date:
        score = 75 if left_tz and right_tz else 60
        reasons = ["DEADLINE_DATE_MATCH"]
        mismatch = False
    else:
        score = 15
        reasons = ["DEADLINE_MISMATCH"]
        mismatch = True
    return DimensionScore(
        score=score,
        reason_codes=reasons,
        evidence={
            "left_deadline": left_end.isoformat(),
            "right_deadline": right_end.isoformat(),
            "left_timezone": left_tz,
            "right_timezone": right_tz,
        },
        hard_flags={"deadline_mismatch": mismatch},
    )


def score_threshold_alignment(
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
) -> DimensionScore:
    if left_predicate is None or right_predicate is None:
        return DimensionScore(score=35, reason_codes=["THRESHOLD_DATA_MISSING"])
    left_value = left_predicate.threshold_value
    right_value = right_predicate.threshold_value
    left_unit = _unit(left_predicate.threshold_unit)
    right_unit = _unit(right_predicate.threshold_unit)
    if left_value is None and right_value is None:
        return DimensionScore(score=80, reason_codes=["NO_EXPLICIT_THRESHOLD_ON_EITHER_SIDE"])
    if left_value is None or right_value is None:
        return DimensionScore(
            score=30,
            reason_codes=["THRESHOLD_MISSING_ON_ONE_SIDE"],
            hard_flags={"threshold_mismatch": True},
        )
    comparator_match = left_predicate.comparator == right_predicate.comparator
    value_match = left_value == right_value
    unit_match = left_unit == right_unit
    if value_match and unit_match and comparator_match:
        score = 100
        reasons = ["THRESHOLD_ALIGNED"]
        mismatch = False
    elif value_match and unit_match:
        score = 70
        reasons = ["THRESHOLD_VALUE_UNIT_MATCH_COMPARATOR_DIFFERS"]
        mismatch = False
    else:
        score = 20
        reasons = ["THRESHOLD_MISMATCH"]
        mismatch = True
    return DimensionScore(
        score=score,
        reason_codes=reasons,
        evidence={
            "left_comparator": (
                left_predicate.comparator.value if left_predicate.comparator else None
            ),
            "left_threshold_unit": left_unit,
            "left_threshold_value": str(left_value),
            "right_comparator": (
                right_predicate.comparator.value if right_predicate.comparator else None
            ),
            "right_threshold_unit": right_unit,
            "right_threshold_value": str(right_value),
        },
        hard_flags={"threshold_mismatch": mismatch},
    )


def score_timezone_alignment(
    left_predicate: ResolutionPredicate | None,
    right_predicate: ResolutionPredicate | None,
    left_rule_snapshot: MarketRuleSnapshot | None,
    right_rule_snapshot: MarketRuleSnapshot | None,
) -> DimensionScore:
    left_tz = _normalize_tz(_timezone(left_predicate, left_rule_snapshot))
    right_tz = _normalize_tz(_timezone(right_predicate, right_rule_snapshot))
    if left_tz and right_tz and left_tz == right_tz:
        return DimensionScore(
            score=100,
            reason_codes=["TIMEZONE_ALIGNED"],
            evidence={"left_timezone": left_tz, "right_timezone": right_tz},
        )
    if not left_tz and not right_tz:
        return DimensionScore(
            score=45,
            reason_codes=["TIMEZONE_MISSING_BOTH"],
            evidence={"left_timezone": left_tz, "right_timezone": right_tz},
            hard_flags={"insufficient_rule_data": True},
        )
    if not left_tz or not right_tz:
        return DimensionScore(
            score=30,
            reason_codes=["TIMEZONE_MISSING_ONE_SIDE"],
            evidence={"left_timezone": left_tz, "right_timezone": right_tz},
        )
    return DimensionScore(
        score=20,
        reason_codes=["TIMEZONE_MISMATCH"],
        evidence={"left_timezone": left_tz, "right_timezone": right_tz},
        hard_flags={"timezone_mismatch": True},
    )


def score_ambiguity_compatibility(
    left_ambiguity: AmbiguityAssessment | None,
    right_ambiguity: AmbiguityAssessment | None,
) -> DimensionScore:
    if left_ambiguity is None or right_ambiguity is None:
        return DimensionScore(
            score=35,
            reason_codes=["AMBIGUITY_ASSESSMENT_MISSING"],
            hard_flags={"insufficient_rule_data": True},
        )
    highest = max(left_ambiguity.overall_score, right_ambiguity.overall_score)
    divergence = abs(left_ambiguity.overall_score - right_ambiguity.overall_score)
    if highest >= 80:
        score = 20
        reasons = ["HIGH_AMBIGUITY"]
        high_ambiguity = True
    elif highest >= 50:
        score = max(30, 75 - divergence)
        reasons = ["MODERATE_AMBIGUITY"]
        high_ambiguity = False
    else:
        score = max(70, 100 - divergence)
        reasons = ["LOW_AMBIGUITY_COMPATIBLE"]
        high_ambiguity = False
    return DimensionScore(
        score=_clamp(score),
        reason_codes=reasons,
        evidence={
            "left_overall_score": left_ambiguity.overall_score,
            "right_overall_score": right_ambiguity.overall_score,
            "score_divergence": divergence,
        },
        hard_flags={"high_ambiguity": high_ambiguity},
    )


def score_venue_rule_compatibility(
    left_rule_snapshot: MarketRuleSnapshot | None,
    right_rule_snapshot: MarketRuleSnapshot | None,
) -> DimensionScore:
    if left_rule_snapshot is None or right_rule_snapshot is None:
        return DimensionScore(
            score=35,
            reason_codes=["RULE_SNAPSHOT_MISSING"],
            hard_flags={"insufficient_rule_data": True},
        )
    left_terms = _venue_rule_terms(left_rule_snapshot.raw_rule_text)
    right_terms = _venue_rule_terms(right_rule_snapshot.raw_rule_text)
    if not left_terms and not right_terms:
        return DimensionScore(score=60, reason_codes=["DISPUTE_LANGUAGE_NOT_SPECIFIED"])
    score = (
        100
        if left_terms == right_terms
        else token_jaccard_score(" ".join(left_terms), " ".join(right_terms))
    )
    reasons = ["VENUE_RULE_TERMS_ALIGNED"] if score >= 70 else ["VENUE_RULE_TERMS_DIFFER"]
    return DimensionScore(
        score=score,
        reason_codes=reasons,
        evidence={"left_terms": left_terms, "right_terms": right_terms},
    )


def outcome_mapping_score(mappings: list[OutcomeEquivalenceMapping]) -> int:
    if not mappings:
        return 20
    return round(sum(mapping.score for mapping in mappings) / len(mappings))


def inverse_outcome_likely(mappings: list[OutcomeEquivalenceMapping]) -> bool:
    return any(mapping.relation == OutcomeRelation.INVERSE for mapping in mappings)


def _mapping(
    left_outcome: Outcome,
    right_outcome: Outcome | None,
    left_market_id: str,
    right_market_id: str,
    relation: OutcomeRelation,
    score: int,
    evidence: dict[str, Any],
) -> OutcomeEquivalenceMapping:
    digest = hash_payload(
        {
            "left_outcome_id": left_outcome.outcome_id,
            "right_outcome_id": right_outcome.outcome_id if right_outcome else None,
            "relation": relation.value,
            "score": score,
        }
    )
    return OutcomeEquivalenceMapping(
        outcome_mapping_id=f"outcome_mapping_{digest[:24]}",
        equivalence_assessment_id="pending",
        left_market_id=left_market_id,
        right_market_id=right_market_id,
        left_outcome_id=left_outcome.outcome_id,
        right_outcome_id=right_outcome.outcome_id if right_outcome else None,
        left_label=left_outcome.label,
        right_label=right_outcome.label if right_outcome else None,
        relation=relation,
        score=_clamp(score),
        evidence=evidence,
    )


def _normalized_labels(outcomes: list[Outcome]) -> list[str]:
    return [normalize_outcome_label(outcome.label) for outcome in outcomes]


def _is_binary_yes_no(labels: list[str]) -> bool:
    return set(labels) == {"yes", "no"}


def _label_overlap_score(left_labels: list[str], right_labels: list[str]) -> int:
    if not left_labels or not right_labels:
        return 20
    return round(
        100
        * len(set(left_labels) & set(right_labels))
        / len(set(left_labels) | set(right_labels))
    )


def _score_text_alignment(
    left_text: str | None,
    right_text: str | None,
    *,
    exact_reason: str,
    weak_reason: str,
    mismatch_reason: str,
    mismatch_flag: str,
) -> DimensionScore:
    left_norm = normalize_text(left_text)
    right_norm = normalize_text(right_text)
    if not left_norm or not right_norm:
        return DimensionScore(
            score=30,
            reason_codes=[weak_reason],
            evidence={"left_text": left_text, "right_text": right_text},
            hard_flags={"insufficient_rule_data": True},
        )
    if left_norm == right_norm:
        return DimensionScore(
            score=100,
            reason_codes=[exact_reason],
            evidence={"left_text": left_text, "right_text": right_text},
        )
    similarity = token_jaccard_score(left_text, right_text)
    mismatch = similarity < 50
    return DimensionScore(
        score=similarity,
        reason_codes=[mismatch_reason if mismatch else weak_reason],
        evidence={"left_text": left_text, "right_text": right_text, "similarity": similarity},
        hard_flags={mismatch_flag: mismatch},
    )


def _source_text(
    rule_snapshot: MarketRuleSnapshot | None,
    predicate: ResolutionPredicate | None,
) -> str | None:
    if rule_snapshot is not None and rule_snapshot.resolution_source:
        return rule_snapshot.resolution_source
    if predicate is not None and predicate.resolution_source_id:
        return predicate.resolution_source_id
    return None


def _authority_text(
    rule_snapshot: MarketRuleSnapshot | None,
    predicate: ResolutionPredicate | None,
) -> str | None:
    if rule_snapshot is not None and rule_snapshot.settlement_authority:
        return rule_snapshot.settlement_authority
    if predicate is not None and predicate.settlement_authority:
        return predicate.settlement_authority
    return None


def _deadline(predicate: ResolutionPredicate | None) -> datetime | None:
    if predicate is None:
        return None
    return predicate.time_window_end or predicate.time_window_start


def _timezone(
    predicate: ResolutionPredicate | None,
    rule_snapshot: MarketRuleSnapshot | None,
) -> str | None:
    if predicate is not None and predicate.time_zone:
        return predicate.time_zone
    if rule_snapshot is not None and rule_snapshot.time_zone:
        return rule_snapshot.time_zone
    return None


def _normalize_tz(value: str | None) -> str | None:
    if value is None:
        return None
    mapping = {
        "america/new_york": "ET",
        "edt": "ET",
        "est": "ET",
        "et": "ET",
        "utc": "UTC",
        "z": "UTC",
    }
    return mapping.get(normalize_text(value), value.strip().upper())


def _venue_specific_authority_pair(left_text: str | None, right_text: str | None) -> bool:
    left = normalize_text(left_text)
    right = normalize_text(right_text)
    return {left, right}.issubset({"kalshi", "polymarket"}) and left != right


def _unit(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = normalize_text(value)
    aliases = {
        "inch": "inches",
        "in": "inches",
        "percent": "%",
        "percentage": "%",
        "usd": "$",
    }
    return aliases.get(normalized, normalized)


def _venue_rule_terms(raw_text: str) -> list[str]:
    tokens = tokenize(raw_text)
    terms = [
        token
        for token in tokens
        if token
        in {
            "appeal",
            "appeals",
            "discretion",
            "dispute",
            "disputes",
            "final",
            "manual",
            "review",
            "override",
            "settlement",
        }
    ]
    return sorted(dict.fromkeys(terms))


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _clamp(value: int | float | Decimal) -> int:
    return max(0, min(100, round(value)))
