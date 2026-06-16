from __future__ import annotations

from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.scoring.resolution_risk import score_resolution_risk


def test_resolution_risk_clean_vs_ambiguous_rules() -> None:
    clean, ambiguous = sample_markets()

    clean_result = score_resolution_risk(clean.market, clean.rule_snapshot)
    ambiguous_result = score_resolution_risk(ambiguous.market, ambiguous.rule_snapshot)

    assert clean_result.resolution_risk_score == 0
    assert clean_result.reason_codes == []
    assert ambiguous_result.resolution_risk_score == 100
    assert "missing_resolution_source" in ambiguous_result.reason_codes
    assert "missing_settlement_authority" in ambiguous_result.reason_codes
    assert "multiple_possible_resolution_sources" in ambiguous_result.reason_codes


def test_resolution_risk_missing_snapshot_is_max_risk() -> None:
    clean, _ = sample_markets()

    result = score_resolution_risk(clean.market, None)

    assert result.resolution_risk_score == 100
    assert result.reason_codes == ["missing_rule_snapshot"]
