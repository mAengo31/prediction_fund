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
`UNSUPPORTED_HISTORICAL_ENDPOINT`. Gap rows are append-only audit records in v1. A later
collection run can improve the latest coverage report while still adding new gap rows
from a fresh detection pass.

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
scripts, including staging smoke:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/azure_staging_smoke.sh
```

Manual public fetch mode is explicit, read-only, GET-oriented, credential-free, and must
be called with `allow_network=true`. Tests do not use this mode. The staging pilot script
adds a second operator gate, refuses to run unless `CONFIRM_PUBLIC_READ_ONLY=true`, and
caps `MAX_PAYLOADS` at 10:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

## CLI

```bash
prediction-desk dataops-defaults
prediction-desk dataops-universes
prediction-desk dataops-build-universe --universe-id market_universe_...
prediction-desk dataops-collection-plans
prediction-desk dataops-run-collection --venue kalshi --mode FIXTURE
prediction-desk dataops-run-collection \
  --venue kalshi \
  --mode MANUAL_PUBLIC_FETCH \
  --allow-network \
  --endpoint-type MARKET_DETAIL \
  --endpoint-type ORDERBOOK \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --max-payloads 5
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

Manual public fetch defaults to `MARKET_LIST` when endpoint types are omitted. Targeted
follow-up can request `MARKET_DETAIL`, `ORDERBOOK`, and supported `PRICE_HISTORY` payloads
for existing canonical market IDs/venue mappings. Unsupported endpoint/venue combinations
are recorded as safe partial-run errors; the system does not fabricate historical data.

Kalshi targeted follow-up uses the venue market mapping external market ticker. Polymarket
targeted follow-up is token-aware: catalog/detail normalization persists Gamma market IDs,
condition/question IDs, outcome labels, `enableOrderBook`, and CLOB token/asset IDs in
`venue_outcome_token_mappings`. Polymarket `MARKET_DETAIL` resolves the Gamma market ID
from mapping metadata, and Polymarket `ORDERBOOK` resolves token/asset IDs from the
outcome-token mapping. Polymarket `PRICE_HISTORY` also resolves token/asset IDs and uses
token-level public CLOB requests with `interval=1d` and `fidelity=60`. If a Gamma ID is
missing from the venue mapping, targeted detail follow-up can fall back to active
outcome-token mappings that still carry the Gamma ID. If a Gamma ID or token ID is still
missing, the collection run records a safe missing-identifier error instead of guessing.

Example token-aware Polymarket collection:

```bash
prediction-desk dataops-run-collection \
  --venue polymarket \
  --mode MANUAL_PUBLIC_FETCH \
  --allow-network \
  --endpoint-type MARKET_DETAIL \
  --endpoint-type ORDERBOOK \
  --endpoint-type PRICE_HISTORY \
  --market-id polymarket_market_... \
  --max-payloads 5
```

This is public-read only. It does not use authenticated CLOB endpoints, venue trading
credentials, wallets, private keys, order routing, or execution authority.

## Scheduling

V1 does not include a daemon. Run collection once from cron or deployment jobs:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

For a manual public collection job, pass `--allow-network` explicitly. Do not provide
credentials; none are required or accepted.

For staging operations, prefer the runbook in
[azure_staging.md](azure_staging.md) and [staging_dataops_pilot.md](staging_dataops_pilot.md).
They cover Azure deployment, migrations, fixture smoke, public-read approval, database
count inspection, coverage/gap readback, and rollback.

## Research Use

Coverage and gap reports help strategy research and simulated paper runs understand data
availability. They do not change pre-trade or paper execution behavior directly in v1.
They also do not create live venue access or execution authority.

Interpret current coverage from the latest `DataCoverageReport`. Interpret cumulative
`DataGap` row counts as history of detection passes, not as the current number of open
gaps. For public-read pilots, do not close missing-rule gaps unless the archived public
payload contains usable rule, resolution, or settlement text.
