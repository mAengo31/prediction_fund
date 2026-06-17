"""Deterministic rule snapshot diffing."""

from __future__ import annotations

import hashlib
import re

from prediction_desk.domain.models import MarketRuleSnapshot
from prediction_desk.resolution.enums import RuleSemanticChangeFlag
from prediction_desk.resolution.models import RuleSnapshotDiff

DEADLINE_RE = re.compile(
    r"\b(before|by|on or before|after|on or after|deadline|end of|"
    r"january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b",
    re.IGNORECASE,
)
THRESHOLD_RE = re.compile(
    r"\b(greater than|less than|at least|at most|above|below|over|under|"
    r"\$?\d+(?:\.\d+)?%?|percent|inches|seats|votes)\b",
    re.IGNORECASE,
)
DISPUTE_RE = re.compile(r"\b(dispute|appeal|review|final decision|manual)\b", re.IGNORECASE)
OUTCOME_RE = re.compile(
    r"\b(resolve[s]? yes|resolve[s]? no|outcome|payout|result)\b",
    re.IGNORECASE,
)


def diff_rule_snapshots(
    from_snapshot: MarketRuleSnapshot,
    to_snapshot: MarketRuleSnapshot,
) -> RuleSnapshotDiff:
    raw_text_changed = from_snapshot.raw_rule_text != to_snapshot.raw_rule_text
    normalized_text_changed = (
        from_snapshot.normalized_rule_text != to_snapshot.normalized_rule_text
    )
    resolution_source_changed = (
        _normalize_optional(from_snapshot.resolution_source)
        != _normalize_optional(to_snapshot.resolution_source)
    )
    settlement_authority_changed = (
        _normalize_optional(from_snapshot.settlement_authority)
        != _normalize_optional(to_snapshot.settlement_authority)
    )
    time_zone_changed = _normalize_optional(from_snapshot.time_zone) != _normalize_optional(
        to_snapshot.time_zone
    )

    from_fragments = _fragments(from_snapshot.raw_rule_text)
    to_fragments = _fragments(to_snapshot.raw_rule_text)
    removed_text_fragments = sorted(from_fragments - to_fragments)
    added_text_fragments = sorted(to_fragments - from_fragments)

    changed_terms = _changed_terms(from_snapshot.raw_rule_text, to_snapshot.raw_rule_text)
    semantic_change_flags = _semantic_flags(
        from_snapshot=from_snapshot,
        to_snapshot=to_snapshot,
        raw_text_changed=raw_text_changed,
        resolution_source_changed=resolution_source_changed,
        settlement_authority_changed=settlement_authority_changed,
        time_zone_changed=time_zone_changed,
    )

    return RuleSnapshotDiff(
        diff_id=_diff_id(from_snapshot, to_snapshot),
        market_id=to_snapshot.market_id,
        from_rule_snapshot_id=from_snapshot.rule_snapshot_id,
        to_rule_snapshot_id=to_snapshot.rule_snapshot_id,
        created_at=to_snapshot.captured_at,
        raw_text_changed=raw_text_changed,
        normalized_text_changed=normalized_text_changed,
        resolution_source_changed=resolution_source_changed,
        settlement_authority_changed=settlement_authority_changed,
        time_zone_changed=time_zone_changed,
        old_rule_hash=from_snapshot.rule_hash,
        new_rule_hash=to_snapshot.rule_hash,
        changed_terms=changed_terms,
        added_text_fragments=added_text_fragments,
        removed_text_fragments=removed_text_fragments,
        semantic_change_flags=[flag.value for flag in semantic_change_flags],
        metadata={"diff_version": "rule_diff_v1"},
    )


def _semantic_flags(
    *,
    from_snapshot: MarketRuleSnapshot,
    to_snapshot: MarketRuleSnapshot,
    raw_text_changed: bool,
    resolution_source_changed: bool,
    settlement_authority_changed: bool,
    time_zone_changed: bool,
) -> list[RuleSemanticChangeFlag]:
    flags: list[RuleSemanticChangeFlag] = []
    if resolution_source_changed:
        flags.append(RuleSemanticChangeFlag.RESOLUTION_SOURCE_CHANGED)
    if settlement_authority_changed:
        flags.append(RuleSemanticChangeFlag.SETTLEMENT_AUTHORITY_CHANGED)
    if time_zone_changed:
        flags.append(RuleSemanticChangeFlag.TIMEZONE_CHANGED)
    if _pattern_context_changed(
        DEADLINE_RE,
        from_snapshot.raw_rule_text,
        to_snapshot.raw_rule_text,
    ):
        flags.append(RuleSemanticChangeFlag.DEADLINE_CHANGED)
    if _pattern_context_changed(
        THRESHOLD_RE,
        from_snapshot.raw_rule_text,
        to_snapshot.raw_rule_text,
    ):
        flags.append(RuleSemanticChangeFlag.THRESHOLD_CHANGED)
    if _pattern_context_changed(DISPUTE_RE, from_snapshot.raw_rule_text, to_snapshot.raw_rule_text):
        flags.append(RuleSemanticChangeFlag.DISPUTE_PROCESS_CHANGED)
    if _pattern_context_changed(OUTCOME_RE, from_snapshot.raw_rule_text, to_snapshot.raw_rule_text):
        flags.append(RuleSemanticChangeFlag.OUTCOME_DEFINITION_CHANGED)

    if raw_text_changed and _normalize_space(from_snapshot.raw_rule_text) == _normalize_space(
        to_snapshot.raw_rule_text
    ):
        flags.append(RuleSemanticChangeFlag.ONLY_WHITESPACE_OR_FORMATTING)
    elif raw_text_changed:
        flags.append(RuleSemanticChangeFlag.MATERIAL_RULE_TEXT_CHANGE)

    return flags


def _pattern_context_changed(pattern: re.Pattern[str], old_text: str, new_text: str) -> bool:
    old_terms = sorted({match.group(0).lower() for match in pattern.finditer(old_text)})
    new_terms = sorted({match.group(0).lower() for match in pattern.finditer(new_text)})
    return old_terms != new_terms


def _fragments(raw_text: str) -> set[str]:
    fragments = {
        _normalize_space(fragment)
        for fragment in re.split(r"(?<=[.!?])\s+|\n+", raw_text)
        if _normalize_space(fragment)
    }
    return fragments


def _changed_terms(old_text: str, new_text: str) -> list[str]:
    old_terms = _terms(old_text)
    new_terms = _terms(new_text)
    return sorted(old_terms ^ new_terms)


def _terms(raw_text: str) -> set[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "by",
        "for",
        "if",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "this",
        "to",
    }
    return {
        term
        for term in re.findall(r"[a-zA-Z0-9_$%]+", raw_text.lower())
        if (len(term) > 2 or any(char.isdigit() for char in term)) and term not in stop_words
    }


def _diff_id(from_snapshot: MarketRuleSnapshot, to_snapshot: MarketRuleSnapshot) -> str:
    digest = hashlib.sha256(
        (
            "rule_diff_v1|"
            f"{from_snapshot.rule_snapshot_id}|{to_snapshot.rule_snapshot_id}|"
            f"{from_snapshot.rule_hash}|{to_snapshot.rule_hash}"
        ).encode()
    ).hexdigest()
    return f"rule_diff_{digest[:24]}"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_space(value).lower()


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
