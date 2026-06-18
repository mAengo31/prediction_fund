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
    VenueOutcomeTokenStatus,
)
from prediction_desk.ingestion.fixtures import default_fixture_root
from prediction_desk.ingestion.models import (
    IngestionError,
    IngestionRun,
    IngestionRunResult,
    NormalizedVenuePayload,
    RawVenuePayload,
    VenueMarketMapping,
    VenueOutcomeTokenMapping,
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


def ingest_public_endpoint_payloads(
    *,
    venue_name: str,
    endpoint_types: list[str] | None = None,
    market_ids: list[str] | None = None,
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
            "Targeted public ingestion requires allow_network=true and remains read-only.",
        )
    if repo is not None:
        return _ingest_public_endpoint_payloads(
            repo=repo,
            venue_name=venue_name,
            endpoint_types=endpoint_types,
            market_ids=market_ids,
            limit=limit,
            allow_network=allow_network,
            analyze_rules=analyze_rules,
            recompute_verdicts=recompute_verdicts,
            derive_market_data=derive_market_data,
        )
    with session_scope(database_url) as session:
        from prediction_desk.persistence.repositories import PredictionMarketRepository

        return _ingest_public_endpoint_payloads(
            repo=PredictionMarketRepository(session),
            venue_name=venue_name,
            endpoint_types=endpoint_types,
            market_ids=market_ids,
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

    def ingest_public_endpoint_payloads(
        self,
        *,
        venue_name: str,
        endpoint_types: list[str] | None = None,
        market_ids: list[str] | None = None,
        limit: int = 10,
        allow_network: bool = False,
        analyze_rules: bool = True,
        recompute_verdicts: bool = True,
        derive_market_data: bool = True,
    ) -> IngestionRunResult:
        return ingest_public_endpoint_payloads(
            venue_name=venue_name,
            endpoint_types=endpoint_types,
            market_ids=market_ids,
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
    return _ingest_public_endpoint_payloads(
        repo=repo,
        venue_name=venue_name,
        endpoint_types=[VenueEndpointType.MARKET_LIST.value],
        market_ids=None,
        limit=limit,
        allow_network=allow_network,
        analyze_rules=analyze_rules,
        recompute_verdicts=recompute_verdicts,
        derive_market_data=derive_market_data,
    )


def _ingest_public_endpoint_payloads(
    *,
    repo: PredictionMarketRepository,
    venue_name: str,
    endpoint_types: list[str] | None,
    market_ids: list[str] | None,
    limit: int,
    allow_network: bool,
    analyze_rules: bool,
    recompute_verdicts: bool,
    derive_market_data: bool,
) -> IngestionRunResult:
    adapter = _fixture_adapter(venue_name, fixture_dir=None)
    payloads, pre_errors = _collect_public_payloads(
        repo=repo,
        adapter=adapter,
        endpoint_types=endpoint_types,
        market_ids=market_ids,
        limit=limit,
        allow_network=allow_network,
    )
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
        pre_errors=pre_errors,
    )


def _collect_public_payloads(
    *,
    repo: PredictionMarketRepository,
    adapter: KalshiReadOnlyAdapter | PolymarketReadOnlyAdapter,
    endpoint_types: list[str] | None,
    market_ids: list[str] | None,
    limit: int,
    allow_network: bool,
) -> tuple[list[RawVenuePayload], list[dict[str, str | None]]]:
    requested_endpoint_types = _public_endpoint_types(endpoint_types)
    payloads: list[RawVenuePayload] = []
    errors: list[dict[str, str | None]] = []
    remaining = max(0, limit)
    mappings_cache: list[VenueMarketMapping] | None = None

    for endpoint_type in requested_endpoint_types:
        if remaining <= 0:
            break
        if endpoint_type == VenueEndpointType.MARKET_LIST:
            try:
                fetched = adapter.fetch_market_catalog(
                    limit=remaining,
                    allow_network=allow_network,
                )
            except Exception as exc:
                errors.append(
                    _fetch_error(
                        code="public_fetch_failed",
                        endpoint_type=endpoint_type,
                        external_id=None,
                        exc=exc,
                    )
                )
                continue
            payloads.extend(fetched[:remaining])
            remaining -= min(len(fetched), remaining)
            continue

        if not _targeted_endpoint_supported(adapter, endpoint_type):
            errors.append(
                {
                    "code": "unsupported_public_endpoint",
                    "endpoint_type": endpoint_type.value,
                    "external_id": None,
                    "message": (
                        f"{adapter.venue_name} targeted {endpoint_type.value} "
                        "is not supported by the current read-only normalizer path."
                    ),
                }
            )
            continue

        if mappings_cache is None:
            mappings_cache = _target_mappings(
                repo=repo,
                venue_name=adapter.venue_name,
                market_ids=market_ids,
                limit=limit,
            )
        if not mappings_cache:
            errors.append(
                {
                    "code": "missing_venue_mapping",
                    "endpoint_type": endpoint_type.value,
                    "external_id": None,
                    "message": (
                        f"No existing {adapter.venue_name} venue mappings were available "
                        "for targeted public follow-up."
                    ),
                }
            )
            continue

        if isinstance(adapter, PolymarketReadOnlyAdapter):
            fetched, endpoint_errors = _collect_polymarket_targeted_payloads(
                repo=repo,
                adapter=adapter,
                endpoint_type=endpoint_type,
                mappings=mappings_cache,
                remaining=remaining,
                allow_network=allow_network,
            )
            payloads.extend(fetched)
            errors.extend(endpoint_errors)
            remaining -= min(len(fetched), remaining)
            continue

        for mapping in mappings_cache:
            if remaining <= 0:
                break
            try:
                payloads.append(
                    _fetch_targeted_payload(
                        adapter=adapter,
                        endpoint_type=endpoint_type,
                        external_market_id=mapping.external_market_id,
                        allow_network=allow_network,
                    )
                )
                remaining -= 1
            except Exception as exc:
                errors.append(
                    _fetch_error(
                        code="public_fetch_failed",
                        endpoint_type=endpoint_type,
                        external_id=mapping.external_market_id,
                        exc=exc,
                    )
                )
    return payloads, errors


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
    pre_errors: list[dict[str, str | None]] | None = None,
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

    for pre_error in pre_errors or []:
        error = _record_pre_error(repo, run, pre_error)
        errors.append(error)
        run.errors_count += 1

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


def _public_endpoint_types(endpoint_types: list[str] | None) -> list[VenueEndpointType]:
    if not endpoint_types:
        return [VenueEndpointType.MARKET_LIST]
    allowed = {
        VenueEndpointType.MARKET_LIST,
        VenueEndpointType.MARKET_DETAIL,
        VenueEndpointType.ORDERBOOK,
        VenueEndpointType.PRICE_HISTORY,
    }
    resolved: list[VenueEndpointType] = []
    seen: set[VenueEndpointType] = set()
    for value in endpoint_types:
        try:
            endpoint_type = VenueEndpointType(str(value).upper())
        except ValueError as exc:
            raise IngestionServiceError(
                "unsupported_public_endpoint",
                f"Unsupported public endpoint type: {value}",
            ) from exc
        if endpoint_type not in allowed:
            raise IngestionServiceError(
                "unsupported_public_endpoint",
                f"Unsupported public endpoint type: {endpoint_type.value}",
            )
        if endpoint_type not in seen:
            seen.add(endpoint_type)
            resolved.append(endpoint_type)
    return resolved


def _targeted_endpoint_supported(
    adapter: KalshiReadOnlyAdapter | PolymarketReadOnlyAdapter,
    endpoint_type: VenueEndpointType,
) -> bool:
    if endpoint_type == VenueEndpointType.MARKET_DETAIL:
        return True
    if endpoint_type == VenueEndpointType.ORDERBOOK:
        return adapter.venue_id in {"kalshi", "polymarket"}
    if endpoint_type == VenueEndpointType.PRICE_HISTORY:
        return adapter.venue_id == "polymarket"
    return endpoint_type == VenueEndpointType.MARKET_LIST


def _target_mappings(
    *,
    repo: PredictionMarketRepository,
    venue_name: str,
    market_ids: list[str] | None,
    limit: int,
) -> list[VenueMarketMapping]:
    if market_ids:
        mappings = [
            mapping
            for market_id in sorted(set(market_ids))
            if (mapping := repo.get_mapping_by_canonical_market_id(market_id)) is not None
            and mapping.venue_name.casefold() == venue_name.casefold()
        ]
        return sorted(mappings, key=lambda item: (item.external_market_id, item.mapping_id))
    mappings = repo.list_venue_market_mappings(venue_name=venue_name, limit=max(1, limit))
    return sorted(mappings, key=lambda item: (item.external_market_id, item.mapping_id))


def _fetch_targeted_payload(
    *,
    adapter: KalshiReadOnlyAdapter | PolymarketReadOnlyAdapter,
    endpoint_type: VenueEndpointType,
    external_market_id: str,
    allow_network: bool,
) -> RawVenuePayload:
    if endpoint_type == VenueEndpointType.MARKET_DETAIL:
        return adapter.fetch_market_detail(
            external_market_id,
            allow_network=allow_network,
        )
    if endpoint_type == VenueEndpointType.ORDERBOOK:
        return adapter.fetch_orderbook(
            external_market_id,
            allow_network=allow_network,
        )
    if endpoint_type == VenueEndpointType.PRICE_HISTORY:
        return adapter.fetch_price_history(
            external_market_id,
            allow_network=allow_network,
        )
    raise IngestionServiceError("unsupported_public_endpoint")


def _collect_polymarket_targeted_payloads(
    *,
    repo: PredictionMarketRepository,
    adapter: PolymarketReadOnlyAdapter,
    endpoint_type: VenueEndpointType,
    mappings: list[VenueMarketMapping],
    remaining: int,
    allow_network: bool,
) -> tuple[list[RawVenuePayload], list[dict[str, str | None]]]:
    payloads: list[RawVenuePayload] = []
    errors: list[dict[str, str | None]] = []
    for mapping in mappings:
        if remaining <= 0:
            break
        if endpoint_type == VenueEndpointType.MARKET_DETAIL:
            identifier = _polymarket_gamma_identifier(mapping)
            if identifier is None:
                errors.append(
                    _pre_error(
                        code="POLYMARKET_MISSING_GAMMA_MARKET_ID",
                        endpoint_type=endpoint_type,
                        external_id=mapping.external_market_id,
                        message=(
                            "Polymarket market detail follow-up requires a Gamma market "
                            "identifier from prior catalog/detail ingestion."
                        ),
                    )
                )
                continue
            try:
                payload = adapter.fetch_market_detail_by_gamma_id(
                    identifier,
                    allow_network=allow_network,
                )
            except Exception as exc:
                errors.append(
                    _fetch_error(
                        code="public_fetch_failed",
                        endpoint_type=endpoint_type,
                        external_id=identifier,
                        exc=exc,
                    )
                )
                continue
            payloads.append(_with_polymarket_mapping_metadata(payload, mapping, None))
            remaining -= 1
            continue

        token_mappings = repo.list_venue_outcome_token_mappings(
            venue_name=mapping.venue_name,
            canonical_market_id=mapping.canonical_market_id,
            status=VenueOutcomeTokenStatus.ACTIVE,
            limit=20,
        )
        token_mappings = sorted(
            token_mappings,
            key=lambda item: (
                _polymarket_token_side_order(item.token_side.value),
                item.token_id or item.asset_id or "",
            ),
        )
        if not token_mappings:
            errors.append(
                _pre_error(
                    code="POLYMARKET_MISSING_TOKEN_ID",
                    endpoint_type=endpoint_type,
                    external_id=mapping.external_market_id,
                    message=(
                        "Polymarket CLOB follow-up requires token IDs from prior "
                        "catalog/detail ingestion."
                    ),
                )
            )
            continue

        for token_mapping in token_mappings:
            if remaining <= 0:
                break
            token_id = token_mapping.token_id or token_mapping.asset_id
            if not token_id:
                errors.append(
                    _pre_error(
                        code="POLYMARKET_MISSING_TOKEN_ID",
                        endpoint_type=endpoint_type,
                        external_id=mapping.external_market_id,
                        message="Polymarket token mapping is active but has no token_id/asset_id.",
                    )
                )
                continue
            if (
                endpoint_type == VenueEndpointType.ORDERBOOK
                and token_mapping.enable_orderbook is False
            ):
                errors.append(
                    _pre_error(
                        code="POLYMARKET_ORDERBOOK_DISABLED",
                        endpoint_type=endpoint_type,
                        external_id=token_id,
                        message="Polymarket market reports enableOrderBook=false.",
                    )
                )
                continue
            try:
                if endpoint_type == VenueEndpointType.ORDERBOOK:
                    payload = adapter.fetch_orderbook_by_token_id(
                        token_id,
                        allow_network=allow_network,
                    )
                elif endpoint_type == VenueEndpointType.PRICE_HISTORY:
                    payload = adapter.fetch_price_history_by_token_id(
                        token_id,
                        allow_network=allow_network,
                    )
                else:
                    raise IngestionServiceError("unsupported_public_endpoint")
            except Exception as exc:
                errors.append(
                    _fetch_error(
                        code="public_fetch_failed",
                        endpoint_type=endpoint_type,
                        external_id=token_id,
                        exc=exc,
                    )
                )
                continue
            payloads.append(_with_polymarket_mapping_metadata(payload, mapping, token_mapping))
            remaining -= 1
    return payloads, errors


def _polymarket_gamma_identifier(mapping: VenueMarketMapping) -> str | None:
    metadata = mapping.metadata
    for key in ("gamma_market_id", "gamma_id", "market_id"):
        value = metadata.get(key)
        if value:
            return str(value)
    # Existing pre-token-aware mappings often used the Gamma id as external_market_id.
    external_market_id = mapping.external_market_id
    if external_market_id and not external_market_id.startswith("0x"):
        return external_market_id
    return None


def _polymarket_token_side_order(side: str) -> int:
    return {"YES": 0, "NO": 1}.get(side, 2)


def _with_polymarket_mapping_metadata(
    payload: RawVenuePayload,
    mapping: VenueMarketMapping,
    token_mapping: VenueOutcomeTokenMapping | None,
) -> RawVenuePayload:
    metadata = {
        **payload.metadata,
        "canonical_market_id": mapping.canonical_market_id,
        "canonical_event_id": mapping.canonical_event_id,
        "external_market_id": mapping.external_market_id,
        "condition_id": mapping.metadata.get("condition_id") or mapping.external_symbol,
        "question_id": mapping.metadata.get("question_id"),
        "gamma_market_id": mapping.metadata.get("gamma_market_id"),
        "gamma_event_id": mapping.metadata.get("gamma_event_id"),
        "mapping_id": mapping.mapping_id,
    }
    if token_mapping is not None:
        metadata.update(
            {
                "token_mapping_id": token_mapping.mapping_id,
                "canonical_outcome_id": token_mapping.canonical_outcome_id,
                "outcome_label": token_mapping.outcome_label,
                "token_id": token_mapping.token_id,
                "asset_id": token_mapping.asset_id,
                "token_side": token_mapping.token_side.value,
                "enable_orderbook": token_mapping.enable_orderbook,
            }
        )
    return payload.model_copy(update={"metadata": metadata})


def _pre_error(
    *,
    code: str,
    endpoint_type: VenueEndpointType,
    external_id: str | None,
    message: str,
) -> dict[str, str | None]:
    return {
        "code": code,
        "endpoint_type": endpoint_type.value,
        "external_id": external_id,
        "message": message,
    }


def _fetch_error(
    *,
    code: str,
    endpoint_type: VenueEndpointType,
    external_id: str | None,
    exc: Exception,
) -> dict[str, str | None]:
    return {
        "code": code,
        "endpoint_type": endpoint_type.value,
        "external_id": external_id,
        "message": str(exc),
        "exception_type": type(exc).__name__,
    }


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
    for token_mapping in normalized.outcome_token_mappings:
        repo.upsert_venue_outcome_token_mapping(token_mapping)

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


def _record_pre_error(
    repo: PredictionMarketRepository,
    run: IngestionRun,
    pre_error: dict[str, str | None],
) -> IngestionError:
    error = IngestionError(
        error_id=f"ingestion_error_{uuid4().hex[:24]}",
        ingestion_run_id=run.ingestion_run_id,
        venue_id=run.venue_id,
        external_id=pre_error.get("external_id"),
        endpoint_type=pre_error.get("endpoint_type"),
        occurred_at=datetime.now(tz=UTC),
        error_code=str(pre_error.get("code") or "public_fetch_error"),
        error_message=str(
            pre_error.get("message") or pre_error.get("code") or "public_fetch_error"
        ),
        payload_id=None,
        metadata={
            key: value
            for key, value in pre_error.items()
            if key not in {"code", "message", "external_id", "endpoint_type"}
        },
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
