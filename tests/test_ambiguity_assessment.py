from __future__ import annotations

from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.resolution.ambiguity import assess_rule_ambiguity
from prediction_desk.resolution.parser import parse_resolution_predicate


def test_ambiguity_scores_clean_rule_lower_than_vague_rule() -> None:
    clean, ambiguous, *_ = sample_markets()
    clean_predicate = parse_resolution_predicate(clean.market, clean.rule_snapshot)
    ambiguous_predicate = parse_resolution_predicate(ambiguous.market, ambiguous.rule_snapshot)

    clean_assessment = assess_rule_ambiguity(clean.market, clean.rule_snapshot, clean_predicate)
    ambiguous_assessment = assess_rule_ambiguity(
        ambiguous.market,
        ambiguous.rule_snapshot,
        ambiguous_predicate,
    )

    assert clean_assessment.overall_score < ambiguous_assessment.overall_score
    assert clean_assessment.overall_score == 0
    assert ambiguous_assessment.overall_score >= 50


def test_ambiguity_reason_codes_fire_for_vague_source_and_timing() -> None:
    _, ambiguous, *_ = sample_markets()
    predicate = parse_resolution_predicate(ambiguous.market, ambiguous.rule_snapshot)

    assessment = assess_rule_ambiguity(ambiguous.market, ambiguous.rule_snapshot, predicate)

    assert "MISSING_RESOLUTION_SOURCE" in assessment.reason_codes
    assert "VAGUE_DEADLINE" in assessment.reason_codes
    assert "MISSING_TIMEZONE" in assessment.reason_codes
    assert "MULTIPLE_POSSIBLE_SOURCES" in assessment.reason_codes
    assert "SOURCE_DESCRIBED_AS_REPORTS" in assessment.reason_codes
    assert "SUBJECTIVE_WORDING" in assessment.reason_codes
    assert assessment.evidence_spans


def test_ambiguity_reason_codes_fire_for_vague_deadline_fixture() -> None:
    *_, vague_deadline, _rule_change = sample_markets()
    predicate = parse_resolution_predicate(vague_deadline.market, vague_deadline.rule_snapshot)

    assessment = assess_rule_ambiguity(
        vague_deadline.market,
        vague_deadline.rule_snapshot,
        predicate,
    )

    assert "BEFORE_END_OF_WITHOUT_TIMEZONE" in assessment.reason_codes
    assert "MISSING_TIMEZONE" in assessment.reason_codes
    assert "NON_CANONICAL_SOURCE" in assessment.reason_codes
    assert "DEPENDS_ON_INTERPRETATION" in assessment.reason_codes
