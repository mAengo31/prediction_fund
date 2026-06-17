# Data Scaling, Historical Backfill, And Read-Only Collection

DataOps v1 adds controlled collection orchestration for long-running research. It is a
read-only data layer: it does not place orders, route execution, accept credentials, or
connect to authenticated venue endpoints.

Scaling data is required before making research-edge claims because sparse snapshots can
hide stale data, missing rules, unsupported history, and low coverage. DataOps records
what was collected, what was unavailable, and what remains missing so strategy research
can evaluate inputs instead of assuming completeness.

## Core Objects

`MarketUniverseDefinition` stores a named research universe: venue names, categories,
market statuses, market types, include/exclude IDs, title filters, and optional minimum
quality/liquidity thresholds.

`MarketUniverseMember` records the deterministic membership decision for one market as of
a timestamp, including inclusion and exclusion reason codes.

`CollectionPlan` stores a read-only collection configuration: universe, venues, endpoint
types, cadence, lookback, per-run limits, and whether to derive market data, compute
quality, analyze rules, or recompute verdicts. Default public-fetch plans set
`allow_network_default=false`.

`CollectionRun` records one synchronous collection execution suitable for cron or a
deployment job. Fixture mode uses committed fixture payloads. Manual public fetch mode
requires explicit `allow_network=true`.

`BackfillJob` and `BackfillSegment` record historical imports. Unsupported historical
endpoints are stored as `SKIPPED_UNSUPPORTED` segments instead of fabricated data.

`DataCoverageReport` summarizes coverage for a market, universe, venue, or global scope:
rules, orderbooks, price snapshots, liquidity snapshots, quality reports, stale markets,
missing objects, and a deterministic coverage score.

`DataGap` records missing or stale data such as `MISSING_RULE_SNAPSHOT`,
`MISSING_PRICE_SNAPSHOT`, `MISSING_LIQUIDITY_SNAPSHOT`, `STALE_MARKET_DATA`, and
`UNSUPPORTED_HISTORICAL_ENDPOINT`.

`DataRetentionPolicy` is reporting-only in v1. No deletion or compaction is performed.

## Timestamp Semantics

DataOps preserves the existing point-in-time model:

- `observed_at`: when the venue says a datapoint occurred.
- `captured_at`: when prediction-desk captured or imported it.
- `available_at`: when replay and research may use it.

Historical backfill can import old `observed_at` values, but those rows are not replay
visible before `available_at`. Tests cover the case where `observed_at < T` but
`available_at > T`, and the snapshot is not returned by as-of lookup.

## Modes

Fixture mode is deterministic and network-free. It is used by tests, CI, and smoke
scripts.

Manual public fetch mode is explicit, read-only, GET-oriented, credential-free, and must
be called with `allow_network=true`. Tests do not use this mode.

## CLI

```bash
prediction-desk dataops-defaults
prediction-desk dataops-universes
prediction-desk dataops-build-universe --universe-id market_universe_...
prediction-desk dataops-collection-plans
prediction-desk dataops-run-collection --venue kalshi --mode FIXTURE
prediction-desk dataops-backfill-create \
  --venue kalshi \
  --endpoint-type ORDERBOOK \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --start 2026-06-16T11:00:00+00:00 \
  --end 2026-06-16T12:00:00+00:00
prediction-desk dataops-backfill-run --job-id backfill_job_...
prediction-desk dataops-coverage --scope-type GLOBAL
prediction-desk dataops-gaps
prediction-desk dataops-cycle --mode FIXTURE
```

## API

DataOps endpoints are under `/api/v1/dataops`:

- `POST /dataops/defaults`
- `GET /dataops/universes`
- `POST /dataops/universes/{universe_id}/build`
- `GET /dataops/universes/{universe_id}/members`
- `GET /dataops/collection-plans`
- `POST /dataops/collection/run-once`
- `GET /dataops/collection-runs`
- `GET /dataops/collection-runs/{collection_run_id}`
- `POST /dataops/backfill/jobs`
- `POST /dataops/backfill/jobs/{backfill_job_id}/run`
- `GET /dataops/backfill/jobs`
- `GET /dataops/backfill/jobs/{backfill_job_id}`
- `GET /dataops/backfill/jobs/{backfill_job_id}/segments`
- `POST /dataops/coverage/compute`
- `GET /dataops/coverage`
- `POST /dataops/gaps/detect`
- `GET /dataops/gaps`

## Scheduling

V1 does not include a daemon. Run collection once from cron or deployment jobs:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

For a manual public collection job, pass `--allow-network` explicitly. Do not provide
credentials; none are required or accepted.

## Research Use

Coverage and gap reports help strategy research and simulated paper runs understand data
availability. They do not change pre-trade or paper execution behavior directly in v1.
They also do not create live venue access or execution authority.
