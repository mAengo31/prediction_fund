# Deployment

## A. Deployment Philosophy

`prediction-desk` is currently a read-only/internal research API. It exposes stored market
artifacts, deterministic resolution-corpus analysis, deterministic trust-verdict scoring,
point-in-time admissibility replay, and read-only fixture/manual-public ingestion for
replayable analysis. It also exposes canonical market-data snapshots, data-quality reports,
fast-lane integrity assessments, and a run-once ingestion scheduler suitable for cron or
deployment jobs. It also exposes deterministic cross-venue equivalence assessments for
contract comparison before any cross-venue research comparison. It also exposes
deterministic cross-venue divergence assessments as research context only after
equivalence permits comparison. DataOps endpoints add read-only market universes,
collection plans, historical backfill records, coverage reports, and gap detection.
The desk workbench endpoints add review queues, decision cards, comparison cards, and
desk notes over stored evidence. Queue history is append-only, while latest queue and
summary endpoints provide the active deduplicated desk view. They do not add execution
authority.

It is not a trading system. This deployment surface intentionally includes no live trading,
no venue credentials, no private keys, no wallets, and no order placement.
Read-only ingestion does not change that boundary; authenticated venue APIs remain out of
scope.

No exchange credentials or private keys belong in this repository at this stage.
Replay is admissibility research only. It does not calculate PnL, simulate execution, or
place orders. Equivalence and divergence are research metadata only; they do not compute
execution, EV, or trading instructions.

## B. Local Docker Compose

Build the containers:

```bash
docker compose build
```

Run Postgres and the API:

```bash
cp .env.example .env
docker compose up -d postgres
```

If local port `5432` is already in use, set `POSTGRES_PORT` in `.env` before starting
Compose.

Run migrations:

```bash
docker compose run --rm migrate
```

Load sample data:

```bash
docker compose run --rm app prediction-desk load-sample-data
docker compose up -d app
```

Call health endpoints:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

Call sample endpoints:

```bash
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
  http://localhost:8000/api/v1/ingestion/run-once \
  -H "Content-Type: application/json" \
  -d '{"venue_name":"kalshi","mode":"fixture","limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true,"derive_market_data":true,"compute_quality":true,"metadata":{}}'
curl http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/market-data/latest
curl -X POST \
  http://localhost:8000/api/v1/equivalence/assess \
  -H "Content-Type: application/json" \
  -d '{"left_market_id":"kalshi_market_kxweather_nyc_rain_20260930","right_market_id":"polymarket_market_0xrainnycsep2026","asof_timestamp":"2026-06-16T12:45:00Z","force":false,"config":{}}'
curl -X POST \
  http://localhost:8000/api/v1/divergence/analyze \
  -H "Content-Type: application/json" \
  -d '{"market_id":"kalshi_market_kxweather_nyc_rain_20260930","asof_timestamp":"2026-06-16T12:20:00Z","force":false,"config":{}}'
```

Run the full Docker smoke path. It validates Postgres startup, Alembic migrations, sample
loading, `/healthz`, `/readyz`, `/api/v1/markets`, resolution analysis, rule diffing,
run-once fixture ingestion, venue mappings, canonical market data, data-quality reports,
dataops defaults/universes/fixture collection/backfill coverage/gaps, integrity analysis,
integrity-aware trust-verdict recomputation, replay run creation,
equivalence candidate generation, equivalence assessment/classes, divergence analysis and
runs, pretrade checks, simulated paper execution, paper portfolio readback, deterministic
research strategies, scenario fixture import, scenario feature readback, research
feature/proposal generation, proposal evaluation, research summary and attribution
readback, replay summary readback, replay
market-data/equivalence/divergence/paper/research metadata, and the `integrity_gate_v1`,
`pretrade_gate_v1`, `paper_sim_gate_v1`, and `research_policy_v1` replay policies:

```bash
scripts/smoke_docker.sh
```

Run the standard test suite locally:

```bash
python -m pytest
```

Run against the Docker Compose Postgres database for manual migration checks:

```bash
docker compose up -d postgres
DATABASE_URL=postgresql+psycopg://prediction_desk:prediction_desk@localhost:5432/prediction_desk \
  scripts/migrate.sh
```

Run optional Postgres-backed tests:

```bash
TEST_DATABASE_URL=postgresql+psycopg://prediction_desk:prediction_desk@localhost:5432/prediction_desk \
  python -m pytest -m postgres
```

CI runs the normal SQLite/unit path and a separate `postgres-integration` job. The Postgres
job starts a service container, runs Alembic against Postgres, and then runs tests marked
`postgres`.

## C. Staging Deployment Target

Use Microsoft Azure for staging:

- Azure Container Apps for the FastAPI API.
- Azure Database for PostgreSQL Flexible Server for persistent staging data.
- Azure Container Registry for the Docker image.
- Azure Container Apps Jobs for optional fixture-only DataOps validation.
- Azure Container Apps secrets for immediate staging secrets.

Staging settings:

- Store `PREDICTION_DESK_API_TOKEN` as a platform secret or environment variable.
- Set `APP_ENV=staging`.
- Set `REQUIRE_API_TOKEN=true`.
- Set `ENABLE_OPENAPI_DOCS=false` unless intentionally exposing docs.
- Set `DATABASE_URL` to a managed Postgres connection string.
- Set `GIT_COMMIT` during image build or release.

Use the Azure deployment packet in [../deploy/azure](../deploy/azure). It contains
placeholders only; configure secrets in Azure, GitHub Actions secrets, or the operator shell.
The Container Apps command is:

```bash
uvicorn prediction_desk.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

Deploy only with explicit confirmation:

```bash
CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

Run migrations against staging before smoke:

```bash
DATABASE_URL="postgresql+psycopg://..." scripts/azure_migrate_and_verify.sh
```

Run fixture-only Azure staging smoke without printing secrets:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/azure_staging_smoke.sh
```

Run the desk workbench staging smoke after migrations:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/staging_workbench_smoke.sh
```

The workbench smoke builds review artifacts only. It does not call public-read endpoints
or add execution authority.

Run the fuller desk-analysis cycle over existing staging data:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/staging_desk_cycle.sh
```

The desk cycle may create integrity, equivalence, divergence, pretrade, simulated paper,
research, workbench, and desk-note artifacts from stored staging data. It does not call
public-read collection and does not enable trading.

Read the daily active workbench status without running analysis:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/staging_workbench_status.sh
```

Queue review status updates are review metadata only. They can mark items `IN_REVIEW`,
`WATCHING`, `RESOLVED`, or `DISMISSED` and optionally create a linked desk note. They do
not mutate market data, place orders, or enable execution.

Run the tiny public-read pilot only after explicit approval:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

Inspect staging counts without mutating state:

```bash
DATABASE_URL="postgresql+psycopg://..." scripts/azure_inspect_counts.sh
```

Use PostgreSQL Flexible Server backups and Azure Cost Management budgets before public-read
pilots. The pilot script sends no venue credentials and refuses to run unless
`CONFIRM_PUBLIC_READ_ONLY=true`. See [azure_staging.md](azure_staging.md),
[staging_deployment.md](staging_deployment.md), and
[staging_dataops_pilot.md](staging_dataops_pilot.md) for the full operational runbooks.

If a scheduled validation job is enabled later, use fixture mode only:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Create or update the Azure fixture-only schedule only after explicit confirmation:

```bash
CONFIRM_ENABLE_FIXTURE_SCHEDULE=true \
DATABASE_URL="postgresql+psycopg://..." \
scripts/azure_enable_fixture_schedule.sh
```

Disable it with:

```bash
CONFIRM_DISABLE_FIXTURE_SCHEDULE=true scripts/azure_disable_fixture_schedule.sh
```

The helper does not schedule public-read collection, does not pass `--allow-network`, and
does not require venue credentials.

Do not schedule public-read collection during this staging phase.

## D. Production Research Deployment Target

The production research target should be:

- AWS ECS/Fargate service.
- RDS Postgres.
- Secrets Manager for tokens and database credentials.
- Private networking/VPC.
- Centralized logs and metrics.
- No public write access.
- No live execution service in this API.
- No venue adapters or live exchange calls in this API.
- No authenticated venue adapters or live trading calls in this API.
- No background ingestion daemon in this API; use explicit run-once jobs for fixture or
  manual public sample ingestion.
- Paper execution endpoints are simulated-only and must remain disconnected from venue
  order routing and real account state.
- No integrity signal should be interpreted as an alpha claim or proof of manipulation.
- No equivalence or divergence assessment should be interpreted as a trading instruction.
- Pre-trade gate endpoints evaluate hypothetical intents only; they must not be connected
  directly to venue order routing or real account state.
- Strategy research endpoints generate hypotheses, proposals, traces, and simulated
  attribution only; they must continue to depend on the pre-trade gate and simulated paper
  layer rather than live venue access.
- DataOps endpoints are read-only collection and coverage controls. Manual public fetch
  requires explicit `allow_network=true`; no credentials are accepted.

Bearer-token auth is temporary. Replace it with stronger service authentication or SSO before
real production use.

## E. Access Model

- Local: localhost.
- Staging: token-protected HTTPS endpoint.
- Production research: private/internal endpoint behind VPN/SSO or private networking.
- Future UI clients should call this API and should not bypass it by reading database tables
  directly.

## F. Out Of Scope For Deployment

- Live execution services.
- Exchange credentials.
- Wallet custody.
- Trading keys.
- Autonomous order placement.
- Live venue adapters.
- Authenticated Kalshi or Polymarket endpoints.
- LLM-backed rule parsing.
- Scenario simulation workers.
- PnL attribution.
- Strategy research automation connected to live venues.
- Cross-venue execution or spread trading.
- Real pre-trade account exposure from venue accounts.

This service remains a replayable research API, not an execution service.
