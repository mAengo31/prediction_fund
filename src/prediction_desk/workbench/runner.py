"""Synchronous workbench build runner."""

from __future__ import annotations

from prediction_desk.persistence.database import session_scope
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.workbench.models import WorkbenchRunConfig, WorkbenchRunResult
from prediction_desk.workbench.service import WorkbenchService, WorkbenchServiceError


class WorkbenchRunError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def run_workbench_build(
    config: WorkbenchRunConfig,
    *,
    repo: PredictionMarketRepository | None = None,
) -> WorkbenchRunResult:
    if repo is not None:
        return _run(config, repo)
    with session_scope() as session:
        return _run(config, PredictionMarketRepository(session))


def _run(
    config: WorkbenchRunConfig,
    repo: PredictionMarketRepository,
) -> WorkbenchRunResult:
    try:
        return WorkbenchService(repo).run_workbench(config)
    except WorkbenchServiceError as exc:
        raise WorkbenchRunError(exc.code, exc.message) from exc

