"""Service layer for canonical market-data derivation and quality reports."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from prediction_desk.ingestion.enums import VenueEndpointType
from prediction_desk.ingestion.models import RawVenuePayload
from prediction_desk.marketdata.enums import MarketPriceSource
from prediction_desk.marketdata.models import (
    MarketDataDerivationResult,
    MarketDataLatest,
    MarketDataQualityReport,
    MarketLiquiditySnapshot,
    MarketPriceSnapshot,
    compute_market_price_hash,
)
from prediction_desk.marketdata.orderbook import (
    derive_liquidity_snapshot_from_orderbook,
    derive_price_snapshot_from_orderbook,
)
from prediction_desk.marketdata.quality import build_quality_report

if TYPE_CHECKING:
    from prediction_desk.persistence.repositories import PredictionMarketRepository


class MarketDataServiceError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class MarketDataService:
    def __init__(self, repo: PredictionMarketRepository) -> None:
        self.repo = repo

    def derive_market_data_for_orderbook(
        self, orderbook_snapshot_id: str, *, force: bool = False
    ) -> MarketDataDerivationResult:
        orderbook = self.repo.get_orderbook_snapshot(orderbook_snapshot_id)
        if orderbook is None:
            raise MarketDataServiceError("orderbook_snapshot_not_found")
        market = self.repo.get_market(orderbook.market_id)
        if market is None:
            raise MarketDataServiceError("market_not_found")
        venue = self.repo.get_venue(market.venue_id)
        if venue is None:
            raise MarketDataServiceError("venue_not_found")
        if not orderbook.bids and not orderbook.asks:
            return MarketDataDerivationResult(market_id=market.market_id)
        price = derive_price_snapshot_from_orderbook(market, orderbook, venue)
        liquidity = derive_liquidity_snapshot_from_orderbook(market, orderbook, venue)
        result = MarketDataDerivationResult(market_id=market.market_id)
        if force or self.repo.find_price_snapshot_by_hash(price.data_hash) is None:
            self.repo.save_market_price_snapshot(price)
            result.price_snapshots_created += 1
            result.price_snapshots.append(price)
        if force or self.repo.find_liquidity_snapshot_by_hash(liquidity.data_hash) is None:
            self.repo.save_market_liquidity_snapshot(liquidity)
            result.liquidity_snapshots_created += 1
            result.liquidity_snapshots.append(liquidity)
        return result

    def derive_market_data_for_market(
        self, market_id: str, *, force: bool = False
    ) -> MarketDataDerivationResult:
        if self.repo.get_market(market_id) is None:
            raise MarketDataServiceError("market_not_found")
        result = MarketDataDerivationResult(market_id=market_id)
        for orderbook in self.repo.list_orderbook_snapshots(market_id, limit=10000):
            item = self.derive_market_data_for_orderbook(orderbook.snapshot_id, force=force)
            result.price_snapshots_created += item.price_snapshots_created
            result.liquidity_snapshots_created += item.liquidity_snapshots_created
            result.price_snapshots.extend(item.price_snapshots)
            result.liquidity_snapshots.extend(item.liquidity_snapshots)
        return result

    def derive_market_data_for_all_markets(
        self, *, force: bool = False, limit: int | None = None
    ) -> MarketDataDerivationResult:
        result = MarketDataDerivationResult()
        for market in self.repo.list_markets(limit=limit or 500):
            item = self.derive_market_data_for_market(market.market_id, force=force)
            result.price_snapshots_created += item.price_snapshots_created
            result.liquidity_snapshots_created += item.liquidity_snapshots_created
            result.price_snapshots.extend(item.price_snapshots)
            result.liquidity_snapshots.extend(item.liquidity_snapshots)
        return result

    def normalize_price_history_payload(
        self, payload_id: str, *, force: bool = False
    ) -> MarketDataDerivationResult:
        payload = self.repo.get_raw_venue_payload(payload_id)
        if payload is None:
            raise MarketDataServiceError("raw_payload_not_found")
        if payload.endpoint_type != VenueEndpointType.PRICE_HISTORY:
            return MarketDataDerivationResult()
        snapshots = _price_history_snapshots(payload, self.repo)
        result = MarketDataDerivationResult()
        for snapshot in snapshots:
            result.market_id = snapshot.market_id
            if force or self.repo.find_price_snapshot_by_hash(snapshot.data_hash) is None:
                self.repo.save_market_price_snapshot(snapshot)
                result.price_snapshots_created += 1
                result.price_snapshots.append(snapshot)
        return result

    def compute_market_data_quality(
        self,
        market_id: str,
        asof_timestamp: datetime,
        *,
        freshness_threshold_seconds: int = 3600,
        wide_spread_threshold: Decimal = Decimal("0.10"),
    ) -> MarketDataQualityReport:
        if self.repo.get_market(market_id) is None:
            raise MarketDataServiceError("market_not_found")
        report = build_quality_report(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            created_at=datetime.now(tz=UTC),
            price_snapshot=self.repo.get_latest_price_snapshot_asof(
                market_id, asof_timestamp
            ),
            liquidity_snapshot=self.repo.get_latest_liquidity_snapshot_asof(
                market_id, asof_timestamp
            ),
            orderbook_snapshot=self.repo.get_latest_orderbook_snapshot_asof(
                market_id, asof_timestamp
            ),
            rule_snapshot=self.repo.get_latest_rule_snapshot_asof(market_id, asof_timestamp),
            venue_mapping=self.repo.get_mapping_by_canonical_market_id(market_id),
            freshness_threshold_seconds=freshness_threshold_seconds,
            wide_spread_threshold=wide_spread_threshold,
        )
        self.repo.save_market_data_quality_report(report)
        return report

    def compute_market_data_quality_for_all(
        self,
        asof_timestamp: datetime,
        *,
        freshness_threshold_seconds: int = 3600,
        wide_spread_threshold: Decimal = Decimal("0.10"),
    ) -> MarketDataDerivationResult:
        result = MarketDataDerivationResult()
        for market in self.repo.list_markets(limit=500):
            report = self.compute_market_data_quality(
                market.market_id,
                asof_timestamp,
                freshness_threshold_seconds=freshness_threshold_seconds,
                wide_spread_threshold=wide_spread_threshold,
            )
            result.quality_reports_created += 1
            result.quality_reports.append(report)
        return result

    def get_latest_market_data_asof(
        self, market_id: str, asof_timestamp: datetime
    ) -> MarketDataLatest:
        if self.repo.get_market(market_id) is None:
            raise MarketDataServiceError("market_not_found")
        return MarketDataLatest(
            market_id=market_id,
            asof_timestamp=asof_timestamp,
            price_snapshot=self.repo.get_latest_price_snapshot_asof(
                market_id, asof_timestamp
            ),
            liquidity_snapshot=self.repo.get_latest_liquidity_snapshot_asof(
                market_id, asof_timestamp
            ),
            quality_report=self.repo.get_latest_quality_report_asof(
                market_id, asof_timestamp
            ),
        )

    def list_price_snapshots(
        self,
        market_id: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketPriceSnapshot]:
        return self.repo.list_price_snapshots(
            market_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def list_liquidity_snapshots(
        self,
        market_id: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> list[MarketLiquiditySnapshot]:
        return self.repo.list_liquidity_snapshots(
            market_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )


def _price_history_snapshots(
    payload: RawVenuePayload, repo: PredictionMarketRepository
) -> list[MarketPriceSnapshot]:
    if payload.venue_id != "polymarket":
        return []
    external_market_id = payload.external_id
    if external_market_id is None:
        external_market_id = payload.request_params.get("market")
    if external_market_id is None:
        return []
    mapping = repo.get_mapping_by_external_market_id(payload.venue_name, str(external_market_id))
    if mapping is None or mapping.canonical_market_id is None:
        return []
    history = payload.response_payload.get("history", [])
    if not isinstance(history, list):
        return []
    snapshots: list[MarketPriceSnapshot] = []
    for point in history:
        if not isinstance(point, dict) or point.get("p") is None or point.get("t") is None:
            continue
        observed_at = datetime.fromisoformat(str(point["t"]).replace("Z", "+00:00"))
        available_at = datetime.fromisoformat(
            str(point.get("available_at", payload.captured_at.isoformat())).replace("Z", "+00:00")
        )
        price = Decimal(str(point["p"]))
        snapshot = MarketPriceSnapshot(
            price_snapshot_id="pending",
            market_id=mapping.canonical_market_id,
            outcome_id=None,
            venue_id=payload.venue_id,
            venue_name=payload.venue_name,
            source=MarketPriceSource.VENUE_PRICE_HISTORY,
            observed_at=observed_at,
            captured_at=payload.captured_at,
            available_at=available_at,
            price=price,
            bid=None,
            ask=None,
            mid=price,
            spread=None,
            last_trade_price=price,
            volume=None,
            open_interest=None,
            source_payload_id=payload.payload_id,
            orderbook_snapshot_id=None,
            external_market_id=str(external_market_id),
            external_outcome_id=str(point.get("token_id")) if point.get("token_id") else None,
            data_hash="pending",
            metadata={"raw_point": point},
        )
        data_hash = compute_market_price_hash(snapshot)
        snapshots.append(
            snapshot.model_copy(
                update={"price_snapshot_id": f"price_{data_hash[:24]}", "data_hash": data_hash}
            )
        )
    return snapshots
