"""API routes for stored market data and deterministic trust verdicts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import Engine

from prediction_desk.api.auth import require_api_token
from prediction_desk.api.dependencies import get_repository
from prediction_desk.api.schemas import SERVICE_NAME, HealthResponse, MarketSummary, VersionResponse
from prediction_desk.config import Settings
from prediction_desk.domain.enums import MarketStatus
from prediction_desk.domain.models import Market, MarketRuleSnapshot
from prediction_desk.domain.verdicts import TrustVerdict
from prediction_desk.persistence.database import check_database_connection
from prediction_desk.persistence.repositories import PredictionMarketRepository
from prediction_desk.scoring.trust_verdict import build_trust_verdict

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
def healthz(request: Request) -> HealthResponse:
    settings = _settings(request)
    return _health_response(settings)


@router.get(
    "/readyz",
    response_model=HealthResponse,
    dependencies=[Depends(require_api_token)],
)
def readyz(request: Request) -> HealthResponse:
    engine = cast(Engine, request.app.state.engine)
    if not check_database_connection(engine):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database_unreachable",
        )
    return _health_response(_settings(request))


@router.get(
    "/version",
    response_model=VersionResponse,
    dependencies=[Depends(require_api_token)],
)
def version(request: Request) -> VersionResponse:
    settings = _settings(request)
    return VersionResponse(
        service=SERVICE_NAME,
        version=settings.app_version,
        commit=settings.git_commit,
        environment=settings.app_env,
    )


@router.get(
    "/markets",
    response_model=list[MarketSummary],
    dependencies=[Depends(require_api_token)],
)
def list_markets(
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
    status_filter: Annotated[MarketStatus | None, Query(alias="status")] = None,
    venue_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[MarketSummary]:
    markets = repo.list_markets(
        status=status_filter,
        venue_id=venue_id,
        limit=limit,
        offset=offset,
    )
    return [MarketSummary.from_market(market) for market in markets]


@router.get(
    "/markets/{market_id}",
    response_model=Market,
    dependencies=[Depends(require_api_token)],
)
def get_market(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> Market:
    return _market_or_404(repo, market_id)


@router.get(
    "/markets/{market_id}/rule-snapshots/latest",
    response_model=MarketRuleSnapshot,
    dependencies=[Depends(require_api_token)],
)
def get_latest_rule_snapshot(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> MarketRuleSnapshot:
    _market_or_404(repo, market_id)
    snapshot = repo.get_latest_rule_snapshot(market_id)
    if snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="rule_snapshot_not_found")
    return snapshot


@router.get(
    "/markets/{market_id}/trust-verdicts/latest",
    response_model=TrustVerdict,
    dependencies=[Depends(require_api_token)],
)
def get_latest_trust_verdict(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> TrustVerdict:
    _market_or_404(repo, market_id)
    verdict = repo.get_latest_trust_verdict(market_id)
    if verdict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="trust_verdict_not_found")
    return verdict


@router.post(
    "/markets/{market_id}/trust-verdicts/recompute",
    response_model=TrustVerdict,
    dependencies=[Depends(require_api_token)],
)
def recompute_trust_verdict(
    market_id: str,
    repo: Annotated[PredictionMarketRepository, Depends(get_repository)],
) -> TrustVerdict:
    market = _market_or_404(repo, market_id)
    verdict = build_trust_verdict(
        market=market,
        rule_snapshot=repo.get_latest_rule_snapshot(market_id),
        orderbook_snapshot=repo.get_latest_orderbook_snapshot(market_id),
        asof_timestamp=datetime.now(tz=UTC),
    )
    return repo.save_trust_verdict(verdict)


def _settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def _health_response(settings: Settings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=settings.app_version,
        environment=settings.app_env,
    )


def _market_or_404(repo: PredictionMarketRepository, market_id: str) -> Market:
    market = repo.get_market(market_id)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    return market
