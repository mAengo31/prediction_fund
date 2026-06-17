"""Deterministic v1 ambiguity assessment for market resolution rules."""

from __future__ import annotations

import hashlib
import re

from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.resolution.models import (
    AmbiguityAssessment,
    EvidenceSpan,
    ResolutionPredicate,
)

MONTH_NAMES = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def assess_rule_ambiguity(
    market: Market,
    rule_snapshot: MarketRuleSnapshot,
    predicate: ResolutionPredicate | None = None,
) -> AmbiguityAssessment:
    del market

    raw_text = rule_snapshot.raw_rule_text or ""
    lower_text = raw_text.lower()
    reason_codes: list[str] = []
    evidence_spans: list[EvidenceSpan] = []

    source_score = 0
    temporal_score = 0
    definition_score = 0
    measurement_score = 0
    actor_score = 0
    threshold_score = 0
    dispute_score = 0
    exceptional_score = 0
    venue_score = 0

    def add(
        code: str,
        points: int,
        dimension: str,
        pattern: str | None = None,
        text: str | None = None,
    ) -> int:
        if code not in reason_codes:
            reason_codes.append(code)
        evidence_spans.append(_evidence(code, dimension, raw_text, pattern, text))
        return points

    if not _has_text(rule_snapshot.resolution_source) and not (
        predicate and predicate.resolution_source_id
    ):
        source_score += add("MISSING_RESOLUTION_SOURCE", 30, "source")
    if re.search(
        r"\band/or\b|\bvarious sources\b|\bofficial sources\b|\bcredible sources\b",
        lower_text,
    ):
        source_score += add(
            "MULTIPLE_POSSIBLE_SOURCES",
            20,
            "source",
            r"\band/or\b|\bvarious sources\b|\bofficial sources\b|\bcredible sources\b",
        )
    if re.search(r"\breports\b|\breportedly\b", lower_text):
        source_score += add(
            "SOURCE_DESCRIBED_AS_REPORTS",
            15,
            "source",
            r"\breports\b|\breportedly\b",
        )
    if re.search(r"\bofficial sources\b|\bcredible sources\b", lower_text) and not _has_text(
        rule_snapshot.resolution_source
    ):
        source_score += add(
            "NON_CANONICAL_SOURCE",
            15,
            "source",
            r"\bofficial sources\b|\bcredible sources\b",
        )

    has_deadline_language = bool(
        re.search(
            r"\b(before|by|deadline|on or before|before the end of)\b",
            lower_text,
        )
    )
    if has_deadline_language and not _has_text(rule_snapshot.time_zone) and not (
        predicate and predicate.time_zone
    ):
        temporal_score += add("MISSING_TIMEZONE", 25, "temporal")
    if re.search(r"\bsoon\b|\baround\b|\bapproximately\b|\bexpected\b|\banticipated\b", lower_text):
        temporal_score += add(
            "VAGUE_DEADLINE",
            20,
            "temporal",
            r"\bsoon\b|\baround\b|\bapproximately\b|\bexpected\b|\banticipated\b",
        )
    if re.search(r"\bsoon\b|\beventually\b|\bshortly\b|\bbefore the end of\b", lower_text):
        temporal_score += add(
            "RELATIVE_TIME_WORDING",
            15,
            "temporal",
            r"\bsoon\b|\beventually\b|\bshortly\b|\bbefore the end of\b",
        )
    if _has_month_without_day(lower_text):
        temporal_score += add("MONTH_WITHOUT_DAY", 20, "temporal", _month_without_day_pattern())
    if has_deadline_language and not re.search(r"\b\d{1,2}(:\d{2})?\s*(am|pm)\b", lower_text):
        temporal_score += add("DEADLINE_WITHOUT_TIME", 10, "temporal")
    if "before the end of" in lower_text and not _has_text(rule_snapshot.time_zone) and not (
        predicate and predicate.time_zone
    ):
        temporal_score += add(
            "BEFORE_END_OF_WITHOUT_TIMEZONE",
            20,
            "temporal",
            r"\bbefore the end of\b",
        )

    if re.search(r"\bundefined\b|\bnot defined\b|\bto be determined\b|\bif unclear\b", lower_text):
        definition_score += add(
            "UNDEFINED_KEY_TERM",
            20,
            "definition",
            r"\bundefined\b|\bnot defined\b|\bto be determined\b|\bif unclear\b",
        )
    if re.search(
        r"\blikely\b|\bsubstantially\b|\bmaterially\b|\bsignificant\b|\bcredible\b",
        lower_text,
    ):
        definition_score += add(
            "SUBJECTIVE_WORDING",
            20,
            "definition",
            r"\blikely\b|\bsubstantially\b|\bmaterially\b|\bsignificant\b|\bcredible\b",
        )
    if re.search(
        r"\bmay resolve\b|\bexpected\b|\banticipated\b|\bdepends on interpretation\b",
        lower_text,
    ):
        definition_score += add(
            "VAGUE_CONDITION",
            15,
            "definition",
            r"\bmay resolve\b|\bexpected\b|\banticipated\b|\bdepends on interpretation\b",
        )
    if "interpretation" in lower_text or "if unclear" in lower_text:
        definition_score += add(
            "DEPENDS_ON_INTERPRETATION",
            15,
            "definition",
            r"\binterpretation\b|\bif unclear\b",
        )

    threshold_value_present = predicate is not None and predicate.threshold_value is not None
    if threshold_value_present and not re.search(
        r"\baccording to\b|\bmeasured by\b|\bsource\b",
        lower_text,
    ):
        measurement_score += add("MISSING_MEASUREMENT_METHOD", 15, "measurement")
    if re.search(r"\brevised\b|\bpreliminary\b", lower_text):
        measurement_score += add(
            "PRELIMINARY_OR_REVISED_DATA_AMBIGUITY",
            15,
            "measurement",
            r"\brevised\b|\bpreliminary\b",
        )
    if (
        threshold_value_present
        and re.search(r"\bpreliminary\b|\brevised\b", lower_text)
        and not re.search(r"\brevision policy\b|\bfinal\b", lower_text)
    ):
        measurement_score += add("UNSPECIFIED_DATA_REVISION_POLICY", 10, "measurement")

    if re.search(r"\bwhoever\b|\bthey\b|\bofficials\b|\bauthorities\b", lower_text):
        actor_score += add(
            "AMBIGUOUS_ACTOR",
            15,
            "actor",
            r"\bwhoever\b|\bthey\b|\bofficials\b|\bauthorities\b",
        )
    if re.search(
        r"\b(candidate|company|agency|committee)\b.*\bor\b.*"
        r"\b(candidate|company|agency|committee)\b",
        lower_text,
    ):
        actor_score += add("MULTIPLE_ACTORS", 15, "actor", r"\bor\b")
    if "at the discretion" in lower_text:
        actor_score += add("ACTOR_ROLE_UNCLEAR", 15, "actor", r"\bat the discretion\b")

    if (
        predicate is not None
        and predicate.threshold_value is not None
        and not predicate.threshold_unit
    ):
        threshold_score += add("MISSING_THRESHOLD_UNIT", 30, "threshold")
    if re.search(r"\baround\b|\bapproximately\b|\babout\b", lower_text):
        threshold_score += add(
            "APPROXIMATE_THRESHOLD",
            20,
            "threshold",
            r"\baround\b|\bapproximately\b|\babout\b",
        )
    if "between" in lower_text and not re.search(r"\bbetween\b.+\band\b.+", lower_text):
        threshold_score += add("RANGE_ENDPOINT_AMBIGUITY", 20, "threshold", r"\bbetween\b")

    if re.search(r"\bdispute\b|\bappeal\b|\bsubject to review\b|\bif unclear\b", lower_text):
        if "final" not in lower_text:
            dispute_score += add("MISSING_DISPUTE_PROCESS", 20, "dispute")
        if "appeal" not in lower_text:
            dispute_score += add("APPEAL_PROCESS_UNSPECIFIED", 15, "dispute")
    if "at the discretion" in lower_text or "if unclear" in lower_text:
        dispute_score += add(
            "VENUE_FINAL_DECISION_UNCLEAR",
            15,
            "dispute",
            r"\bat the discretion\b|\bif unclear\b",
        )

    if re.search(r"\bcancel(lation|ed)?\b", lower_text) and "not specified" in lower_text:
        exceptional_score += add("CANCELLATION_NOT_SPECIFIED", 10, "exceptional", r"\bcancel")
    if re.search(r"\bpostpone(d|ment)?\b", lower_text) and "not specified" in lower_text:
        exceptional_score += add("POSTPONEMENT_NOT_SPECIFIED", 10, "exceptional", r"\bpostpone")
    if re.search(r"\bdata unavailable\b|\bsource unavailable\b", lower_text):
        exceptional_score += add(
            "DATA_UNAVAILABLE_NOT_SPECIFIED",
            15,
            "exceptional",
            r"\bdata unavailable\b|\bsource unavailable\b",
        )
    if "force majeure" in lower_text and "not specified" in lower_text:
        exceptional_score += add(
            "FORCE_MAJEURE_UNSPECIFIED",
            10,
            "exceptional",
            r"\bforce majeure\b",
        )

    if not _has_text(rule_snapshot.settlement_authority) and not (
        predicate and predicate.settlement_authority
    ):
        venue_score += add("SETTLEMENT_AUTHORITY_MISSING", 25, "venue_adjudication")
    if re.search(r"\bmanual review\b|\bsubject to review\b", lower_text):
        venue_score += add(
            "MANUAL_REVIEW_UNCLEAR",
            15,
            "venue_adjudication",
            r"\bmanual review\b|\bsubject to review\b",
        )
    if re.search(r"\bvenue may\b|\bvenue reserves\b|\boverride\b", lower_text):
        venue_score += add(
            "VENUE_RULE_OVERRIDE_UNCLEAR",
            15,
            "venue_adjudication",
            r"\bvenue may\b|\bvenue reserves\b|\boverride\b",
        )

    scores = {
        "source_ambiguity_score": min(source_score, 100),
        "temporal_ambiguity_score": min(temporal_score, 100),
        "definition_ambiguity_score": min(definition_score, 100),
        "measurement_ambiguity_score": min(measurement_score, 100),
        "actor_ambiguity_score": min(actor_score, 100),
        "threshold_ambiguity_score": min(threshold_score, 100),
        "dispute_ambiguity_score": min(dispute_score, 100),
        "exceptional_case_ambiguity_score": min(exceptional_score, 100),
        "venue_adjudication_ambiguity_score": min(venue_score, 100),
    }
    overall_score = _overall_score(list(scores.values()))

    return AmbiguityAssessment(
        assessment_id=_assessment_id(rule_snapshot.market_id, rule_snapshot.rule_snapshot_id),
        market_id=rule_snapshot.market_id,
        rule_snapshot_id=rule_snapshot.rule_snapshot_id,
        captured_at=rule_snapshot.captured_at,
        overall_score=overall_score,
        reason_codes=reason_codes,
        evidence_spans=evidence_spans,
        metadata={
            "scorer_version": "ambiguity_v1",
            "overall_formula": "round(max_dimension * 0.6 + average_dimension * 0.4)",
        },
        **scores,
    )


def _overall_score(scores: list[int]) -> int:
    if not scores:
        return 0
    return min(round(max(scores) * 0.6 + (sum(scores) / len(scores)) * 0.4), 100)


def _evidence(
    code: str,
    dimension: str,
    raw_text: str,
    pattern: str | None,
    fallback_text: str | None,
) -> EvidenceSpan:
    if pattern:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return EvidenceSpan(
                field_name=dimension,
                text=raw_text[match.start() : match.end()],
                start_char=match.start(),
                end_char=match.end(),
                confidence_score=85,
            )
    return EvidenceSpan(field_name=dimension, text=fallback_text or code, confidence_score=60)


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _has_month_without_day(lower_text: str) -> bool:
    return bool(re.search(_month_without_day_pattern(), lower_text, re.IGNORECASE))


def _month_without_day_pattern() -> str:
    month_group = "|".join(MONTH_NAMES)
    return rf"\bby\s+({month_group})\b(?!\s+\d{{1,2}}(?:st|nd|rd|th)?\b)"


def _assessment_id(market_id: str, rule_snapshot_id: str) -> str:
    digest = hashlib.sha256(
        f"ambiguity_assessment_v1|{market_id}|{rule_snapshot_id}".encode()
    ).hexdigest()
    return f"ambiguity_{digest[:24]}"
