# Staging DataOps Pilot Runbook

This runbook covers the first controlled staging deployment and read-only collection
pilot for prediction-desk. The goal is operational evidence: API health, migrations,
fixture collection, coverage, gaps, and small public-read failure modes when explicitly
enabled.

This is not a trading deployment. Do not add order routing, venue credentials, wallets,
private keys, real account IDs, MiroFish runtime execution, or background daemons.

## Required Environment

For API smoke scripts:

```bash
export API_BASE_URL="https://your-staging-api.example.com"
export PREDICTION_DESK_API_TOKEN="..."
```

`PREDICTION_DESK_API_TOKEN` is optional for local unauthenticated staging smoke, but staging
should normally run with `REQUIRE_API_TOKEN=true`. Scripts never print the token.

For the public-read pilot:

```bash
export CONFIRM_PUBLIC_READ_ONLY=true
export PUBLIC_READ_VENUES=kalshi
export MAX_PAYLOADS=5
```

`CONFIRM_PUBLIC_READ_ONLY` must be exactly `true`. `MAX_PAYLOADS` is restricted to 1-10 by
the pilot script.

## Deploy Staging API

Use the containerized app with persistent managed Postgres:

```bash
docker compose build
docker compose up -d postgres
DATABASE_URL="postgresql+psycopg://..." scripts/migrate.sh
```

For hosted staging, set:

- `APP_ENV=staging`
- `DATABASE_URL` to managed Postgres
- `REQUIRE_API_TOKEN=true`
- `PREDICTION_DESK_API_TOKEN` as a platform secret
- `ENABLE_OPENAPI_DOCS=false` unless intentionally exposing docs
- `GIT_COMMIT` during build or release

Enable automated database backups before running collection pilots.

## Fixture Staging Smoke

Fixture smoke does not call public venue endpoints:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/staging_smoke.sh
```

The script calls health/readiness, market listing, DataOps defaults, universes, collection
plans, fixture collection, coverage compute, gap detection, and coverage/gap readback. It
prints compact counts and IDs only.

## Public-Read-Only Pilot

Run this only after fixture staging smoke passes and an operator explicitly approves a
small public-read sample:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

The script sends no venue credentials. It calls only the DataOps collection endpoint in
`MANUAL_PUBLIC_FETCH` mode with `allow_network=true`, then reads back the collection run,
computes coverage, detects gaps, and prints compact counts.

If public fetch is unsupported or unavailable, keep fixture staging as the validated path
and record the failure mode in validation notes.

## Inspect Database Counts

`scripts/inspect_db_counts.py` is read-only and works with `DATABASE_URL` or
`--database-url`:

```bash
DATABASE_URL="postgresql+psycopg://..." python scripts/inspect_db_counts.py
DATABASE_URL="postgresql+psycopg://..." python scripts/inspect_db_counts.py --json
```

It reports major domain, ingestion, market-data, research, replay, and DataOps table
counts, including raw payloads, collection runs, coverage reports, and data gaps.

## Read Coverage And Gap Reports

Use API endpoints:

```bash
curl -fsS -H "Authorization: Bearer ${PREDICTION_DESK_API_TOKEN}" \
  "${API_BASE_URL}/api/v1/dataops/coverage"
curl -fsS -H "Authorization: Bearer ${PREDICTION_DESK_API_TOKEN}" \
  "${API_BASE_URL}/api/v1/dataops/gaps"
```

Use CLI for local/staging shells with database access:

```bash
prediction-desk dataops-coverage --scope-type GLOBAL
prediction-desk dataops-gaps
```

Coverage and gaps are measurement artifacts. They do not create execution authority or
strategy recommendations.

## Rollback

Rollback is the normal deployment rollback path:

1. Stop scheduled run-once jobs.
2. Revert the app image to the previous known-good release.
3. Keep the Postgres database intact.
4. Restore from backup only if a migration or operator action corrupted staging data.

DataOps v1 does not delete or compact data. Retention policies are reporting-only.

## Secret Hygiene

- Do not echo API tokens.
- Do not run scripts with shell tracing enabled.
- Store tokens in platform secrets or a local environment manager, not in git.
- Do not put venue credentials in environment variables; they are not required.

## Scheduling Recommendation

Start with low-frequency fixture jobs for staging validation:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Only after fixture coverage/gaps look sane, schedule tiny public-read jobs with explicit
operator approval. Keep early runs low-frequency with small `max_payloads`; increase scope
only after collection runs, coverage, and gaps remain explainable.

## Still Prohibited

- Live trading
- Order routing or order placement
- Venue trading credentials
- Wallets or private keys
- Authenticated venue endpoints
- Real account IDs or real user positions
- MiroFish runtime execution
- Background collection daemons
