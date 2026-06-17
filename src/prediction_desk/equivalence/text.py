"""Deterministic text utilities for conservative contract matching."""

from __future__ import annotations

import re
import unicodedata

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "market",
    "of",
    "on",
    "or",
    "question",
    "resolve",
    "resolves",
    "that",
    "the",
    "this",
    "to",
    "will",
    "with",
}

_INVERSE_TERMS = {
    "fail",
    "fails",
    "fewer",
    "less",
    "no",
    "not",
    "under",
    "without",
}


def normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    normalized = unicodedata.normalize("NFKD", text).casefold()
    normalized = re.sub(r"[^a-z0-9%$]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def tokenize(text: str | None) -> list[str]:
    return [
        token
        for token in normalize_text(text).split()
        if token and token not in _STOPWORDS
    ]


def token_jaccard_score(a: str | None, b: str | None) -> int:
    left = set(tokenize(a))
    right = set(tokenize(b))
    if not left and not right:
        return 0
    if not left or not right:
        return 0
    return round(100 * len(left & right) / len(left | right))


def contains_negation_or_inverse(text: str | None) -> bool:
    return any(token in _INVERSE_TERMS for token in tokenize(text))


def extract_key_terms(text: str | None) -> list[str]:
    terms = [token for token in tokenize(text) if len(token) > 2 or token.isdigit()]
    return sorted(dict.fromkeys(terms))


def normalize_outcome_label(label: str | None) -> str:
    text = normalize_text(label)
    if text in {"y", "yes", "true", "1"}:
        return "yes"
    if text in {"n", "no", "false", "0"}:
        return "no"
    return text
