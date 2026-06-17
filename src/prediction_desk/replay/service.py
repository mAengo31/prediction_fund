"""Service layer for point-in-time replay."""

from __future__ import annotations

from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.replay.models import (
    ReplayRun,
    ReplayRunConfig,
    ReplayRunResult,
    ReplayRunSummary,
    ReplayStep,
)
from prediction_desk.replay.runner import ReplayError, run_replay


class ReplayService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def run(self, config: ReplayRunConfig) -> ReplayRunResult:
        return run_replay(config, self.repo)

    def get_run(self, run_id: str) -> ReplayRun:
        run = self.repo.get_replay_run(run_id)
        if run is None:
            raise ReplayError("replay_run_not_found")
        return run

    def list_steps(self, run_id: str, *, limit: int = 500, offset: int = 0) -> list[ReplayStep]:
        if self.repo.get_replay_run(run_id) is None:
            raise ReplayError("replay_run_not_found")
        return self.repo.list_replay_steps(run_id, limit=limit, offset=offset)

    def get_summary(self, run_id: str) -> ReplayRunSummary:
        if self.repo.get_replay_run(run_id) is None:
            raise ReplayError("replay_run_not_found")
        summary = self.repo.get_replay_summary(run_id)
        if summary is None:
            raise ReplayError("replay_summary_not_found")
        return summary
