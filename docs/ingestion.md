# Read-Only Venue Ingestion v1

Venue payloads are archived before normalization because the public payload is evidence.
Normalized `Venue`, `Market`, rule snapshot, and orderbook objects can be regenerated later
from the archived payload without depending on a live venue response.

This layer is read-only. It does not accept venue credentials, private keys, wallets,
authenticated endpoints, order placement, order cancellation, or position data.

## Models

`RawVenuePayload` stores the public response, source URL, sanitized request parameters,
capture timestamp, schema version, and deterministic SHA-256 `response_hash`.

`VenueMarketMapping` maps external identifiers such as Kalshi tickers and Polymarket
condition IDs to canonical prediction-desk market IDs.

`IngestionRun` records a fixture or manual public-fetch ingestion attempt, including counts
for archived payloads, created and updated markets, rule snapshots, orderbooks, derived
price snapshots, derived liquidity snapshots, quality reports, and errors.

`IngestionError` records per-payload failures while allowing the ingestion run to continue.

## Fixture Ingestion

Fixture ingestion is the default path for tests, CI, and smoke checks:

```bash
prediction-desk ingest-fixtures --venue kalshi
prediction-desk ingest-fixtures --venue polymarket
prediction-desk ingest-fixtures --venue all
```

Fixtures live under `sample_data/venue_payloads/`. They are small, deterministic, and
contain no credentials or user data. Tests reference the same safe committed sample-data
tree, so Docker images do not need to copy the test directory to ingest fixtures.

## Manual Public Sample

Manual public fetching is explicit and read-only:

```bash
prediction-desk ingest-public-sample --venue kalshi --allow-network
prediction-desk ingest-public-sample --venue polymarket --allow-network
```

If `--allow-network` is omitted, the command fails safely. The adapters use public GET
requests only, conservative timeouts, and no auth headers.

## Kalshi Normalization

Kalshi fixtures include market catalog/detail payloads and binary orderbooks. The
normalizer:

- maps ticker and event ticker into deterministic canonical IDs
- preserves ticker and event ticker in metadata
- builds rule snapshots from primary and secondary rules
- maps YES/NO binary outcomes
- converts cent prices into Decimal prices in `[0, 1]`
- converts NO bids into YES-side asks with `ask_price = 1 - no_bid_price`

## Polymarket Normalization

Polymarket fixtures model Gamma market payloads and public CLOB orderbooks. The normalizer:

- maps condition IDs, question IDs, market IDs, and token IDs into metadata
- builds binary or multi-outcome canonical markets
- builds rule snapshots from resolution rules and description text
- maps active/closed/resolved status into canonical status
- preserves token IDs and condition IDs
- normalizes CLOB bid/ask prices as Decimal values in `[0, 1]`
- converts price-history fixture points into `MarketPriceSnapshot` rows without using
  `observed_at` as replay availability

## Run-Once Scheduler

The run-once scheduler wraps fixture ingestion or manual public sample ingestion for cron
and deployment jobs:

```bash
prediction-desk ingestion-run-once --venue kalshi
prediction-desk ingestion-run-once --venue polymarket
prediction-desk ingestion-cursors
```

It can derive canonical market-data snapshots, compute quality reports, update cursors, and
then return. It is not a daemon and it does not call network unless
`mode=manual_public_fetch` and `--allow-network` are explicitly provided.

## Downstream Use

Ingested rule snapshots feed the resolution corpus. Ingested orderbooks feed canonical
price/liquidity snapshots, trust verdicts, and point-in-time replay. Future phases can add
historical venue adapters, fast-lane integrity checks, cross-venue equivalence checks,
execution simulation, and MiroFish slow-lane feature generation without changing the
raw-payload archive contract.

See [market_data.md](market_data.md) for the canonical market-data and quality-report
contract. See [equivalence.md](equivalence.md) for contract-comparison objects that can use
ingested Kalshi and Polymarket fixtures without any external calls.
