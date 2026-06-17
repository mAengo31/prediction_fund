# Staging Pilot Validation

Validation date: 2026-06-17

Validated checkpoint: `59cf2d0` (`dataops-v1`)

Working tree note: Round 14 was clean and tagged before this staging pilot hardening
round. This document and the staging scripts are Round 15 changes and were not committed at
the time of validation.

## Commands Run

```bash
git status --short
git log -1 --oneline
git tag --points-at HEAD
bash -n scripts/staging_smoke.sh scripts/staging_public_read_pilot.sh
python -m pytest
python -m ruff check .
python -m mypy
git diff --check
DATABASE_URL=sqlite:////tmp/prediction_desk_staging_pilot_migration.db scripts/migrate.sh
docker compose config
scripts/smoke_local.sh
API_BASE_URL=http://127.0.0.1:8011 scripts/staging_smoke.sh
scripts/smoke_docker.sh
TEST_DATABASE_URL=postgresql+psycopg://prediction_desk:prediction_desk@localhost:55432/prediction_desk python -m pytest -m postgres
DATABASE_URL=sqlite:////tmp/prediction_desk_smoke_local.db python scripts/inspect_db_counts.py --json
```

`scripts/staging_public_read_pilot.sh` was also run without
`CONFIRM_PUBLIC_READ_ONLY=true`; it exited without making public-read requests.

## Results

- Full pytest: `288 passed, 5 skipped`
- Ruff: passed
- Mypy: passed
- Diff whitespace: passed
- SQLite migration: passed through `20260617_0013`
- Docker Compose config: passed
- Local smoke: passed
- Docker smoke: passed
- Postgres tests: `5 passed, 288 deselected`
- Local staging smoke script validation: passed against `http://127.0.0.1:8011`
- Real staging smoke: not run; `API_BASE_URL` was not configured
- Public-read pilot: not run; `CONFIRM_PUBLIC_READ_ONLY` was not set to `true`

## Database Count Summary

Counts from `/tmp/prediction_desk_smoke_local.db` after local smoke and local staging
smoke:

| Table | Count |
| --- | ---: |
| venues | 3 |
| events | 8 |
| markets | 8 |
| outcomes | 16 |
| raw_venue_payloads | 11 |
| market_rule_snapshots | 9 |
| orderbook_snapshots | 14 |
| market_price_snapshots | 6 |
| market_liquidity_snapshots | 5 |
| market_data_quality_reports | 14 |
| integrity_assessments | 1 |
| market_equivalence_assessments | 1 |
| cross_venue_divergence_assessments | 1 |
| pretrade_decisions | 9 |
| paper_orders | 4 |
| paper_fills | 1 |
| paper_position_snapshots | 1 |
| paper_portfolio_snapshots | 4 |
| research_strategy_definitions | 6 |
| research_feature_snapshots | 10 |
| research_signals | 3 |
| research_intent_proposals | 1 |
| research_decision_traces | 2 |
| research_runs | 1 |
| replay_runs | 5 |
| market_universe_definitions | 4 |
| market_universe_members | 8 |
| collection_plans | 4 |
| collection_runs | 4 |
| backfill_jobs | 1 |
| backfill_segments | 1 |
| data_coverage_reports | 2 |
| data_gaps | 36 |

## Coverage And Gaps

Latest local coverage report:

- `coverage_score=62`
- `total_markets=8`
- `missing_price_markets=5`
- `missing_liquidity_markets=5`

Gap counts:

- `MISSING_LIQUIDITY_SNAPSHOT`: 10
- `MISSING_PRICE_SNAPSHOT`: 10
- `MISSING_QUALITY_REPORT`: 13
- `STALE_MARKET_DATA`: 3

These gaps are expected for the compact fixture corpus and demonstrate that missing
coverage is measured rather than fabricated.

## Bug Found And Fixed

The first local run of `scripts/staging_smoke.sh` returned HTTP 422 on the fixture
collection request. Root cause: Bash parsed `${payload:-{}}` as a default `{` plus a
literal `}`, appending an extra closing brace to every POST payload. Both staging scripts
now use an explicit empty-payload assignment before passing `-d "${payload}"`.

## Known Limitations

- No real staging API URL was available in this shell, so staging smoke was validated only
  against a local API instance.
- The public-read pilot was not executed because explicit confirmation was not present.
- Fixture coverage remains intentionally sparse; the gaps are useful operational evidence,
  not a production coverage target.
- DataOps remains run-once only. There is no daemon.

## Recommendation

Proceed to staging fixture smoke on the deployed API once `API_BASE_URL` and the API token
are available. Hold scheduled public-read collection until fixture staging smoke passes on
the deployed environment, database backups are confirmed, and an operator explicitly
enables a tiny `MAX_PAYLOADS` public-read pilot.
