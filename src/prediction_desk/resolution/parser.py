"""Deterministic v1 parser for resolution predicates."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from prediction_desk.domain.enums import MarketType
from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.resolution.enums import Comparator, ParseStatus, PredicateType
from prediction_desk.resolution.models import EvidenceSpan, ResolutionPredicate, ResolutionSource

THRESHOLD_TERMS = re.compile(
    r"\b(greater than|less than|at least|at most|above|below|over|under|no less than|"
    r"no more than|greater than or equal|less than or equal)\b",
    re.IGNORECASE,
)
TIMEZONE_RE = re.compile(r"\b(UTC|ET|EST|EDT|CT|CST|CDT|MT|MST|MDT|PT|PST|PDT)\b")
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
MONTH_PATTERN = "|".join(MONTHS)
MONTH_DATE_PATTERN = rf"\b({MONTH_PATTERN})\s+(\d{{1,2}}),\s+(\d{{4}})\b"
MONTH_DATE_RE = re.compile(MONTH_DATE_PATTERN, re.IGNORECASE)
ISO_DATE_RE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
TIME_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\s*(UTC|ET|EST|EDT|CT|CST|CDT|MT|MST|MDT|PT|PST|PDT)?\b",
    re.IGNORECASE,
)
SOURCE_PHRASE_RE = re.compile(
    r"\b(according to|as reported by|as determined by|official|final settlement source|"
    r"source of truth)\b",
    re.IGNORECASE,
)
AUTHORITY_RE = re.compile(
    r"\b(?:determined|settled|resolved|final decision)\s+by\s+([^.;\n]{2,100})",
    re.IGNORECASE,
)


def parse_resolution_predicate(
    market: Market,
    rule_snapshot: MarketRuleSnapshot,
    known_sources: list[ResolutionSource] | None = None,
) -> ResolutionPredicate:
    raw_text = rule_snapshot.raw_rule_text or ""
    stripped = raw_text.strip()
    if not stripped:
        return ResolutionPredicate(
            predicate_id=_predicate_id(market.market_id, rule_snapshot.rule_snapshot_id),
            market_id=market.market_id,
            rule_snapshot_id=rule_snapshot.rule_snapshot_id,
            captured_at=rule_snapshot.captured_at,
            predicate_type=PredicateType.UNKNOWN,
            parse_status=ParseStatus.FAILED,
            subject=market.title,
            condition=None,
            confidence_score=0,
            evidence_spans=[],
            normalized_predicate_text=None,
            metadata={"parser_version": "resolution_parser_v1"},
        )

    evidence: list[EvidenceSpan] = []
    predicate_type = _predicate_type(market, stripped)
    comparator, comparator_span = _extract_comparator(stripped)
    if comparator_span is not None:
        evidence.append(comparator_span)

    threshold_value, threshold_unit, threshold_span = _extract_threshold(stripped)
    if threshold_span is not None:
        evidence.append(threshold_span)

    time_window_start, time_window_end, time_zone, time_spans = _extract_time_window(stripped)
    if rule_snapshot.time_zone:
        time_zone = rule_snapshot.time_zone
        evidence.append(
            EvidenceSpan(
                field_name="time_zone",
                text=rule_snapshot.time_zone,
                confidence_score=95,
            )
        )
    evidence.extend(time_spans)

    source_id, source_text, source_span = _extract_resolution_source(
        stripped, rule_snapshot, known_sources or []
    )
    if source_span is not None:
        evidence.append(source_span)
    elif source_text:
        evidence.append(
            EvidenceSpan(
                field_name="resolution_source",
                text=source_text,
                confidence_score=90,
            )
        )

    settlement_authority, authority_span = _extract_settlement_authority(stripped, rule_snapshot)
    if authority_span is not None:
        evidence.append(authority_span)

    condition = _condition_text(stripped)
    confidence_score = _confidence_score(
        comparator=comparator,
        threshold_value=threshold_value,
        time_window_end=time_window_end,
        source_text=source_text,
        settlement_authority=settlement_authority,
    )
    parse_status = ParseStatus.PARSED if confidence_score >= 75 else ParseStatus.PARTIAL

    return ResolutionPredicate(
        predicate_id=_predicate_id(market.market_id, rule_snapshot.rule_snapshot_id),
        market_id=market.market_id,
        rule_snapshot_id=rule_snapshot.rule_snapshot_id,
        captured_at=rule_snapshot.captured_at,
        predicate_type=predicate_type,
        parse_status=parse_status,
        subject=market.title,
        condition=condition,
        threshold_value=threshold_value,
        threshold_unit=threshold_unit,
        comparator=comparator,
        time_window_start=time_window_start,
        time_window_end=time_window_end,
        time_zone=time_zone,
        resolution_source_id=source_id,
        settlement_authority=settlement_authority,
        confidence_score=confidence_score,
        evidence_spans=evidence,
        normalized_predicate_text=_normalized_predicate_text(
            predicate_type=predicate_type,
            subject=market.title,
            condition=condition,
            comparator=comparator,
            threshold_value=threshold_value,
            threshold_unit=threshold_unit,
            time_window_start=time_window_start,
            time_window_end=time_window_end,
            time_zone=time_zone,
            source_text=source_text,
            settlement_authority=settlement_authority,
        ),
        metadata={"parser_version": "resolution_parser_v1"},
    )


def _predicate_type(market: Market, raw_text: str) -> PredicateType:
    if THRESHOLD_TERMS.search(raw_text):
        return PredicateType.SCALAR_THRESHOLD
    if re.search(r"\bbetween\b", raw_text, re.IGNORECASE):
        return PredicateType.RANGE
    if _has_deadline_signal(raw_text):
        return PredicateType.DATE_DEADLINE
    if market.market_type is MarketType.BINARY:
        return PredicateType.BINARY_EVENT
    if market.market_type is MarketType.MULTI_OUTCOME:
        return PredicateType.MULTI_OUTCOME_EVENT
    if market.market_type is MarketType.SCALAR:
        return PredicateType.SCALAR_THRESHOLD
    return PredicateType.UNKNOWN


def _extract_comparator(raw_text: str) -> tuple[Comparator | None, EvidenceSpan | None]:
    patterns: tuple[tuple[Comparator, str], ...] = (
        (
            Comparator.GREATER_THAN_OR_EQUAL,
            r"\bat least\b|\bgreater than or equal\b|\bno less than\b",
        ),
        (
            Comparator.LESS_THAN_OR_EQUAL,
            r"\bat most\b|\bless than or equal\b|\bno more than\b",
        ),
        (Comparator.GREATER_THAN, r"\bgreater than\b|\babove\b|\bover\b"),
        (Comparator.LESS_THAN, r"\bless than\b|\bbelow\b|\bunder\b"),
        (
            Comparator.ON_OR_BEFORE,
            rf"\bon or before\b|\bby\s+({MONTH_PATTERN}|\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}/)",
        ),
        (Comparator.ON_OR_AFTER, r"\bon or after\b"),
        (Comparator.BETWEEN, r"\bbetween\b"),
        (Comparator.BEFORE, r"\bbefore\b"),
        (Comparator.AFTER, r"\bafter\b"),
    )
    for comparator, pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            return comparator, _span("comparator", raw_text, match, 90)
    return None, None


def _has_deadline_signal(raw_text: str) -> bool:
    if re.search(
        r"\b(before|on or before|after|on or after|between|deadline)\b",
        raw_text,
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            rf"\bby\s+({MONTH_PATTERN}|\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}/)",
            raw_text,
            re.IGNORECASE,
        )
    )


def _extract_threshold(raw_text: str) -> tuple[Decimal | None, str | None, EvidenceSpan | None]:
    percent_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(%|percent)\b", raw_text, re.IGNORECASE)
    if percent_match:
        return (
            _decimal(percent_match.group(1)),
            "percent",
            _span("threshold_value", raw_text, percent_match, 95),
        )

    currency_match = re.search(
        r"\$(\d[\d,]*(?:\.\d+)?)\s*(billion|million|thousand)?\b",
        raw_text,
        re.IGNORECASE,
    )
    if currency_match:
        value = _decimal(currency_match.group(1).replace(",", ""))
        multiplier_text = (currency_match.group(2) or "").lower()
        if value is not None:
            if multiplier_text == "billion":
                value *= Decimal("1000000000")
            elif multiplier_text == "million":
                value *= Decimal("1000000")
            elif multiplier_text == "thousand":
                value *= Decimal("1000")
        return value, "USD", _span("threshold_value", raw_text, currency_match, 95)

    unit_pattern = re.compile(
        r"\b(\d+(?:\.\d+)?)\s+([A-Za-z][A-Za-z]*(?:\s+[A-Za-z][A-Za-z]*){0,3})\b",
    )
    for unit_match in unit_pattern.finditer(raw_text):
        unit = _clean_unit(unit_match.group(2))
        value = _decimal(unit_match.group(1))
        if value is not None and _looks_like_threshold_unit(unit, value):
            return value, unit, _span("threshold_value", raw_text, unit_match, 85)
    return None, None, None


def _extract_time_window(
    raw_text: str,
) -> tuple[datetime | None, datetime | None, str | None, list[EvidenceSpan]]:
    evidence: list[EvidenceSpan] = []
    time_zone = _extract_timezone(raw_text)
    if time_zone is not None:
        tz_match = TIMEZONE_RE.search(raw_text)
        if tz_match:
            evidence.append(_span("time_zone", raw_text, tz_match, 90))

    between_match = re.search(
        rf"\bbetween\s+({MONTH_DATE_PATTERN})\s+and\s+({MONTH_DATE_PATTERN})",
        raw_text,
        re.IGNORECASE,
    )
    if between_match:
        dates = [
            match
            for match in MONTH_DATE_RE.finditer(raw_text)
            if between_match.start() <= match.start() <= between_match.end()
        ]
        if len(dates) >= 2:
            start = _datetime_from_month_match(dates[0], raw_text)
            end = _datetime_from_month_match(dates[1], raw_text)
            evidence.append(_span("time_window_start", raw_text, dates[0], 90))
            evidence.append(_span("time_window_end", raw_text, dates[1], 90))
            return start, end, time_zone, evidence

    date_match = MONTH_DATE_RE.search(raw_text)
    if date_match:
        parsed = _datetime_from_month_match(date_match, raw_text)
        evidence.append(_span("time_window_end", raw_text, date_match, 90))
        return None, parsed, time_zone, evidence

    iso_match = ISO_DATE_RE.search(raw_text)
    if iso_match:
        year, month, day = (int(part) for part in iso_match.groups())
        evidence.append(_span("time_window_end", raw_text, iso_match, 85))
        return None, datetime(year, month, day, tzinfo=UTC), time_zone, evidence

    return None, None, time_zone, evidence


def _extract_resolution_source(
    raw_text: str,
    rule_snapshot: MarketRuleSnapshot,
    known_sources: list[ResolutionSource],
) -> tuple[str | None, str | None, EvidenceSpan | None]:
    if rule_snapshot.resolution_source and rule_snapshot.resolution_source.strip():
        matched_source = _match_known_source(rule_snapshot.resolution_source, known_sources)
        return (
            matched_source.source_id if matched_source else None,
            rule_snapshot.resolution_source,
            EvidenceSpan(
                field_name="resolution_source",
                text=rule_snapshot.resolution_source,
                confidence_score=95,
            ),
        )

    for source in known_sources:
        match = re.search(re.escape(source.canonical_name), raw_text, re.IGNORECASE)
        if match:
            return (
                source.source_id,
                source.canonical_name,
                _span("resolution_source", raw_text, match, 90),
            )

    source_phrase = SOURCE_PHRASE_RE.search(raw_text)
    if source_phrase:
        fragment = raw_text[source_phrase.start() : min(len(raw_text), source_phrase.end() + 120)]
        return (
            None,
            _condition_text(fragment),
            _span("resolution_source", raw_text, source_phrase, 60),
        )

    return None, None, None


def _extract_settlement_authority(
    raw_text: str, rule_snapshot: MarketRuleSnapshot
) -> tuple[str | None, EvidenceSpan | None]:
    if rule_snapshot.settlement_authority and rule_snapshot.settlement_authority.strip():
        return (
            rule_snapshot.settlement_authority,
            EvidenceSpan(
                field_name="settlement_authority",
                text=rule_snapshot.settlement_authority,
                confidence_score=95,
            ),
        )
    authority_match = AUTHORITY_RE.search(raw_text)
    if authority_match:
        authority = authority_match.group(1).strip()
        return authority, _span("settlement_authority", raw_text, authority_match, 75)
    return None, None


def _datetime_from_month_match(match: re.Match[str], raw_text: str | None = None) -> datetime:
    month = MONTHS[match.group(1).lower()]
    day = int(match.group(2))
    year = int(match.group(3))
    hour = 0
    minute = 0
    if raw_text is not None:
        prefix = raw_text[max(0, match.start() - 50) : match.start()]
        time_match = TIME_RE.search(prefix)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2) or "0")
            if time_match.group(3).upper() == "PM" and hour != 12:
                hour += 12
            if time_match.group(3).upper() == "AM" and hour == 12:
                hour = 0
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _extract_timezone(raw_text: str) -> str | None:
    match = TIMEZONE_RE.search(raw_text)
    return match.group(1).upper() if match else None


def _match_known_source(
    text: str, known_sources: list[ResolutionSource]
) -> ResolutionSource | None:
    normalized = text.lower()
    for source in known_sources:
        if source.canonical_name.lower() in normalized:
            return source
    return None


def _confidence_score(
    *,
    comparator: Comparator | None,
    threshold_value: Decimal | None,
    time_window_end: datetime | None,
    source_text: str | None,
    settlement_authority: str | None,
) -> int:
    score = 45
    if comparator is not None:
        score += 10
    if threshold_value is not None:
        score += 12
    if time_window_end is not None:
        score += 10
    if source_text:
        score += 13
    if settlement_authority:
        score += 10
    return min(score, 100)


def _normalized_predicate_text(
    *,
    predicate_type: PredicateType,
    subject: str,
    condition: str | None,
    comparator: Comparator | None,
    threshold_value: Decimal | None,
    threshold_unit: str | None,
    time_window_start: datetime | None,
    time_window_end: datetime | None,
    time_zone: str | None,
    source_text: str | None,
    settlement_authority: str | None,
) -> str:
    pieces = [f"type={predicate_type.value}", f"subject={_normalize_space(subject)}"]
    if condition:
        pieces.append(f"condition={_normalize_space(condition)}")
    if comparator:
        pieces.append(f"comparator={comparator.value}")
    if threshold_value is not None:
        pieces.append(f"threshold={threshold_value.normalize()}")
    if threshold_unit:
        pieces.append(f"unit={threshold_unit}")
    if time_window_start:
        pieces.append(f"start={time_window_start.isoformat()}")
    if time_window_end:
        pieces.append(f"end={time_window_end.isoformat()}")
    if time_zone:
        pieces.append(f"time_zone={time_zone}")
    if source_text:
        pieces.append(f"source={_normalize_space(source_text)}")
    if settlement_authority:
        pieces.append(f"authority={_normalize_space(settlement_authority)}")
    return " | ".join(pieces)


def _condition_text(raw_text: str) -> str:
    first_sentence = re.split(r"(?<=[.!?])\s+", raw_text.strip(), maxsplit=1)[0]
    return _normalize_space(first_sentence[:240])


def _span(field_name: str, raw_text: str, match: re.Match[str], confidence: int) -> EvidenceSpan:
    return EvidenceSpan(
        field_name=field_name,
        text=raw_text[match.start() : match.end()],
        start_char=match.start(),
        end_char=match.end(),
        confidence_score=confidence,
    )


def _predicate_id(market_id: str, rule_snapshot_id: str) -> str:
    digest = hashlib.sha256(
        f"resolution_predicate_v1|{market_id}|{rule_snapshot_id}".encode()
    ).hexdigest()
    return f"predicate_{digest[:24]}"


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _clean_unit(unit: str) -> str:
    words = re.sub(r"\s+", " ", unit).strip().lower().split()
    stop_words = {"for", "on", "by", "before", "after", "if", "in", "at", "from", "to"}
    kept: list[str] = []
    for word in words:
        if word in stop_words:
            break
        kept.append(word)
    return " ".join(kept)


def _looks_like_threshold_unit(unit: str, value: Decimal) -> bool:
    if not unit:
        return False
    first_word = unit.split()[0]
    if first_word.lower() in MONTHS or first_word.lower() in {"am", "pm", "utc", "et", "pt"}:
        return False
    if value >= Decimal("1900") and first_word.lower() in {"and", "to"}:
        return False
    return first_word not in {"the", "a", "an", "if", "on", "by", "before", "after"}


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
