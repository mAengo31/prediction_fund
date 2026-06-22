# prediction-desk

`prediction-desk` is a prediction-market research and operations platform for
point-in-time analysis, data quality review, replay, simulated execution, and desk-facing
decision support.

It is intentionally **not** a live trading system. The repository contains no live order
placement, no order cancellation, no wallets, no private keys, no venue trading
credentials, no real account IDs, and no execution adapters.

## Current Status

The project currently supports:

- canonical prediction-market domain models
- SQLAlchemy persistence and Alembic migrations through `20260619_0016`
- internal FastAPI API with bearer-token auth support
- Docker and Postgres local deployment
- Azure Container Apps staging deployment path
- Azure PostgreSQL Flexible Server persistence
- fixture-only Azure scheduling
- read-only Kalshi public-read validation
- token-aware Polymarket public-read validation
- Polymarket CLOB orderbook and price-history ingestion
- canonical market data snapshots and data-quality reports
- resolution corpus and rule ambiguity analysis
- point-in-time replay harness
- integrity signals
- cross-venue equivalence engine
- cross-venue divergence signals
- pre-trade admissibility gate for hypothetical intents
- simulated-only paper execution
- deterministic strategy research harness
- slow-lane scenario feature interface
- DataOps universes, collection plans, coverage, gaps, and backfill records
- desk decision workbench with queues, cards, notes, and status summaries
- vendor dataset intake and dry-run evaluation scaffold
- vendor schema mapping configs
- large-file vendor sampling for CSV, JSONL, and Parquet

## Safety Boundary

These boundaries are deliberate and should not be weakened casually:

- No live trading.
- No order routing.
- No venue trading credentials.
- No authenticated venue trading endpoints.
- No wallets or private keys.
- No real account IDs.
- No execution adapters.
- No public-read collection schedule.
- No vendor API pulls.
- No canonical writes from vendor samples.
- No LLM calls in core analysis paths.
- No MiroFish runtime execution.

Fixture collection may be scheduled. Public-read collection remains manual and explicitly
gated. Vendor data evaluation remains local-file and dry-run only.

## Repository Layout

```text
src/prediction_desk/
  api/             FastAPI app, auth, routes, schemas
  dataops/         universes, collection plans, coverage, gaps, backfill
  divergence/      equivalence-gated cross-venue divergence context
  domain/          canonical market, event, outcome, rule, venue models
  equivalence/     contract comparison and comparable-market grouping
  ingestion/       read-only fixture/public payload ingestion
  integrity/       deterministic market integrity features/signals
  marketdata/      orderbook, price, liquidity, and quality reports
  paper/           simulated-only orders, fills, ledger, portfolio
  persistence/     SQLAlchemy ORM, repositories, database setup
  pretrade/        hypothetical-intent admissibility checks
  replay/          point-in-time replay harness
  research/        deterministic research features/signals/proposals
  resolution/      rule parsing, ambiguity, diffs
  scenario/        fixture-backed slow-lane scenario features
  scoring/         trust and resolution-risk scoring
  vendor_data/     local vendor sample inspection, validation, dry-run evaluation
  workbench/       review queues, decision cards, comparison cards, notes

docs/              subsystem and operations documentation
sample_data/       tiny committed fixtures and mapping configs
scripts/           local, Docker, staging, Azure, and smoke helpers
deploy/azure/      Azure staging infrastructure docs/templates
alembic/           migrations
tests/             unit, API, CLI, and integration tests
```

Downloaded vendor files belong under `data/vendor_samples/`, which is ignored by git.
Do not commit paid or downloaded vendor datasets.

## Quickstart

Use Python 3.12+.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Initialize the default local SQLite database and load deterministic fixtures:

```bash
prediction-desk init-db
prediction-desk load-sample-data
```

Run the local API:

```bash
scripts/run_api.sh
```

Check health:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl http://localhost:8000/api/v1/markets
```

## Quality Gates

Run the standard local validation suite:

```bash
python -m pytest
python -m ruff check .
python -m mypy
git diff --check
DATABASE_URL=sqlite:////tmp/prediction_desk_migration_check.db scripts/migrate.sh
docker compose config
```

Optional Docker smoke:

```bash
scripts/smoke_docker.sh
```

Optional Postgres tests, when local Postgres is available:

```bash
TEST_DATABASE_URL=postgresql+psycopg://prediction_desk:prediction_desk@localhost:55432/prediction_desk \
  python -m pytest -m postgres
```

## Docker Compose

```bash
cp .env.example .env
docker compose build
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm app prediction-desk load-sample-data
docker compose up -d app
curl http://localhost:8000/healthz
```

## API

Local development can run without token enforcement. Staging should require bearer-token
auth and should keep OpenAPI docs disabled.

Important environment variables:

```text
APP_ENV=staging
REQUIRE_API_TOKEN=true
ENABLE_OPENAPI_DOCS=false
DATABASE_URL=postgresql+psycopg://...
PREDICTION_DESK_API_TOKEN=...
LOG_LEVEL=INFO
APP_VERSION=...
GIT_COMMIT=...
```

Selected route groups:

- `/api/v1/markets`
- `/api/v1/ingestion/*`
- `/api/v1/dataops/*`
- `/api/v1/market-data/*`
- `/api/v1/integrity/*`
- `/api/v1/equivalence/*`
- `/api/v1/divergence/*`
- `/api/v1/pretrade/*`
- `/api/v1/paper/*`
- `/api/v1/research/*`
- `/api/v1/workbench/*`
- `/api/v1/vendor-data/*`

See [docs/api.md](docs/api.md).

## DataOps And Public Read

Fixture mode is deterministic and safe:

```bash
prediction-desk dataops-cycle --mode FIXTURE
prediction-desk dataops-coverage --scope-type GLOBAL
prediction-desk dataops-gaps
```

Manual public-read is opt-in and read-only:

```bash
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

Targeted Polymarket follow-up uses persisted token-aware mappings:

```bash
prediction-desk dataops-run-collection \
  --mode MANUAL_PUBLIC_FETCH \
  --allow-network \
  --venue polymarket \
  --endpoint-type MARKET_DETAIL \
  --endpoint-type ORDERBOOK \
  --endpoint-type PRICE_HISTORY \
  --market-id polymarket_market_... \
  --max-payloads 5
```

Public-read scheduling remains held. Do not schedule `MANUAL_PUBLIC_FETCH`.

See [docs/data_scaling.md](docs/data_scaling.md) and
[docs/staging_dataops_pilot.md](docs/staging_dataops_pilot.md).

## Desk Workbench

The workbench turns stored evidence into desk review artifacts. It does not recommend or
place trades.

```bash
prediction-desk workbench-run
prediction-desk workbench-build-queue
prediction-desk workbench-queue --latest
prediction-desk workbench-queue-summary
prediction-desk workbench-status
prediction-desk workbench-card --market-id mkt_...
prediction-desk workbench-notes
prediction-desk workbench-add-note \
  --market-id mkt_... \
  --text "Reviewed data-quality context. No trading action."
prediction-desk workbench-update-item-status \
  --queue-item-id queue_item_... \
  --review-status WATCHING \
  --reviewed-by operator \
  --review-outcome NEEDS_MORE_DATA \
  --review-reason "Keep in daily review."
```

Queue items are append-only for audit. `--latest` returns the deduplicated active queue.
Resolved and dismissed items are excluded by default from the active view.

See [docs/desk_workbench.md](docs/desk_workbench.md).

## Vendor Data Evaluation

Vendor data is evaluated as raw material. It is not imported into canonical market-data
tables in v1.

Supported local file types:

- CSV
- JSON
- JSONL
- Parquet, when PyArrow/Pandas are available

Register and evaluate a sample:

```bash
prediction-desk vendor-register-source \
  --vendor-name Kaggle \
  --dataset-name polymarket_tick_level_orderbook_dataset \
  --dataset-version kaggle_marvingozo_current \
  --license-status SAMPLE_ONLY

prediction-desk vendor-load-sample \
  --vendor-source-id vendor_source_... \
  --file-path data/vendor_samples/kaggle/.../snapshots_2026-03-23.parquet \
  --max-rows 10000

prediction-desk vendor-inspect-sample \
  --sample-file-id vendor_sample_... \
  --max-rows 10000

prediction-desk vendor-validate-sample \
  --sample-file-id vendor_sample_... \
  --max-rows 10000

prediction-desk vendor-dry-run-import \
  --sample-file-id vendor_sample_... \
  --sample-kind orderbook \
  --max-rows 10000

prediction-desk vendor-evaluate \
  --vendor-source-id vendor_source_... \
  --sample-file-id vendor_sample_...
```

Mapping configs can interpret vendor-specific columns without changing global heuristics:

```bash
prediction-desk vendor-inspect-sample \
  --sample-file-id vendor_sample_... \
  --mapping-config sample_data/vendor_samples/mapping_configs/debayan31415_btc_5m_top_of_book.json
```

Large-file sampling is supported with `--max-rows`. CSV and JSONL stream bounded rows.
Parquet uses PyArrow batch reads. Files over 500 MB should be sampled before processing.

Recent local vendor evaluations:

- `luciferforge/polymarket-historical-prices`: weak for replay; missing token IDs and
  replay-safe availability timestamps.
- `debayan31415/polymarket-5-minutes-btc-up-down-data`: prediction-market quote dataset,
  useful for exploratory dry-run research, but missing token IDs and full L2 depth.
- `marvingozo/polymarket-tick-level-orderbook-dataset`: sampled Parquet snapshot looked
  promising for dry-run L2 research; license and timestamp semantics still need review.
- `ithiria137/polymarket-l2-capture-cumulative-2026`: not downloaded; useful files are
  large SQLite databases and need a SQLite sampling path or owner-provided sample.

See [docs/vendor_data_evaluation.md](docs/vendor_data_evaluation.md).

## Azure Staging

Current Azure staging architecture:

- Azure Container Apps API
- Azure Database for PostgreSQL Flexible Server
- Azure Container Registry
- Azure Container Apps Job for fixture-only schedule
- bearer-token auth required
- OpenAPI docs disabled
- public-read schedule held
- fixture job runs every 12 hours

Useful scripts:

```bash
scripts/azure_build_push.sh
scripts/azure_deploy_staging.sh
scripts/azure_migrate_and_verify.sh
scripts/azure_staging_smoke.sh
scripts/azure_inspect_counts.sh
scripts/staging_workbench_smoke.sh
scripts/staging_desk_cycle.sh
scripts/staging_workbench_status.sh
scripts/azure_enable_fixture_schedule.sh
scripts/azure_disable_fixture_schedule.sh
```

Local secret files such as `.env.azure.staging.local` must not be committed.

See [docs/azure_staging.md](docs/azure_staging.md) and
[docs/deployment.md](docs/deployment.md).

## Research And Replay Examples

Resolution analysis:

```bash
prediction-desk analyze-rules --all
prediction-desk diff-rule-snapshots --market-id mkt_rate_cut_rule_change_2026
```

Replay:

```bash
prediction-desk replay-run \
  --policy trust_verdict_v1 \
  --start 2026-06-16T12:00:00+00:00 \
  --end 2026-06-16T13:00:00+00:00 \
  --interval-seconds 3600 \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --max-steps 10
```

Integrity:

```bash
prediction-desk integrity-run \
  --asof 2026-06-16T12:45:00Z \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --max-steps 10
```

Equivalence and divergence:

```bash
prediction-desk equivalence-run \
  --asof 2026-06-16T12:45:00Z \
  --max-pairs 10

prediction-desk divergence-run \
  --asof 2026-06-16T12:45:00Z \
  --max-pairs 10
```

Pre-trade and paper simulation:

```bash
prediction-desk pretrade-create-default-policy
prediction-desk pretrade-check \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --strategy-context RESEARCH \
  --intent-type RESEARCH_ONLY \
  --requested-size-units 1

prediction-desk paper-create-default-policy
prediction-desk paper-simulate-intent \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --intent-type AGGRESSIVE_LIMIT \
  --requested-price 0.52
```

Strategy research:

```bash
prediction-desk research-create-default-strategies
prediction-desk research-run \
  --strategy-id research_strategy_baseline_research_only_v1 \
  --start 2026-06-16T12:00:00+00:00 \
  --end 2026-06-16T13:00:00+00:00 \
  --max-steps 10 \
  --no-paper-simulation
```

## Documentation Index

- [API](docs/api.md)
- [Azure staging](docs/azure_staging.md)
- [Data scaling and DataOps](docs/data_scaling.md)
- [Deployment](docs/deployment.md)
- [Desk workbench](docs/desk_workbench.md)
- [Divergence signals](docs/divergence_signals.md)
- [Equivalence](docs/equivalence.md)
- [Ingestion](docs/ingestion.md)
- [Integrity signals](docs/integrity_signals.md)
- [Market data](docs/market_data.md)
- [Paper execution](docs/paper_execution.md)
- [Pre-trade gate](docs/pretrade_gate.md)
- [Replay](docs/replay.md)
- [Resolution corpus](docs/resolution_corpus.md)
- [Scenario features](docs/scenario_features.md)
- [Strategy research](docs/strategy_research.md)
- [Vendor data evaluation](docs/vendor_data_evaluation.md)

## Development Notes

The system is designed around as-of-safe data. `observed_at` describes when something
happened, while `available_at` controls when replay/research was allowed to know it.
Do not use future data in replay or workbench summaries.

Use structured parsers and deterministic logic. Avoid ad hoc parsing when the standard
library or an existing local helper is available.

When adding new persisted objects, add an Alembic migration and verify both SQLite and
Postgres-compatible behavior.

When adding external datasets, keep raw downloads under `data/vendor_samples/` and commit
only tiny synthetic fixtures or mapping configs under `sample_data/`.
