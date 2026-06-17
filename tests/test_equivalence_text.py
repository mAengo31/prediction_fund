from __future__ import annotations

from prediction_desk.equivalence.text import (
    contains_negation_or_inverse,
    normalize_outcome_label,
    normalize_text,
    token_jaccard_score,
    tokenize,
)


def test_text_normalization_and_similarity_are_deterministic() -> None:
    text = "Will NYC record at least 1 inch of rain?"

    assert normalize_text(text) == normalize_text(text.upper())
    assert tokenize(text) == tokenize(text)
    assert token_jaccard_score(text, text) == 100
    assert token_jaccard_score(text, "Will LA reach 90 degrees?") < 50


def test_outcome_label_normalization_and_inverse_detection() -> None:
    assert normalize_outcome_label(" YES ") == "yes"
    assert normalize_outcome_label("No") == "no"
    assert contains_negation_or_inverse("Will the event not happen?")
