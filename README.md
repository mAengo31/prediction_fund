# prediction-desk

`prediction-desk` is an institutional-grade prediction-market quant research system.
The focus is point-in-time, reproducible analysis: market rules, prices, scores, and
verdicts are represented as replayable snapshots.

## What This Round Implements

- Typed Pydantic v2 domain models for venues, events, markets, outcomes, rule snapshots,
  order book snapshots, trade prints, resolution events, and trust verdicts.
- Deterministic rule hashing with SHA-256.
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
  http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01/trust-verdicts/recompute
```

Authentication is controlled by `REQUIRE_API_TOKEN` and `PREDICTION_DESK_API_TOKEN`.
`/healthz` is always public. In staging and production, set `REQUIRE_API_TOKEN=true`.

See [docs/api.md](docs/api.md) for endpoint details.

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

See [docs/deployment.md](docs/deployment.md) and [deploy/README.md](deploy/README.md)
for staging and production deployment notes.

## Architecture Notes

The system separates canonical domain schemas from persistence records. Pydantic models
represent replayable research artifacts; SQLAlchemy records store those artifacts in a
local relational database. Rule snapshots include deterministic hashes over the rule text,
normalized text, resolution source, settlement authority, and time zone so later backtests
can identify the exact rule version used by a score or verdict.

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
