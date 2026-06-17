# Staging Deployment

This guide prepares the first safe staging deployment for prediction-desk. Staging is a
read-only, non-executing research API backed by persistent Postgres. It must not include
live trading, order routing, venue trading credentials, wallets, private keys, real account
IDs, real positions, MiroFish runtime execution, LLM calls, or background trading jobs.

## Target Shape

The default target is a Render-style managed container deployment:

- Docker web service built from `Dockerfile`.
- Managed Postgres attached through `DATABASE_URL`.
- Bearer-token API auth enabled.
- OpenAPI docs disabled by default.
- Migrations run explicitly with `scripts/migrate.sh` or
  `scripts/staging_migrate_and_verify.sh`.
- Fixture-only DataOps validation runs before any public-read pilot.

The web service command is:

```bash
uvicorn prediction_desk.api.app:create_app --factory --host 0.0.0.0 --port "$PORT"
```

## Required Environment Variables

Set these in the platform secret/config UI. Do not commit or print real values:

```bash
APP_ENV=staging
REQUIRE_API_TOKEN=true
ENABLE_OPENAPI_DOCS=false
DATABASE_URL=<managed Postgres internal URL>
PREDICTION_DESK_API_TOKEN=<platform secret>
LOG_LEVEL=INFO
```

Optional release metadata:

```bash
APP_VERSION=<git sha or release tag>
GIT_COMMIT=<git sha>
```

Use [../deploy/staging.env.example](../deploy/staging.env.example) as a checklist only.

## Render-Style Blueprint

`deploy/render.yaml` defines:

- `prediction-desk-api` web service using the Dockerfile.
- `prediction-desk-postgres` managed Postgres.
- Required staging env vars.
- A commented fixture-only cron template.

The fixture cron is intentionally commented. Uncomment it only after staging fixture smoke
passes, backups are confirmed, and an operator approves a low-frequency validation job.
The safe fixture command is:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Do not schedule public-read collection in this round.

If the Render CLI is authenticated, validate the blueprint before applying it:

```bash
render blueprints validate deploy/render.yaml --output json
```

The CLI requires an authenticated Render workspace for semantic validation.

## Migration

Run migrations as an explicit release step:

```bash
DATABASE_URL="<staging database url>" scripts/staging_migrate_and_verify.sh
```

The helper hides the URL, runs `scripts/migrate.sh`, and then prints read-only table
counts unless `SKIP_DB_COUNTS=true`.

Equivalent direct command:

```bash
DATABASE_URL="<staging database url>" scripts/migrate.sh
```

No deletion or compaction is performed by the migration helper.

## Fixture Smoke

After deploy and migration:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="<token from platform secret>" \
scripts/staging_smoke.sh
```

The script calls health, readiness, market listing, DataOps defaults, universes, collection
plans, fixture collection, coverage, gap detection, and coverage/gap readback. It uses the
bearer token when provided and does not print it.

## DB Counts

If the staging database URL is available to the operator shell:

```bash
DATABASE_URL="<staging database url>" python scripts/inspect_db_counts.py
DATABASE_URL="<staging database url>" python scripts/inspect_db_counts.py --json
```

This script is read-only.

## Coverage And Gaps

Use API readback:

```bash
curl -fsS -H "Authorization: Bearer ${PREDICTION_DESK_API_TOKEN}" \
  "${API_BASE_URL}/api/v1/dataops/coverage"
curl -fsS -H "Authorization: Bearer ${PREDICTION_DESK_API_TOKEN}" \
  "${API_BASE_URL}/api/v1/dataops/gaps"
```

Coverage and gaps are operational evidence. They do not produce trade instructions or
execution authority.

## Backup Check

Before public-read pilots or scheduled fixture jobs, confirm managed Postgres backups are
enabled in the platform dashboard. Record the backup status in the deployment notes.

## Manual Public-Read Pilot

Public-read collection remains manual only. Run it only after all conditions are true:

- Deployed staging API exists.
- Managed Postgres is attached.
- Migrations succeeded.
- Fixture smoke passed.
- Backups are confirmed, or the operator explicitly accepts the risk.
- `CONFIRM_PUBLIC_READ_ONLY=true` is set.

Command:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="<token from platform secret>" \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

The pilot sends no venue credentials and calls only DataOps `MANUAL_PUBLIC_FETCH` with
`allow_network=true`.

## Rollback

1. Stop optional fixture cron jobs.
2. Roll back the web service image/release.
3. Keep Postgres intact.
4. Restore from backup only if a migration or operator action corrupted staging data.

## Prohibited In Staging

- Live trading
- Order placement or cancellation
- Order routing
- Authenticated venue trading endpoints
- Venue credentials
- Wallets or private keys
- Real account IDs or real positions
- Public-read scheduled collection
- MiroFish runtime execution
- LLM calls
