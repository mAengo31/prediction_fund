"""Service orchestration for read-only venue ingestion."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from prediction_desk.domain.models import Market, MarketRuleSnapshot, OrderBookSnapshot
from prediction_desk.ingestion.adapters.kalshi import KalshiReadOnlyAdapter
from prediction_desk.ingestion.adapters.polymarket import PolymarketReadOnlyAdapter
from prediction_desk.ingestion.enums import (
    IngestionMode,
    IngestionRunStatus,
    IngestionSource,
    VenueEndpointType,
)
from prediction_desk.ingestion.fixtures import default_fixture_root
from prediction_desk.ingestion.models import (
    IngestionError,
    IngestionRun,
    IngestionRunResult,
    NormalizedVenuePayload,
    RawVenuePayload,
)
from prediction_desk.ingestion.normalizers.kalshi import normalize_kalshi_payload
from prediction_desk.ingestion.normalizers.polymarket import normalize_polymarket_payload
from prediction_desk.marketdata.service import MarketDataService, MarketDataServiceError
from prediction_desk.persistence.database import session_scope
from prediction_desk.resolution.service import ResolutionCorpusError, ResolutionCorpusService
from prediction_desk.scoring.trust_verdict import build_trust_verdict

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


class IngestionServiceError(Exception):
    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


def ingest_fixture_payloads(
    *,
    venue_name: str,
    fixture_dir: Path | None = None,
    captured_at: datetime | None = None,
    analyze_rules: bool = True,
    recompute_verdicts: bool = True,
    derive_market_data: bool = True,
    repo: PredictionMarketRepository | None = None,
    database_url: str | None = None,
) -> IngestionRunResult:
    if repo is not None:
        return _ingest_fixture_payloads(
            repo=repo,
            venue_name=venue_name,
            fixture_dir=fixture_dir,
            captured_at=captured_at,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )
    with session_scope(database_url) as session:
        from prediction_desk.persistence.repositories import PredictionMarketRepository

        return _ingest_fixture_payloads(
            repo=PredictionMarketRepository(session),
            venue_name=venue_name,
            fixture_dir=fixture_dir,
            captured_at=captured_at,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )


def ingest_public_market_sample(
    *,
    venue_name: str,
    limit: int = 10,
    allow_network: bool = False,
    analyze_rules: bool = True,
    recompute_verdicts: bool = True,
    derive_market_data: bool = True,
    repo: PredictionMarketRepository | None = None,
    database_url: str | None = None,
) -> IngestionRunResult:
    if not allow_network:
        raise IngestionServiceError(
            "public_network_disabled",
            "Public sample ingestion requires allow_network=true and remains read-only.",
        )
    if repo is not None:
        return _ingest_public_market_sample(
            repo=repo,
            venue_name=venue_name,
            limit=limit,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )
    with session_scope(database_url) as session:
        from prediction_desk.persistence.repositories import PredictionMarketRepository

        return _ingest_public_market_sample(
            repo=PredictionMarketRepository(session),
            venue_name=venue_name,
            limit=limit,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )


class IngestionService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def ingest_fixture_payloads(
        self,
        *,
        venue_name: str,
        fixture_dir: Path | None = None,
        captured_at: datetime | None = None,
        analyze_rules: bool = True,
        recompute_verdicts: bool = True,
        derive_market_data: bool = True,
    ) -> IngestionRunResult:
        return _ingest_fixture_payloads(
            repo=self.repo,
            venue_name=venue_name,
            fixture_dir=fixture_dir,
            captured_at=captured_at,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )

    def ingest_public_market_sample(
        self,
        *,
        venue_name: str,
        limit: int = 10,
        allow_network: bool = False,
        analyze_rules: bool = True,
        recompute_verdicts: bool = True,
        derive_market_data: bool = True,
    ) -> IngestionRunResult:
        return ingest_public_market_sample(
            venue_name=venue_name,
            limit=limit,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
            repo=self.repo,
        )

    def list_runs(
        self,
        *,
        venue_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[IngestionRun]:
        return self.repo.list_ingestion_runs(
            venue_name=venue_name,
            limit=limit,
            offset=offset,
        )

    def get_run(self, ingestion_run_id: str) -> IngestionRun:
        run = self.repo.get_ingestion_run(ingestion_run_id)
        if run is None:
            raise IngestionServiceError("ingestion_run_not_found")
        return run

    def list_errors(self, ingestion_run_id: str) -> list[IngestionError]:
        if self.repo.get_ingestion_run(ingestion_run_id) is None:
            raise IngestionServiceError("ingestion_run_not_found")
        return self.repo.list_ingestion_errors(ingestion_run_id)


def _ingest_fixture_payloads(
    *,
    repo: PredictionMarketRepository,
    venue_name: str,
    fixture_dir: Path | None,
    captured_at: datetime | None,
    analyze_rules: bool,
    recompute_verdicts: bool,
    derive_market_data: bool,
) -> IngestionRunResult:
    adapter = _fixture_adapter(venue_name, fixture_dir)
    payloads = adapter.fixture_payloads(captured_at=captured_at)
    return _ingest_payloads(
        repo=repo,
        venue_id=adapter.venue_id,
        venue_name=adapter.venue_name,
        source=_source(adapter.venue_name),
        mode=IngestionMode.FIXTURE,
        payloads=payloads,
        analyze_rules=analyze_rules,
        recompute_verdicts=recompute_verdicts,
        derive_market_data=derive_market_data,
    )


def _ingest_public_market_sample(
    *,
    repo: PredictionMarketRepository,
    venue_name: str,
    limit: int,
    allow_network: bool,
    analyze_rules: bool,
    recompute_verdicts: bool,
    derive_market_data: bool,
) -> IngestionRunResult:
    adapter = _fixture_adapter(venue_name, fixture_dir=None)
    payloads = adapter.fetch_market_catalog(limit=limit, allow_network=allow_network)
    return _ingest_payloads(
        repo=repo,
        venue_id=adapter.venue_id,
        venue_name=adapter.venue_name,
        source=_source(adapter.venue_name),
        mode=IngestionMode.MANUAL_PUBLIC_FETCH,
        payloads=payloads,
        analyze_rules=analyze_rules,
        recompute_verdicts=recompute_verdicts,
        derive_market_data=derive_market_data,
    )


def _ingest_payloads(
    *,
    repo: PredictionMarketRepository,
    venue_id: str,
    venue_name: str,
    source: IngestionSource,
    mode: IngestionMode,
    payloads: list[RawVenuePayload],
    analyze_rules: bool,
    recompute_verdicts: bool,
    derive_market_data: bool,
) -> IngestionRunResult:
    started_at = datetime.now(tz=UTC)
    run = IngestionRun(
        ingestion_run_id=f"ingestion_run_{uuid4().hex[:24]}",
        venue_id=venue_id,
        venue_name=venue_name,
        started_at=started_at,
        completed_at=None,
        status=IngestionRunStatus.RUNNING,
        mode=mode,
        source=source,
        endpoint_types=sorted({payload.endpoint_type.value for payload in payloads}),
        metadata={"payload_count": len(payloads), "service_version": "ingestion_v1"},
    )
    repo.save_ingestion_run(run)
    errors: list[IngestionError] = []
    seen_markets: set[str] = set()

    for payload in payloads:
        try:
            repo.save_raw_venue_payload(payload)
            run.payloads_archived += 1
            normalized_items = _normalize_payload(payload)
            normalized_price_history = False
            for normalized in normalized_items:
                if normalized.price_snapshots:
                    normalized_price_history = True
                _upsert_normalized(
                    repo=repo,
                    run=run,
                    normalized=normalized,
                    analyze_rules=analyze_rules,
                    recompute_verdicts=recompute_verdicts,
                    derive_market_data=derive_market_data,
                )
                if normalized.market is not None:
                    seen_markets.add(normalized.market.market_id)
                elif normalized.orderbook_snapshot is not None:
                    seen_markets.add(normalized.orderbook_snapshot.market_id)
            if (
                derive_market_data
                and payload.endpoint_type == VenueEndpointType.PRICE_HISTORY
                and not normalized_price_history
            ):
                _normalize_price_history(repo, run, payload.payload_id)
        except Exception as exc:
            error = _record_error(repo, run, payload, "payload_ingestion_failed", exc)
            errors.append(error)
            run.errors_count += 1

    run.markets_seen = len(seen_markets)
    run.completed_at = datetime.now(tz=UTC)
    run.status = (
        IngestionRunStatus.COMPLETED
        if run.errors_count == 0
        else IngestionRunStatus.PARTIAL
    )
    repo.update_ingestion_run(run)
    return IngestionRunResult(run=run, errors=errors)


def _upsert_normalized(
    *,
    repo: PredictionMarketRepository,
    run: IngestionRun,
    normalized: NormalizedVenuePayload,
    analyze_rules: bool,
    recompute_verdicts: bool,
    derive_market_data: bool,
) -> None:
    if normalized.venue is not None:
        repo.upsert_venue(normalized.venue)
    if normalized.event is not None:
        repo.upsert_event(normalized.event)
    market = normalized.market
    if market is not None:
        if repo.get_market(market.market_id) is None:
            run.markets_created += 1
        else:
            run.markets_updated += 1
        repo.upsert_market(market)
    for outcome in normalized.outcomes:
        repo.upsert_outcome(outcome)
    if normalized.mapping is not None:
        repo.upsert_venue_market_mapping(normalized.mapping)

    rule_snapshot = _save_rule_snapshot_if_changed(repo, normalized.rule_snapshot)
    if rule_snapshot is not None:
        run.rule_snapshots_created += 1

    orderbook_snapshot = normalized.orderbook_snapshot
    if orderbook_snapshot is not None and repo.get_market(orderbook_snapshot.market_id) is not None:
        if repo.get_orderbook_snapshot(orderbook_snapshot.snapshot_id) is None:
            run.orderbook_snapshots_created += 1
        repo.save_orderbook_snapshot(orderbook_snapshot)
        if derive_market_data:
            _derive_orderbook_market_data(repo, run, orderbook_snapshot.snapshot_id)

    for price_snapshot in normalized.price_snapshots:
        if repo.find_price_snapshot_by_hash(price_snapshot.data_hash) is None:
            repo.save_market_price_snapshot(price_snapshot)
            run.price_snapshots_created += 1

    target_market_id = _target_market_id(market, rule_snapshot, orderbook_snapshot)
    if target_market_id is None:
        return
    if analyze_rules:
        _analyze_latest(repo, target_market_id)
    if recompute_verdicts:
        _recompute_verdict(repo, target_market_id, _asof(rule_snapshot, orderbook_snapshot))


def _derive_orderbook_market_data(
    repo: PredictionMarketRepository, run: IngestionRun, orderbook_snapshot_id: str
) -> None:
    try:
        result = MarketDataService(repo).derive_market_data_for_orderbook(orderbook_snapshot_id)
    except MarketDataServiceError:
        return
    run.price_snapshots_created += result.price_snapshots_created
    run.liquidity_snapshots_created += result.liquidity_snapshots_created


def _normalize_price_history(
    repo: PredictionMarketRepository, run: IngestionRun, payload_id: str
) -> None:
    try:
        result = MarketDataService(repo).normalize_price_history_payload(payload_id)
    except MarketDataServiceError:
        return
    run.price_snapshots_created += result.price_snapshots_created


def _save_rule_snapshot_if_changed(
    repo: PredictionMarketRepository, snapshot: MarketRuleSnapshot | None
) -> MarketRuleSnapshot | None:
    if snapshot is None:
        return None
    latest = repo.get_latest_rule_snapshot(snapshot.market_id)
    if latest is not None and latest.rule_hash == snapshot.rule_hash:
        return None
    repo.save_rule_snapshot(snapshot)
    return snapshot


def _analyze_latest(repo: PredictionMarketRepository, market_id: str) -> None:
    try:
        ResolutionCorpusService(repo).analyze_latest_rule_snapshot(market_id)
    except ResolutionCorpusError:
        return


def _recompute_verdict(
    repo: PredictionMarketRepository, market_id: str, asof_timestamp: datetime | None
) -> None:
    market = repo.get_market(market_id)
    if market is None:
        return
    actual_asof_timestamp = asof_timestamp or datetime.now(tz=UTC)
    rule_snapshot = repo.get_latest_rule_snapshot(market_id)
    orderbook_snapshot = repo.get_latest_orderbook_snapshot(market_id)
    ambiguity = (
        repo.get_ambiguity_assessment_for_rule_snapshot(rule_snapshot.rule_snapshot_id)
        if rule_snapshot is not None
        else None
    )
    verdict = build_trust_verdict(
        market=market,
        rule_snapshot=rule_snapshot,
        orderbook_snapshot=orderbook_snapshot,
        asof_timestamp=actual_asof_timestamp,
        ambiguity_assessment=ambiguity,
        integrity_assessment=repo.get_latest_integrity_assessment_asof(
            market_id,
            actual_asof_timestamp,
        ),
    )
    repo.save_trust_verdict(verdict)


def _normalize_payload(payload: RawVenuePayload) -> list[NormalizedVenuePayload]:
    venue = payload.venue_name.lower()
    if venue == "kalshi" or payload.venue_id == "kalshi":
        return normalize_kalshi_payload(payload)
    if venue == "polymarket" or payload.venue_id == "polymarket":
        return normalize_polymarket_payload(payload)
    raise IngestionServiceError("unsupported_venue", f"Unsupported venue: {payload.venue_name}")


def _record_error(
    repo: PredictionMarketRepository,
    run: IngestionRun,
    payload: RawVenuePayload,
    code: str,
    exc: Exception,
) -> IngestionError:
    error = IngestionError(
        error_id=f"ingestion_error_{uuid4().hex[:24]}",
        ingestion_run_id=run.ingestion_run_id,
        venue_id=run.venue_id,
        external_id=payload.external_id,
        endpoint_type=payload.endpoint_type.value,
        occurred_at=datetime.now(tz=UTC),
        error_code=code,
        error_message=str(exc),
        payload_id=payload.payload_id,
        metadata={"exception_type": type(exc).__name__},
    )
    repo.save_ingestion_error(error)
    return error


def _fixture_adapter(
    venue_name: str, fixture_dir: Path | None
) -> KalshiReadOnlyAdapter | PolymarketReadOnlyAdapter:
    normalized = venue_name.lower()
    if normalized == "kalshi":
        return KalshiReadOnlyAdapter(fixture_dir or default_fixture_root() / "kalshi")
    if normalized == "polymarket":
        return PolymarketReadOnlyAdapter(fixture_dir or default_fixture_root() / "polymarket")
    raise IngestionServiceError("unsupported_venue", f"Unsupported venue: {venue_name}")


def _source(venue_name: str) -> IngestionSource:
    normalized = venue_name.lower()
    if normalized == "kalshi":
        return IngestionSource.KALSHI
    if normalized == "polymarket":
        return IngestionSource.POLYMARKET
    return IngestionSource.OTHER


def _target_market_id(
    market: Market | None,
    rule_snapshot: MarketRuleSnapshot | None,
    orderbook_snapshot: OrderBookSnapshot | None,
) -> str | None:
    if market is not None:
        return market.market_id
    if rule_snapshot is not None:
        return rule_snapshot.market_id
    if orderbook_snapshot is not None:
        return orderbook_snapshot.market_id
    return None


def _asof(
    rule_snapshot: MarketRuleSnapshot | None, orderbook_snapshot: OrderBookSnapshot | None
) -> datetime | None:
    candidates = [
        value
        for value in [
            rule_snapshot.captured_at if rule_snapshot is not None else None,
            orderbook_snapshot.captured_at if orderbook_snapshot is not None else None,
        ]
        if value is not None
    ]
    return max(candidates) if candidates else None
