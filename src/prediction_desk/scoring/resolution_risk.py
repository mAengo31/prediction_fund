"""Deterministic v0 resolution-risk scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass

from prediction_desk.domain.models import Market, MarketRuleSnapshot

AMBIGUOUS_TIMING_PATTERNS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    ("ambiguous_timing_soon", re.compile(r"\bsoon\b", re.IGNORECASE), 12),
    ("ambiguous_timing_around", re.compile(r"\baround\b", re.IGNORECASE), 10),
    ("ambiguous_timing_approximately", re.compile(r"\bapproximately\b", re.IGNORECASE), 10),
    ("ambiguous_timing_expected", re.compile(r"\bexpected\b", re.IGNORECASE), 10),
    ("ambiguous_timing_anticipated", re.compile(r"\banticipated\b", re.IGNORECASE), 10),
    (
        "ambiguous_by_month_without_date",
        re.compile(
            r"\bby\s+"
            r"(january|february|march|april|may|june|july|august|september|october|"
            r"november|december)\b(?!\s+\d{1,2}(?:st|nd|rd|th)?\b)",
            re.IGNORECASE,
        ),
        18,
    ),
)

MULTIPLE_SOURCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("multiple_sources_and_or", re.compile(r"\band/or\b", re.IGNORECASE)),
    ("multiple_sources_various_sources", re.compile(r"\bvarious sources\b", re.IGNORECASE)),
    ("multiple_sources_reports", re.compile(r"\breports\b", re.IGNORECASE)),
    ("multiple_sources_or", re.compile(r"\bor\b", re.IGNORECASE)),
)


@dataclass(frozen=True)
class ResolutionRiskResult:
    resolution_risk_score: int
    reason_codes: list[str]


def score_resolution_risk(
    market: Market, rule_snapshot: MarketRuleSnapshot | None
) -> ResolutionRiskResult:
    """Score resolution risk from deterministic text and metadata heuristics."""

    del market

    if rule_snapshot is None:
        return ResolutionRiskResult(
            resolution_risk_score=100,
            reason_codes=["missing_rule_snapshot"],
        )

    score = 0
    reason_codes: list[str] = []
    raw_rule_text = rule_snapshot.raw_rule_text.strip()

    if not raw_rule_text:
        score += 70
        reason_codes.append("missing_raw_rule_text")

    if not _has_text(rule_snapshot.resolution_source):
        score += 20
        reason_codes.append("missing_resolution_source")

    if not _has_text(rule_snapshot.settlement_authority):
        score += 15
        reason_codes.append("missing_settlement_authority")

    for reason_code, pattern, points in AMBIGUOUS_TIMING_PATTERNS:
        if pattern.search(raw_rule_text):
            score += points
            reason_codes.append(reason_code)

    if (
        re.search(r"\bbefore the end of\b", raw_rule_text, re.IGNORECASE)
        and not _has_text(rule_snapshot.time_zone)
    ):
        score += 15
        reason_codes.append("ambiguous_end_of_period_without_timezone")

    if _has_multiple_source_signal(raw_rule_text):
        score += 15
        reason_codes.append("multiple_possible_resolution_sources")

    return ResolutionRiskResult(
        resolution_risk_score=min(score, 100),
        reason_codes=reason_codes,
    )


def _has_text(value: str | None) -> bool:
    return value is not None and bool(value.strip())


def _has_multiple_source_signal(raw_rule_text: str) -> bool:
    source_text = re.sub(
        r"\b(greater|less)\s+than\s+or\s+equal\s+to\b",
        "",
        raw_rule_text,
        flags=re.IGNORECASE,
    )
    return any(pattern.search(source_text) for _, pattern in MULTIPLE_SOURCE_PATTERNS)
