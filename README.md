# prediction-desk

`prediction-desk` is the first commit of an institutional-grade prediction-market
quant research system. The focus is point-in-time, reproducible analysis: market
rules, prices, scores, and verdicts are represented as replayable snapshots.

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
- Pytest coverage for domain validation, scoring, verdict actions, and persistence roundtrips.

## Intentionally Out Of Scope

This is not a trading bot. This round intentionally excludes:

- Live exchange connectivity.
- External API calls.
- Real order placement.
- Wallets, private keys, custody, or signing.
- API credentials or exchange secrets.
- Execution algorithms.
- Production deployment.

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

Live trading and execution are deliberately absent. Future exchange adapters should write
captured market data into the same point-in-time snapshot model before any research or
backtest consumes it.
