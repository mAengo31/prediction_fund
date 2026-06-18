from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from prediction_desk.dataops.orchestrator import DataOpsCollectionError, run_collection_once
from prediction_desk.dataops.plans import create_default_collection_plans_if_missing
from prediction_desk.domain.enums import MarketStatus, MarketType, VenueType
from prediction_desk.domain.models import Event, Market, Outcome, Venue
from prediction_desk.ingestion.adapters.kalshi import KalshiReadOnlyAdapter
from prediction_desk.ingestion.adapters.polymarket import PolymarketReadOnlyAdapter
from prediction_desk.ingestion.enums import (
    VenueMappingStatus,
    VenueOutcomeTokenSide,
    VenueOutcomeTokenStatus,
)
from prediction_desk.ingestion.models import (
    RawVenuePayload,
    VenueMarketMapping,
    VenueOutcomeTokenMapping,
)
from prediction_desk.persistence.database import build_engine, build_session_factory, init_db
from prediction_desk.persistence.repositories import PredictionMarketRepository


def test_collection_run_fixture_mode_uses_no_network(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_collection.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        plan = create_default_collection_plans_if_missing(repo=repo)[0]
        result = run_collection_once(
            plan_id=plan.collection_plan_id,
            venue_names=["kalshi"],
            mode="FIXTURE",
            allow_network=False,
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.allow_network is False
    assert result.run.payloads_archived >= 1
    assert result.run.price_snapshots_created >= 1


def test_manual_public_fetch_without_allow_network_fails_safely(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'dataops_collection_no_network.db'}"
    init_db(database_url)
    engine = build_engine(database_url)
    factory = build_session_factory(engine)
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        with pytest.raises(DataOpsCollectionError) as exc:
            run_collection_once(
                venue_names=["kalshi"],
                mode="MANUAL_PUBLIC_FETCH",
                allow_network=False,
                repo=repo,
            )

    assert exc.value.code == "public_network_disabled"


def test_manual_public_fetch_market_list_routes_with_no_external_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_kalshi_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_public_market_list.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        result = run_collection_once(
            venue_names=["kalshi"],
            endpoint_types=["MARKET_LIST"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=1,
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.endpoint_types == ["MARKET_LIST"]
    assert result.run.payloads_archived == 1
    assert result.run.markets_processed == 1


def test_manual_public_fetch_targeted_detail_and_orderbook_use_existing_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_kalshi_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_public_targeted.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_kalshi_mapping(repo)
        result = run_collection_once(
            venue_names=["kalshi"],
            market_ids=["kalshi_market_kxweather_nyc_rain_20260930"],
            endpoint_types=["MARKET_DETAIL", "ORDERBOOK"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )
        orderbooks = repo.list_orderbook_snapshots(
            "kalshi_market_kxweather_nyc_rain_20260930"
        )
        prices = repo.list_price_snapshots("kalshi_market_kxweather_nyc_rain_20260930")
        liquidity = repo.list_liquidity_snapshots(
            "kalshi_market_kxweather_nyc_rain_20260930"
        )
        mapping = repo.get_mapping_by_canonical_market_id(
            "kalshi_market_kxweather_nyc_rain_20260930"
        )
        rule_snapshot = repo.get_latest_rule_snapshot(
            "kalshi_market_kxweather_nyc_rain_20260930"
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 2
    assert result.run.markets_processed == 1
    assert result.run.price_snapshots_created == 1
    assert result.run.liquidity_snapshots_created == 1
    assert result.run.quality_reports_created >= 1
    assert rule_snapshot is not None
    assert mapping is not None
    assert mapping.canonical_event_id == "kalshi_event_kxweather_nyc_rain"
    assert orderbooks
    assert prices
    assert liquidity
    assert calls == [
        ("detail", "KXWEATHER-NYC-RAIN-20260930"),
        ("orderbook", "KXWEATHER-NYC-RAIN-20260930"),
    ]


def test_manual_public_fetch_enforces_max_payloads_across_endpoint_types(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_kalshi_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_public_max_payloads.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_kalshi_mapping(repo)
        result = run_collection_once(
            venue_names=["kalshi"],
            market_ids=["kalshi_market_kxweather_nyc_rain_20260930"],
            endpoint_types=["MARKET_DETAIL", "ORDERBOOK"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=1,
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 1
    assert calls == [("detail", "KXWEATHER-NYC-RAIN-20260930")]


def test_manual_public_fetch_unsupported_endpoint_records_safe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_kalshi_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_public_unsupported.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_kalshi_mapping(repo)
        result = run_collection_once(
            venue_names=["kalshi"],
            market_ids=["kalshi_market_kxweather_nyc_rain_20260930"],
            endpoint_types=["PRICE_HISTORY"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )
        ingestion_run = repo.list_ingestion_runs(venue_name="Kalshi", limit=1)[0]
        ingestion_errors = repo.list_ingestion_errors(ingestion_run.ingestion_run_id)

    assert result.run.status.value == "PARTIAL"
    assert result.run.payloads_archived == 0
    assert result.run.errors_count == 1
    assert result.run.metadata["errors"][0]["code"] == "unsupported_public_endpoint"
    assert ingestion_errors[0].error_code == "unsupported_public_endpoint"


def test_polymarket_manual_public_detail_resolves_gamma_id_from_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_detail.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["MARKET_DETAIL"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )
        mappings = repo.list_venue_outcome_token_mappings(
            venue_name="Polymarket",
            canonical_market_id="polymarket_market_0xabc123nyctemp",
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 1
    assert calls == [("detail", "pm-nyc-temp-20260704")]
    assert len(mappings) == 2
    assert mappings[0].gamma_market_id == "pm-nyc-temp-20260704"


def test_polymarket_manual_public_detail_resolves_gamma_id_from_token_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_detail_token_gamma.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo, drop_mapping_gamma_id=True)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["MARKET_DETAIL"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 1
    assert calls == [("detail", "pm-nyc-temp-20260704")]


def test_polymarket_manual_public_detail_missing_gamma_id_records_safe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_missing_gamma.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo, gamma_market_id=None)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["MARKET_DETAIL"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )

    assert result.run.status.value == "PARTIAL"
    assert result.run.payloads_archived == 0
    assert result.run.metadata["errors"][0]["code"] == "POLYMARKET_MISSING_GAMMA_MARKET_ID"


def test_polymarket_manual_public_orderbook_resolves_token_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_orderbook.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["ORDERBOOK"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )
        orderbooks = repo.list_orderbook_snapshots("polymarket_market_0xabc123nyctemp")
        prices = repo.list_price_snapshots("polymarket_market_0xabc123nyctemp")
        liquidity = repo.list_liquidity_snapshots("polymarket_market_0xabc123nyctemp")

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 2
    assert result.run.price_snapshots_created == 2
    assert result.run.liquidity_snapshots_created == 2
    assert [call[0] for call in calls] == ["orderbook", "orderbook"]
    assert calls[0][1].startswith("111111")
    assert calls[1][1].startswith("222222")
    assert len(orderbooks) == 2
    assert prices
    assert liquidity


def test_polymarket_manual_public_orderbook_missing_token_records_safe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_missing_token.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo, save_tokens=False)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["ORDERBOOK"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )

    assert result.run.status.value == "PARTIAL"
    assert result.run.payloads_archived == 0
    assert result.run.metadata["errors"][0]["code"] == "POLYMARKET_MISSING_TOKEN_ID"


def test_polymarket_manual_public_orderbook_disabled_records_safe_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_orderbook_disabled.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo, enable_orderbook=False)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["ORDERBOOK"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )

    assert result.run.status.value == "PARTIAL"
    assert result.run.payloads_archived == 0
    assert {error["code"] for error in result.run.metadata["errors"]} == {
        "POLYMARKET_ORDERBOOK_DISABLED"
    }


def test_polymarket_manual_public_price_history_resolves_token_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_price_history.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo, only_yes_token=True)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["PRICE_HISTORY"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=5,
            repo=repo,
        )
        prices = repo.list_price_snapshots("polymarket_market_0xabc123nyctemp")
        mapping = repo.get_mapping_by_canonical_market_id(
            "polymarket_market_0xabc123nyctemp"
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 1
    assert result.run.price_snapshots_created == 1
    assert calls == [
        ("price_history", "1111111111111111111111111111111111111111111111111111111111111111")
    ]
    assert prices[0].external_outcome_id.startswith("111111")
    assert mapping is not None
    assert mapping.metadata["gamma_market_id"] == "pm-nyc-temp-20260704"
    assert mapping.metadata["source"] == "polymarket_price_history"


def test_polymarket_manual_public_max_payloads_enforced_across_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_polymarket_public_fetches(monkeypatch)
    factory = _factory(tmp_path, "dataops_polymarket_max_payloads.db")
    with factory.begin() as session:
        repo = PredictionMarketRepository(session)
        _save_polymarket_market_mapping_and_tokens(repo)
        result = run_collection_once(
            venue_names=["polymarket"],
            market_ids=["polymarket_market_0xabc123nyctemp"],
            endpoint_types=["ORDERBOOK"],
            mode="MANUAL_PUBLIC_FETCH",
            allow_network=True,
            max_payloads=1,
            repo=repo,
        )

    assert result.run.status.value == "COMPLETED"
    assert result.run.payloads_archived == 1
    assert calls == [
        ("orderbook", "1111111111111111111111111111111111111111111111111111111111111111")
    ]


def _factory(tmp_path: Path, filename: str):
    database_url = f"sqlite:///{tmp_path / filename}"
    init_db(database_url)
    engine = build_engine(database_url)
    return build_session_factory(engine)


def _patch_kalshi_public_fetches(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, str]]:
    fixture_adapter = KalshiReadOnlyAdapter()
    original_catalog = KalshiReadOnlyAdapter.fetch_market_catalog
    original_detail = KalshiReadOnlyAdapter.fetch_market_detail
    original_orderbook = KalshiReadOnlyAdapter.fetch_orderbook
    calls: list[tuple[str, str]] = []

    def fake_catalog(
        self: KalshiReadOnlyAdapter,
        *,
        limit: int = 100,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> list[RawVenuePayload]:
        assert allow_network is True
        return original_catalog(
            fixture_adapter,
            limit=limit,
            allow_network=False,
            captured_at=captured_at,
        )[:limit]

    def fake_detail(
        self: KalshiReadOnlyAdapter,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        assert allow_network is True
        calls.append(("detail", external_market_id))
        return original_detail(
            fixture_adapter,
            external_market_id,
            allow_network=False,
            captured_at=captured_at,
        )

    def fake_orderbook(
        self: KalshiReadOnlyAdapter,
        external_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        assert allow_network is True
        calls.append(("orderbook", external_market_id))
        payload = original_orderbook(
            fixture_adapter,
            external_market_id,
            allow_network=False,
            captured_at=captured_at,
        )
        response_payload = dict(payload.response_payload)
        response_payload.pop("event_ticker", None)
        return payload.model_copy(update={"response_payload": response_payload})

    monkeypatch.setattr(KalshiReadOnlyAdapter, "fetch_market_catalog", fake_catalog)
    monkeypatch.setattr(KalshiReadOnlyAdapter, "fetch_market_detail", fake_detail)
    monkeypatch.setattr(KalshiReadOnlyAdapter, "fetch_orderbook", fake_orderbook)
    return calls


def _patch_polymarket_public_fetches(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, str]]:
    fixture_adapter = PolymarketReadOnlyAdapter()
    original_detail = PolymarketReadOnlyAdapter.fetch_market_detail_by_gamma_id
    original_orderbook = PolymarketReadOnlyAdapter.fetch_orderbook_by_token_id
    original_price_history = PolymarketReadOnlyAdapter.fetch_price_history_by_token_id
    calls: list[tuple[str, str]] = []

    def fake_detail(
        self: PolymarketReadOnlyAdapter,
        gamma_market_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        assert allow_network is True
        calls.append(("detail", gamma_market_id))
        return original_detail(
            fixture_adapter,
            gamma_market_id,
            allow_network=False,
            captured_at=captured_at,
        )

    def fake_orderbook(
        self: PolymarketReadOnlyAdapter,
        token_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        assert allow_network is True
        calls.append(("orderbook", token_id))
        return original_orderbook(
            fixture_adapter,
            token_id,
            allow_network=False,
            captured_at=captured_at,
        )

    def fake_price_history(
        self: PolymarketReadOnlyAdapter,
        token_id: str,
        *,
        allow_network: bool = False,
        captured_at: datetime | None = None,
    ) -> RawVenuePayload:
        assert allow_network is True
        calls.append(("price_history", token_id))
        return original_price_history(
            fixture_adapter,
            token_id,
            allow_network=False,
            captured_at=captured_at,
        )

    monkeypatch.setattr(
        PolymarketReadOnlyAdapter,
        "fetch_market_detail_by_gamma_id",
        fake_detail,
    )
    monkeypatch.setattr(
        PolymarketReadOnlyAdapter,
        "fetch_orderbook_by_token_id",
        fake_orderbook,
    )
    monkeypatch.setattr(
        PolymarketReadOnlyAdapter,
        "fetch_price_history_by_token_id",
        fake_price_history,
    )
    return calls


def _save_kalshi_mapping(repo: PredictionMarketRepository) -> None:
    now = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    repo.upsert_venue_market_mapping(
        VenueMarketMapping(
            mapping_id="mapping_kalshi_kxweather_nyc_rain_20260930",
            venue_id="kalshi",
            venue_name="Kalshi",
            external_event_id="KXWEATHER-NYC-RAIN",
            external_market_id="KXWEATHER-NYC-RAIN-20260930",
            external_symbol="KXWEATHER-NYC-RAIN-20260930",
            canonical_event_id="kalshi_event_kxweather_nyc_rain",
            canonical_market_id="kalshi_market_kxweather_nyc_rain_20260930",
            external_url=None,
            first_seen_at=now,
            last_seen_at=now,
            status=VenueMappingStatus.ACTIVE,
            metadata={"test": True},
        )
    )


def _save_polymarket_market_mapping_and_tokens(
    repo: PredictionMarketRepository,
    *,
    gamma_market_id: str | None = "pm-nyc-temp-20260704",
    drop_mapping_gamma_id: bool = False,
    save_tokens: bool = True,
    enable_orderbook: bool | None = True,
    only_yes_token: bool = False,
) -> None:
    now = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)
    market_id = "polymarket_market_0xabc123nyctemp"
    repo.upsert_venue(
        Venue(
            venue_id="polymarket",
            name="Polymarket",
            jurisdiction=None,
            venue_type=VenueType.CRYPTO_CLOB,
            metadata={"test": True},
        )
    )
    repo.upsert_event(
        Event(
            event_id="polymarket_event_nyc_90_degrees_july_4_2026",
            venue_id="polymarket",
            title="NYC July 4 weather",
            category="Weather",
            start_time=None,
            end_time=None,
            metadata={"test": True},
        )
    )
    repo.upsert_market(
        Market(
            market_id=market_id,
            venue_id="polymarket",
            event_id="polymarket_event_nyc_90_degrees_july_4_2026",
            title="Will NYC reach 90 degrees on July 4, 2026?",
            description=None,
            market_type=MarketType.BINARY,
            status=MarketStatus.ACTIVE,
            created_time=None,
            close_time=None,
            settlement_time=None,
            metadata={"condition_id": "0xabc123nyctemp", "gamma_market_id": gamma_market_id},
        )
    )
    repo.upsert_outcome(
        Outcome(
            outcome_id=f"{market_id}_yes",
            market_id=market_id,
            label="Yes",
            payout=Decimal("1"),
            metadata={"token_id": _yes_token_id()},
        )
    )
    repo.upsert_outcome(
        Outcome(
            outcome_id=f"{market_id}_no",
            market_id=market_id,
            label="No",
            payout=Decimal("1"),
            metadata={"token_id": _no_token_id()},
        )
    )
    metadata = {
        "condition_id": "0xabc123nyctemp",
        "question_id": "0xquestion123",
        "gamma_market_id": None if drop_mapping_gamma_id else gamma_market_id,
        "enable_orderbook": enable_orderbook,
    }
    repo.upsert_venue_market_mapping(
        VenueMarketMapping(
            mapping_id="mapping_polymarket_0xabc123nyctemp",
            venue_id="polymarket",
            venue_name="Polymarket",
            external_event_id="nyc-90-degrees-july-4-2026",
            external_market_id="0xabc123nyctemp",
            external_symbol="0xabc123nyctemp",
            canonical_event_id="polymarket_event_nyc_90_degrees_july_4_2026",
            canonical_market_id=market_id,
            external_url="nyc-90-degrees-july-4-2026",
            first_seen_at=now,
            last_seen_at=now,
            status=VenueMappingStatus.ACTIVE,
            metadata=metadata,
        )
    )
    if not save_tokens:
        return
    token_specs = [
        ("yes", "Yes", _yes_token_id(), VenueOutcomeTokenSide.YES),
        ("no", "No", _no_token_id(), VenueOutcomeTokenSide.NO),
    ]
    if only_yes_token:
        token_specs = token_specs[:1]
    for suffix, label, token_id, side in token_specs:
        repo.upsert_venue_outcome_token_mapping(
            VenueOutcomeTokenMapping(
                mapping_id=f"token_mapping_polymarket_{token_id}",
                venue_id="polymarket",
                venue_name="Polymarket",
                canonical_market_id=market_id,
                canonical_outcome_id=f"{market_id}_{suffix}",
                outcome_label=label,
                external_market_id="0xabc123nyctemp",
                condition_id="0xabc123nyctemp",
                question_id="0xquestion123",
                gamma_market_id=gamma_market_id,
                gamma_event_id="nyc-90-degrees-july-4-2026",
                market_address="0x0000000000000000000000000000000000000001",
                token_id=token_id,
                asset_id=token_id,
                token_side=side,
                enable_orderbook=enable_orderbook,
                first_seen_at=now,
                last_seen_at=now,
                status=VenueOutcomeTokenStatus.ACTIVE,
                metadata={"test": True},
            )
        )


def _yes_token_id() -> str:
    return "1111111111111111111111111111111111111111111111111111111111111111"


def _no_token_id() -> str:
    return "2222222222222222222222222222222222222222222222222222222222222222"
