"""Service layer for resolution corpus analysis and persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prediction_desk.resolution.ambiguity import assess_rule_ambiguity
from prediction_desk.resolution.diff import diff_rule_snapshots
from prediction_desk.resolution.models import ResolutionAnalysis, RuleSnapshotDiff
from prediction_desk.resolution.parser import parse_resolution_predicate

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


class ResolutionCorpusError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ResolutionCorpusService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def analyze_rule_snapshot(
        self,
        market_id: str,
        rule_snapshot_id: str | None = None,
        *,
        force: bool = False,
    ) -> ResolutionAnalysis:
        market = self.repo.get_market(market_id)
        if market is None:
            raise ResolutionCorpusError("market_not_found")

        rule_snapshot = (
            self.repo.get_rule_snapshot(rule_snapshot_id)
            if rule_snapshot_id
            else self.repo.get_latest_rule_snapshot(market_id)
        )
        if rule_snapshot is None or rule_snapshot.market_id != market_id:
            raise ResolutionCorpusError("rule_snapshot_not_found")

        existing_predicate = self.repo.get_resolution_predicate_for_rule_snapshot(
            rule_snapshot.rule_snapshot_id
        )
        existing_assessment = self.repo.get_ambiguity_assessment_for_rule_snapshot(
            rule_snapshot.rule_snapshot_id
        )
        if existing_predicate is not None and existing_assessment is not None and not force:
            return ResolutionAnalysis(
                market=market,
                rule_snapshot=rule_snapshot,
                predicate=existing_predicate,
                ambiguity_assessment=existing_assessment,
            )

        predicate = parse_resolution_predicate(
            market=market,
            rule_snapshot=rule_snapshot,
            known_sources=self.repo.list_resolution_sources(),
        )
        assessment = assess_rule_ambiguity(market, rule_snapshot, predicate)
        self.repo.save_resolution_predicate(predicate)
        self.repo.save_ambiguity_assessment(assessment)
        return ResolutionAnalysis(
            market=market,
            rule_snapshot=rule_snapshot,
            predicate=predicate,
            ambiguity_assessment=assessment,
        )

    def analyze_latest_rule_snapshot(
        self, market_id: str, *, force: bool = False
    ) -> ResolutionAnalysis:
        return self.analyze_rule_snapshot(market_id, force=force)

    def get_latest_resolution_analysis(self, market_id: str) -> ResolutionAnalysis:
        market = self.repo.get_market(market_id)
        if market is None:
            raise ResolutionCorpusError("market_not_found")
        predicate = self.repo.get_latest_resolution_predicate(market_id)
        if predicate is None:
            raise ResolutionCorpusError("resolution_analysis_not_found")
        rule_snapshot = self.repo.get_rule_snapshot(predicate.rule_snapshot_id)
        assessment = self.repo.get_ambiguity_assessment_for_rule_snapshot(
            predicate.rule_snapshot_id
        )
        if rule_snapshot is None or assessment is None:
            raise ResolutionCorpusError("resolution_analysis_not_found")
        return ResolutionAnalysis(
            market=market,
            rule_snapshot=rule_snapshot,
            predicate=predicate,
            ambiguity_assessment=assessment,
        )

    def get_resolution_analysis_for_rule_snapshot(
        self, rule_snapshot_id: str
    ) -> ResolutionAnalysis:
        rule_snapshot = self.repo.get_rule_snapshot(rule_snapshot_id)
        if rule_snapshot is None:
            raise ResolutionCorpusError("rule_snapshot_not_found")
        market = self.repo.get_market(rule_snapshot.market_id)
        if market is None:
            raise ResolutionCorpusError("market_not_found")
        predicate = self.repo.get_resolution_predicate_for_rule_snapshot(rule_snapshot_id)
        assessment = self.repo.get_ambiguity_assessment_for_rule_snapshot(rule_snapshot_id)
        if predicate is None or assessment is None:
            raise ResolutionCorpusError("resolution_analysis_not_found")
        return ResolutionAnalysis(
            market=market,
            rule_snapshot=rule_snapshot,
            predicate=predicate,
            ambiguity_assessment=assessment,
        )

    def diff_latest_two_rule_snapshots(
        self, market_id: str, *, force: bool = False
    ) -> RuleSnapshotDiff:
        market = self.repo.get_market(market_id)
        if market is None:
            raise ResolutionCorpusError("market_not_found")
        snapshots = self.repo.get_latest_rule_snapshots(market_id, limit=2)
        if len(snapshots) < 2:
            raise ResolutionCorpusError("insufficient_rule_snapshots")
        latest = snapshots[0]
        previous = snapshots[1]
        existing = self.repo.get_rule_snapshot_diff(
            previous.rule_snapshot_id, latest.rule_snapshot_id
        )
        if existing is not None and not force:
            return existing
        diff = diff_rule_snapshots(previous, latest)
        self.repo.save_rule_snapshot_diff(diff)
        return diff
