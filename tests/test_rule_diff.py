from __future__ import annotations

from datetime import UTC, datetime

from prediction_desk.domain.models import MarketRuleSnapshot
from prediction_desk.examples.sample_markets import sample_markets
from prediction_desk.resolution.diff import diff_rule_snapshots
from prediction_desk.resolution.enums import RuleSemanticChangeFlag


def test_diff_detects_resolution_source_and_deadline_changes() -> None:
    *_, rule_change = sample_markets()
    previous, latest = rule_change.rule_snapshots

    diff = diff_rule_snapshots(previous, latest)
    repeated = diff_rule_snapshots(previous, latest)

    assert diff.resolution_source_changed is True
    assert diff == repeated
    assert diff.created_at == latest.captured_at
    assert RuleSemanticChangeFlag.RESOLUTION_SOURCE_CHANGED.value in diff.semantic_change_flags
    assert RuleSemanticChangeFlag.DEADLINE_CHANGED.value in diff.semantic_change_flags
    assert RuleSemanticChangeFlag.MATERIAL_RULE_TEXT_CHANGE.value in diff.semantic_change_flags


def test_diff_detects_settlement_authority_change() -> None:
    previous = _snapshot(
        "rule_authority_v1",
        "This market resolves YES by September 30, 2026. Settled by Authority A.",
        settlement_authority="Authority A",
    )
    latest = _snapshot(
        "rule_authority_v2",
        "This market resolves YES by September 30, 2026. Settled by Authority B.",
        settlement_authority="Authority B",
    )

    diff = diff_rule_snapshots(previous, latest)

    assert diff.settlement_authority_changed is True
    assert RuleSemanticChangeFlag.SETTLEMENT_AUTHORITY_CHANGED.value in diff.semantic_change_flags


def test_diff_detects_threshold_wording_change() -> None:
    previous = _snapshot(
        "rule_threshold_v1",
        "This market resolves YES if rainfall is at least 10 inches.",
    )
    latest = _snapshot(
        "rule_threshold_v2",
        "This market resolves YES if rainfall is at least 12 inches.",
    )

    diff = diff_rule_snapshots(previous, latest)

    assert RuleSemanticChangeFlag.THRESHOLD_CHANGED.value in diff.semantic_change_flags
    assert "10" in diff.changed_terms
    assert "12" in diff.changed_terms


def _snapshot(
    rule_snapshot_id: str,
    raw_rule_text: str,
    *,
    settlement_authority: str = "Prediction Desk Research",
) -> MarketRuleSnapshot:
    return MarketRuleSnapshot.from_rule_text(
        rule_snapshot_id=rule_snapshot_id,
        market_id="mkt_rule_diff",
        captured_at=datetime(2026, 6, 16, tzinfo=UTC),
        raw_rule_text=raw_rule_text,
        resolution_source="Source",
        settlement_authority=settlement_authority,
        time_zone="ET",
    )
