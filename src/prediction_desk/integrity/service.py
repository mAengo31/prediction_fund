"""Service orchestration for fast-lane integrity analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from prediction_desk.integrity.aggregation import aggregate_integrity_signals
from prediction_desk.integrity.features import build_market_feature_snapshot
from prediction_desk.integrity.models import (
    IntegrityAnalysis,
    IntegrityAssessment,
    IntegritySignal,
)
from prediction_desk.integrity.signals import generate_integrity_signals

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


class IntegrityServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class IntegrityService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def analyze_market_integrity_details(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        config: dict[str, Any] | None = None,
        force: bool = False,
    ) -> IntegrityAnalysis:
        if self.repo.get_market(market_id) is None:
            raise IntegrityServiceError("market_not_found")
        config = dict(config or {})
        feature = build_market_feature_snapshot(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            lookback_seconds=int(config.get("lookback_seconds", 3600)),
            freshness_threshold_seconds=int(config.get("freshness_threshold_seconds", 3600)),
            repo=self.repo,
        )
        persisted_feature = self.repo.find_feature_snapshot_by_hash(feature.input_hash)
        if persisted_feature is not None and not force:
            feature = persisted_feature
        else:
            self.repo.save_market_feature_snapshot(feature)

        signals = generate_integrity_signals(feature, config)
        persisted_signals: list[IntegritySignal] = []
        for signal in signals:
            existing_signal = self.repo.find_integrity_signal_by_hash(signal.output_hash)
            if existing_signal is not None and not force:
                persisted_signals.append(existing_signal)
                continue
            persisted_signals.append(self.repo.save_integrity_signal(signal))

        assessment = aggregate_integrity_signals(feature, persisted_signals)
        existing_assessment = self.repo.find_integrity_assessment_by_hash(
            assessment.output_hash
        )
        if existing_assessment is not None and not force:
            assessment = existing_assessment
        else:
            assessment = self.repo.save_integrity_assessment(assessment)
        return IntegrityAnalysis(
            feature_snapshot=feature,
            signals=persisted_signals,
            assessment=assessment,
        )

    def analyze_market_integrity(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        config: dict[str, Any] | None = None,
        force: bool = False,
    ) -> IntegrityAssessment:
        return self.analyze_market_integrity_details(
            market_id,
            asof_timestamp,
            config=config,
            force=force,
        ).assessment

    def analyze_integrity_for_all_markets(
        self,
        asof_timestamp: datetime,
        *,
        market_ids: list[str] | None = None,
        limit: int | None = None,
        force: bool = False,
        config: dict[str, Any] | None = None,
    ) -> list[IntegrityAssessment]:
        markets = (
            [self.repo.get_market(market_id) for market_id in market_ids]
            if market_ids
            else self.repo.list_markets(limit=limit or 100)
        )
        assessments: list[IntegrityAssessment] = []
        for market in markets:
            if market is None:
                continue
            assessments.append(
                self.analyze_market_integrity(
                    market.market_id,
                    asof_timestamp,
                    config=config,
                    force=force,
                )
            )
        return assessments

    def get_latest_integrity_assessment(
        self,
        market_id: str,
        asof_timestamp: datetime | None = None,
    ) -> IntegrityAssessment:
        if self.repo.get_market(market_id) is None:
            raise IntegrityServiceError("market_not_found")
        assessment = self.repo.get_latest_integrity_assessment_asof(
            market_id,
            asof_timestamp or datetime.now(tz=UTC),
        )
        if assessment is None:
            raise IntegrityServiceError("integrity_assessment_not_found")
        return assessment

    def list_integrity_signals(
        self,
        *,
        market_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[IntegritySignal]:
        return self.repo.list_integrity_signals(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def list_integrity_assessments(
        self,
        *,
        market_id: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[IntegrityAssessment]:
        return self.repo.list_integrity_assessments(
            market_id=market_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
