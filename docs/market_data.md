# Canonical Market Data v1

Canonical market data is separate from raw venue payloads. Raw payloads preserve exactly
what was captured from a fixture or explicit read-only public fetch. Canonical market-data
snapshots convert those venue-specific shapes into replay-safe, venue-neutral time series.

This layer does not trade, simulate execution, calculate PnL, call authenticated venue
endpoints, store credentials, or run a background daemon.

## Timestamp Semantics

Market-data rows use three timestamps:

- `observed_at`: when the venue says the data point occurred.
- `captured_at`: when prediction-desk archived the payload or stored the snapshot.
- `available_at`: when replay and research are allowed to use the data.

As-of repository methods use `available_at <= asof_timestamp`. They do not use
`observed_at` to decide replay availability. For fixture ingestion, committed fixtures use
deterministic timestamps and default `available_at` to `captured_at` unless the fixture
explicitly provides a safe `available_at`. Manual public fetches default `available_at` to
`captured_at`.

## Models

`MarketPriceSnapshot` stores canonical probability/price observations. It can come from an
orderbook-derived mid, a venue last price, venue price history, trade-derived data, manual
fixtures, or an unknown source. Values are `Decimal`, and each row has a deterministic
`data_hash`.

`MarketLiquiditySnapshot` stores orderbook-derived liquidity metrics: best bid, best ask,
mid, spread, spread in basis points, best-level depth, total depth, imbalance, empty-book
flag, and crossed-book flag.

`MarketDataQualityReport` stores an as-of quality status for one market. It checks whether
recent price and orderbook data exist, whether a rule snapshot and venue mapping exist, and
whether the latest liquidity looks stale, wide, crossed, empty, one-sided, or invalid.

`IngestionCursor` stores run-once scheduler/backfill state for a venue, endpoint, and
optional market. It is designed for cron or deployment jobs, not a long-running process.

## Derivation

Orderbook derivation is deterministic:

- `best_bid` is the highest bid.
- `best_ask` is the lowest ask.
- `mid_price = (best_bid + best_ask) / 2` when both sides exist.
- `spread = best_ask - best_bid` when both sides exist.
- `spread_bps = spread / mid_price * 10000` when possible.
- `book_imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)` when depth exists.

One-sided books keep bid or ask fields but leave mid and spread empty. Empty and crossed
books are explicitly flagged. All numeric work uses `Decimal`, not float.

## Price History

Polymarket price-history fixture payloads are normalized into `MarketPriceSnapshot` rows
with source `VENUE_PRICE_HISTORY`. The venue-provided point time is `observed_at`; the raw
payload capture time is `captured_at`; replay availability is `available_at`, defaulting to
`captured_at` unless the fixture provides a safe explicit value.

Kalshi price-history-like payloads are supported only if a fixture provides enough public
read-only data to normalize without fabricating unsupported fields.

## Quality Scoring

Quality starts at `100` and applies deterministic penalties for reason codes such as:

- `NO_PRICE_SNAPSHOT`
- `NO_ORDERBOOK_SNAPSHOT`
- `NO_RULE_SNAPSHOT`
- `NO_VENUE_MAPPING`
- `STALE_MARKET_DATA`
- `CROSSED_BOOK`
- `EMPTY_BOOK`
- `WIDE_SPREAD`
- `OUT_OF_BOUNDS_PRICE`
- `MISSING_BID_OR_ASK`
- `FUTURE_AVAILABLE_AT`

Severity is `OK`, `WARNING`, or `ERROR` based on the score and severe flags.

## Run-Once Scheduler

`run_ingestion_once` is an explicit one-shot orchestration entry point suitable for cron,
deployment jobs, or CI smoke checks. It supports `fixture` mode and
`manual_public_fetch` mode. Manual public fetch requires `allow_network=true`; otherwise it
fails safely. It does not run a daemon or loop.

The run-once path can:

- archive raw venue payloads
- normalize canonical markets, rules, orderbooks, and price history
- derive price and liquidity snapshots
- compute data-quality reports
- update ingestion cursors
- optionally analyze rules and recompute trust verdicts

## CLI

```bash
prediction-desk ingestion-run-once --venue kalshi
prediction-desk market-data-derive --all
prediction-desk market-data-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk market-data-prices --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk data-quality --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk ingestion-cursors
```

## API

Market-data endpoints are under `/api/v1`:

- `GET /api/v1/markets/{market_id}/market-data/latest`
- `GET /api/v1/markets/{market_id}/market-data/prices`
- `GET /api/v1/markets/{market_id}/market-data/liquidity`
- `POST /api/v1/markets/{market_id}/market-data/derive`
- `POST /api/v1/markets/{market_id}/data-quality/recompute`
- `GET /api/v1/markets/{market_id}/data-quality/latest`
- `GET /api/v1/ingestion/cursors`
- `POST /api/v1/ingestion/run-once`

## Future Use

Canonical market data now feeds fast-lane integrity signals and historical replay.
Cross-venue equivalence v1 does not use price discrepancies to infer equivalence, but replay
metadata can cite equivalence assessments alongside market-data snapshots. Later phases can
use the same snapshots for execution simulation, cross-venue divergence signals, and future
MiroFish slow-lane feature snapshots. Execution simulation, PnL, alpha modeling, and
MiroFish are deliberately not implemented in this layer.

See [integrity_signals.md](integrity_signals.md) for the deterministic integrity features
derived from canonical market data. See [equivalence.md](equivalence.md) for deterministic
contract-comparison scoring. See [pretrade_gate.md](pretrade_gate.md) for how quality and
liquidity context feed admissibility decisions.
