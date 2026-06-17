# prediction-desk

`prediction-desk` is an institutional-grade prediction-market quant research system.
The focus is point-in-time, reproducible analysis: market rules, prices, scores, and
verdicts are represented as replayable snapshots.

## What This Round Implements

- Typed Pydantic v2 domain models for venues, events, markets, outcomes, rule snapshots,
  order book snapshots, trade prints, resolution events, and trust verdicts.
- Deterministic rule hashing with SHA-256.
- Resolution Corpus v1 for deterministic parsing of rule language, ambiguity scoring,
  evidence spans, and rule snapshot diffs.
- Point-in-Time Replay Harness v1 for admissibility replay using only snapshots available
  at or before each replay timestamp.
- Read-only Kalshi and Polymarket fixture ingestion that archives raw public-shape payloads
  before deterministic normalization.
- Canonical Market Data v1 for orderbook-derived price/liquidity snapshots,
  price-history normalization, data-quality reports, and run-once ingestion scheduling.
- Fast-Lane Integrity Signals v1 for deterministic point-in-time market-integrity
  features, signals, assessments, and integrity-gated replay policy evaluation.
- Cross-Venue Equivalence Engine v1 for deterministic contract comparison before any
  cross-venue research comparison.
- Cross-Venue Divergence Signals v1 for deterministic, equivalence-gated price divergence
  context across comparable contracts.
- Pre-Trade Gate v1 for deterministic admissibility decisions over hypothetical trade
  intents using as-of trust, resolution, market-data, integrity, equivalence, divergence,
  restriction, and abstract exposure context.
- Paper Execution Simulator v1 for clearly labeled simulated orders, fills, ledger,
  position, and portfolio snapshots gated by pre-trade approval and as-of market data.
- Strategy Research Harness v1 for deterministic hypothesis testing, research signals,
  hypothetical intent proposals, pre-trade evaluation, optional paper simulation, and
  simulated attribution summaries.
- Slow-Lane Scenario Feature Interface v1 for fixture-backed MiroFish-style report import,
  scenario seed bundles, normalized scenario feature snapshots, and research/replay
  metadata exposure.
- Data Scale / Historical Backfill / Read-Only Collection Orchestrator v1 for market
  universes, collection plans, run-once fixture collection, historical backfill records,
  coverage reports, and data-gap detection.
- A deterministic v0 resolution-risk scorer.
- A deterministic v0 trust-verdict builder.
- SQLAlchemy 2.0 ORM mappings and repository methods for local persistence.
- Alembic initial migration.
- SQLite default configuration with schema choices that remain Postgres-compatible.
- Typer CLI commands for local setup, sample data, and sample scoring.
- Internal FastAPI service for reading stored markets and recomputing deterministic
  trust verdicts from stored snapshots.
- Dockerfile, Docker Compose Postgres, and GitHub Actions CI.
- Pytest coverage for domain validation, scoring, verdict actions, and persistence roundtrips.

## Intentionally Out Of Scope

This is not a trading bot. This round intentionally excludes:

- Live exchange connectivity.
- External API calls.
- Real order placement.
- Wallets, private keys, custody, or signing.
- API credentials or exchange secrets.
- Execution algorithms.
- Public trading or execution services.
- LLM calls for rule parsing.
- Autonomous scenario simulation.
- Real PnL calculation or unlabeled/fabricated performance metrics.
- Production alpha models or live strategy automation.
- Authenticated venue endpoints or venue credentials.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Test And Quality Commands

```bash
pytest
ruff check .
mypy
```

CI runs on pull requests and pushes to `main`. It installs the package on Python 3.12,
runs ruff, mypy, pytest, and verifies the Alembic migration against SQLite. A separate
`postgres-integration` CI job starts Postgres, runs Alembic against Postgres, and runs
the tests marked `postgres`.

## CLI Examples

Initialize the default local SQLite database:

```bash
prediction-desk init-db
```

Load deterministic sample markets:

```bash
prediction-desk load-sample-data
```

Score the sample markets and print a compact table:

```bash
prediction-desk score-sample-markets
```

Analyze latest rules into the resolution corpus:

```bash
prediction-desk analyze-rules --all
prediction-desk analyze-rules --market-id mkt_sfo_rain_2026_09_01
```

Diff the latest two rule snapshots for the rule-change fixture:

```bash
prediction-desk diff-rule-snapshots --market-id mkt_rate_cut_rule_change_2026
```

Run a small point-in-time replay:

```bash
prediction-desk replay-run \
  --policy trust_verdict_v1 \
  --start 2026-06-16T12:00:00+00:00 \
  --end 2026-06-16T13:00:00+00:00 \
  --interval-seconds 3600 \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --max-steps 10

prediction-desk replay-summary --run-id replay_run_...
prediction-desk replay-steps --run-id replay_run_... --limit 50
```

Ingest committed read-only venue fixtures:

```bash
prediction-desk ingest-fixtures --venue kalshi
prediction-desk ingest-fixtures --venue polymarket
prediction-desk ingestion-runs
prediction-desk venue-mappings
```

Run one fixture ingestion job with market-data derivation and quality reports:

```bash
prediction-desk ingestion-run-once --venue kalshi
prediction-desk ingestion-cursors
```

Derive and inspect canonical market data:

```bash
prediction-desk market-data-derive --all
prediction-desk market-data-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk market-data-prices --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk data-quality --market-id kalshi_market_kxweather_nyc_rain_20260930
```

Analyze fast-lane integrity signals:

```bash
prediction-desk integrity-analyze --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk integrity-run \
  --asof 2026-06-16T12:45:00Z \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --max-steps 10
prediction-desk integrity-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk integrity-signals --market-id kalshi_market_kxweather_nyc_rain_20260930
```

Assess cross-venue contract equivalence:

```bash
prediction-desk ingestion-run-once --venue kalshi
prediction-desk ingestion-run-once --venue polymarket
prediction-desk equivalence-candidates \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --market-id polymarket_market_0xrainnycsep2026 \
  --asof 2026-06-16T12:45:00Z
prediction-desk equivalence-assess \
  --left-market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --right-market-id polymarket_market_0xrainnycsep2026 \
  --asof 2026-06-16T12:45:00Z
prediction-desk equivalence-run \
  --asof 2026-06-16T12:45:00Z \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --market-id polymarket_market_0xrainnycsep2026 \
  --max-pairs 10
prediction-desk equivalence-classes
```

Analyze equivalence-gated divergence context:

```bash
prediction-desk divergence-analyze \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --asof 2026-06-16T12:20:00Z
prediction-desk divergence-run \
  --asof 2026-06-16T12:20:00Z \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --max-pairs 10
prediction-desk divergence-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk divergence-signals --market-id kalshi_market_kxweather_nyc_rain_20260930
```

Evaluate pre-trade admissibility for a hypothetical research intent:

```bash
prediction-desk pretrade-create-default-policy
prediction-desk pretrade-check \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --strategy-context RESEARCH \
  --intent-type RESEARCH_ONLY \
  --requested-size-units 1
prediction-desk pretrade-run \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --asof 2026-06-16T12:20:00Z \
  --max-checks 10
prediction-desk pretrade-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
```

Run simulated-only paper execution:

```bash
prediction-desk paper-create-default-policy
prediction-desk paper-simulate-intent \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --asof 2026-06-16T12:00:00+00:00 \
  --intent-type AGGRESSIVE_LIMIT \
  --requested-price 0.52
prediction-desk paper-position-latest --market-id mkt_cpi_yoy_at_least_3pct_2026_09
prediction-desk paper-portfolio-latest
```

Run deterministic strategy research:

```bash
prediction-desk research-create-default-strategies
prediction-desk research-build-features \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --asof 2026-06-16T12:00:00+00:00
prediction-desk research-generate-signals \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --asof 2026-06-16T12:00:00+00:00
prediction-desk research-generate-proposals \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --strategy-id research_strategy_baseline_research_only_v1 \
  --asof 2026-06-16T12:00:00+00:00
prediction-desk research-run \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --strategy-id research_strategy_baseline_research_only_v1 \
  --start 2026-06-16T12:00:00+00:00 \
  --end 2026-06-16T12:00:00+00:00 \
  --max-steps 10 \
  --max-proposals 10 \
  --no-paper-simulation
```

Import slow-lane scenario features:

```bash
prediction-desk scenario-build-seed \
  --market-id mkt_sfo_rain_2026_09_01 \
  --asof 2026-06-16T12:00:00+00:00
prediction-desk scenario-import-fixtures \
  --market-id mkt_sfo_rain_2026_09_01 \
  --asof 2026-06-16T12:00:00+00:00
prediction-desk scenario-latest --market-id mkt_sfo_rain_2026_09_01
prediction-desk scenario-run \
  --market-id mkt_sfo_rain_2026_09_01 \
  --asof 2026-06-16T12:00:00+00:00
```

Run read-only data scaling checks:

```bash
prediction-desk dataops-defaults
prediction-desk dataops-universes
prediction-desk dataops-collection-plans
prediction-desk dataops-run-collection --venue kalshi --mode FIXTURE
prediction-desk dataops-coverage --scope-type GLOBAL
prediction-desk dataops-gaps
prediction-desk dataops-cycle --mode FIXTURE
```

Manual public sampling is opt-in and read-only:

```bash
prediction-desk dataops-run-collection \
  --venue kalshi \
  --mode MANUAL_PUBLIC_FETCH \
  --allow-network \
  --max-payloads 5
```

Use a custom database URL:

```bash
prediction-desk init-db --database-url sqlite:///local_research.db
```

## API Service

Run the internal API locally against the default SQLite database:

```bash
prediction-desk init-db
prediction-desk load-sample-data
scripts/run_api.sh
```

Useful local endpoints:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl http://localhost:8000/api/v1/markets
curl -X POST \
  http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01/resolution/analyze-latest
curl -X POST \
  http://localhost:8000/api/v1/markets/mkt_rate_cut_rule_change_2026/rule-snapshots/diff-latest
curl -X POST \
  http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01/trust-verdicts/recompute
curl -X POST \
  http://localhost:8000/api/v1/replay/runs \
  -H "Content-Type: application/json" \
  -d '{"name":"sample replay","policy_name":"trust_verdict_v1","start_time":"2026-06-16T12:00:00Z","end_time":"2026-06-16T13:00:00Z","interval_seconds":3600,"market_ids":["mkt_cpi_yoy_at_least_3pct_2026_09"],"max_steps":10,"persist_steps":true,"force_recompute_verdicts":true,"metadata":{}}'
curl -X POST \
  http://localhost:8000/api/v1/ingestion/fixtures/kalshi \
  -H "Content-Type: application/json" \
  -d '{"fixture_dir":null,"captured_at":null,"analyze_rules":true,"recompute_verdicts":true}'
curl -X POST \
  http://localhost:8000/api/v1/ingestion/run-once \
  -H "Content-Type: application/json" \
  -d '{"venue_name":"kalshi","mode":"fixture","limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true,"derive_market_data":true,"compute_quality":true,"metadata":{}}'
curl \
  http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/market-data/latest
curl -X POST \
  http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/integrity/analyze \
  -H "Content-Type: application/json" \
  -d '{"asof_timestamp":"2026-06-16T12:45:00Z","force":false,"thresholds":{}}'
curl -X POST \
  http://localhost:8000/api/v1/equivalence/assess \
  -H "Content-Type: application/json" \
  -d '{"left_market_id":"kalshi_market_kxweather_nyc_rain_20260930","right_market_id":"polymarket_market_0xrainnycsep2026","asof_timestamp":"2026-06-16T12:45:00Z","force":false,"config":{}}'
curl -X POST \
  http://localhost:8000/api/v1/divergence/analyze \
  -H "Content-Type: application/json" \
  -d '{"market_id":"kalshi_market_kxweather_nyc_rain_20260930","asof_timestamp":"2026-06-16T12:20:00Z","force":false,"config":{}}'
curl -X POST \
  http://localhost:8000/api/v1/pretrade/check \
  -H "Content-Type: application/json" \
  -d '{"market_id":"kalshi_market_kxweather_nyc_rain_20260930","strategy_context":"RESEARCH","side":"BUY","intent_type":"RESEARCH_ONLY","requested_size_units":"1","asof_timestamp":"2026-06-16T12:20:00Z","metadata":{}}'
```

Authentication is controlled by `REQUIRE_API_TOKEN` and `PREDICTION_DESK_API_TOKEN`.
`/healthz` is always public. In staging and production, set `REQUIRE_API_TOKEN=true`.
Use `scripts/staging_smoke.sh` for fixture-only staging validation and
`scripts/staging_public_read_pilot.sh` only after explicitly setting
`CONFIRM_PUBLIC_READ_ONLY=true`.

See [docs/api.md](docs/api.md) for endpoint details and
[docs/resolution_corpus.md](docs/resolution_corpus.md) for rule-analysis details. See
[docs/replay.md](docs/replay.md) for point-in-time replay details and
[docs/ingestion.md](docs/ingestion.md) for read-only venue ingestion details. See
[docs/market_data.md](docs/market_data.md) for canonical market-data snapshots,
data-quality reports, timestamp semantics, and run-once scheduling. See
[docs/integrity_signals.md](docs/integrity_signals.md) for fast-lane integrity features,
signals, assessments, trust-verdict integration, and integrity-gated replay. See
[docs/equivalence.md](docs/equivalence.md) for cross-venue contract comparison,
outcome mappings, comparison permissions, and equivalence run-once scans. See
[docs/divergence_signals.md](docs/divergence_signals.md) for equivalence-gated
cross-venue divergence context. See [docs/pretrade_gate.md](docs/pretrade_gate.md) for
intent-only admissibility checks and abstract exposure gating. See
[docs/paper_execution.md](docs/paper_execution.md) for simulated-only paper execution. See
[docs/scenario_features.md](docs/scenario_features.md) for fixture-backed slow-lane
scenario features and research/replay metadata. See [docs/data_scaling.md](docs/data_scaling.md)
for market universes, collection plans, backfill jobs, coverage reports, and gap detection.
See [docs/staging_dataops_pilot.md](docs/staging_dataops_pilot.md) for staging smoke,
public-read pilot, database inspection, coverage/gap readback, and rollback guidance.

## Docker Compose Quickstart

```bash
cp .env.example .env
docker compose build
docker compose up -d postgres
docker compose run --rm migrate
docker compose run --rm app prediction-desk load-sample-data
docker compose up -d app
curl http://localhost:8000/healthz
curl http://localhost:8000/api/v1/markets
```

Run the deterministic Docker smoke path:

```bash
scripts/smoke_docker.sh
```

The smoke path validates Postgres migrations, sample loading, `/healthz`, `/readyz`,
`/api/v1/markets`, run-once fixture ingestion, venue mappings, canonical market data,
data-quality recomputation, dataops defaults/collection/coverage/gaps, resolution analysis, rule diffing, trust-verdict recomputation,
integrity analysis, equivalence scans, divergence scans, integrity/divergence-aware
trust-verdict metadata, pretrade checks, paper policy creation, simulated paper fills,
paper portfolio readback, replay run creation, replay summary readback, replay
market-data/paper/research metadata, default research strategies, research feature and
proposal generation, proposal evaluation, research summaries and attribution,
`integrity_gate_v1`, `pretrade_gate_v1`, `paper_sim_gate_v1`, and `research_policy_v1`.

See [docs/deployment.md](docs/deployment.md) and [deploy/README.md](deploy/README.md)
for staging and production deployment notes.

## Architecture Notes

The system separates canonical domain schemas from persistence records. Pydantic models
represent replayable research artifacts; SQLAlchemy records store those artifacts in a
local relational database. Rule snapshots include deterministic hashes over the rule text,
normalized text, resolution source, settlement authority, and time zone so later backtests
can identify the exact rule version used by a score or verdict.

Resolution Corpus v1 treats rule text as contract data. It preserves raw rule snapshots,
parses deterministic predicates, records evidence spans, scores ambiguity by dimension,
and stores rule diffs for point-in-time replay. The implementation is intentionally
heuristic and deterministic: no LLM calls, no external APIs, and no venue connectivity.

Replay Harness v1 asks what admissibility decision the system would have produced at a
timestamp using only data available at or before that timestamp. It records selected
snapshots, scores, actions, reason codes, and deterministic input/output hashes. It does
not calculate PnL, simulate fills, place orders, or allocate capital.

Read-Only Venue Ingestion v1 archives Kalshi and Polymarket public-shape payloads before
normalization, stores venue-to-canonical mappings, and creates canonical rule snapshots and
orderbooks that resolution analysis, trust verdicts, and replay can consume. Fixture
ingestion is deterministic and network-free; manual public sample fetching is explicit,
GET-only, and credential-free.

Canonical Market Data v1 derives venue-neutral price and liquidity snapshots from stored
orderbooks, normalizes fixture price history where available, and stores quality reports.
Replay-safe lookups use `available_at <= asof_timestamp`; `observed_at` alone never makes a
historical data point usable in replay.

Fast-Lane Integrity Signals v1 derives deterministic risk/admissibility signals from
canonical market data, quality reports, rule snapshots, and rule diffs. It explicitly
labels manipulation-related outputs as heuristic proxies only. Trust verdicts can consume
an as-of integrity assessment, and replay can evaluate the `integrity_gate_v1` policy.

Cross-Venue Equivalence and Divergence v1 first compare contract terms, outcomes,
resolution sources, deadlines, ambiguity, and venue mechanics. Divergence analysis only
runs after that contract-comparison gate and remains research context: it records aligned
price gaps plus stale-data, liquidity, quality, integrity, and equivalence context without
creating trade instructions.

Pre-Trade Gate v1 evaluates hypothetical `TradeIntent` objects and persists the exact
as-of inputs used for the decision. It combines hard restrictions, abstract exposure
limits, trust verdicts, resolution risk, market-data quality, integrity, equivalence, and
divergence context. It never creates venue orders and uses abstract exposure units rather
than real account positions.

Paper Execution Simulator v1 consumes hypothetical intents only after pre-trade approval.
It creates simulated orders, fills, ledger entries, position snapshots, and portfolio
snapshots using stored as-of market data. All position, equity, and mark-to-market fields
are explicitly named simulated and no venue order or real account state is produced.

DataOps v1 organizes read-only data scaling. It builds research universes, validates
collection plans, runs one-shot fixture collection, records unsupported historical
endpoints, computes coverage reports, and persists data gaps. Historical imports preserve
`available_at`; old `observed_at` values are not replay-visible until the imported data is
available to the system.

Scores and verdicts are deterministic. They accept explicit market, rule snapshot, order
book snapshot, and as-of timestamp inputs. The resulting verdict stores model versions,
data versions, source references, reason codes, and risk scores so later analysis can
reconstruct why an action was selected.

Live trading and execution are deliberately absent. The API reads stored artifacts and
recomputes deterministic verdicts from stored snapshots. This service is not an execution
service. No exchange credentials, venue credentials, wallets, private keys, or signing keys
belong in this repository at this stage. Future exchange adapters should write captured
market data into the same point-in-time snapshot model before any research or backtest
consumes it.
