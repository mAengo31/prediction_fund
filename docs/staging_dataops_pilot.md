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

See [azure_staging.md](azure_staging.md) and
[staging_deployment.md](staging_deployment.md) for the Azure deployment blueprint and
first-deploy sequence.

Current Azure staging uses:

- Resource group: `prediction-desk-staging-cus-rg`
- Region: `centralus`
- API: `https://prediction-desk-staging-api.bluebush-22f9863f.centralus.azurecontainerapps.io`

Fixture smoke has passed against this endpoint. Manual public-read pilots require an
Azure budget alert, confirmed backup posture, and `CONFIRM_PUBLIC_READ_ONLY=true`.
Scheduled public-read collection remains held.

## Fixture Staging Smoke

Fixture smoke does not call public venue endpoints:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/azure_staging_smoke.sh
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

If the first catalog/list pilot discovers markets and creates sparse coverage gaps, run
targeted follow-up manually with explicit endpoint types and market IDs:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
PUBLIC_READ_ENDPOINT_TYPES=MARKET_DETAIL,ORDERBOOK \
PUBLIC_READ_MARKET_IDS=kalshi_market_... \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

The targeted shape still calls only the existing DataOps collection endpoint. It does not
schedule collection and does not pass venue credentials. Keep `MAX_PAYLOADS` tiny while
validating coverage/gap changes.

The first targeted Kalshi follow-up used `MARKET_DETAIL,ORDERBOOK` for two discovered
canonical markets. It completed with 4 archived payloads, 2 markets processed, 0 errors,
and coverage improving from `50` to `65`. It created 2 orderbook snapshots, 2 price
snapshots, and 2 liquidity snapshots. The archived `MARKET_DETAIL` payloads had
`rules_primary` and `rules_secondary` keys, but both fields were empty and no
description/resolution/settlement text was present. Missing rule snapshot gaps therefore
remain valid for those two markets. Do not create rule snapshots from title/subtitle text
alone. Public-read scheduling remains held.

A final one-market targeted follow-up covered the remaining Kalshi market with missing
orderbook, price, and liquidity data. It completed with 2 archived payloads, 1 market
processed, 0 errors, and coverage improving from `80` to `88`. Non-rule market-data
coverage is now complete for the current eight-market staging set: orderbooks `8 / 8`,
prices `8 / 8`, and liquidity `8 / 8`. Rule snapshot coverage remains `3 / 8`; the final
detail payload again exposed empty rule fields, so the rule gaps remain valid. Treat this
as a successful manual validation result, not approval to schedule public-read collection.

A matching Polymarket check using `MARKET_DETAIL,ORDERBOOK` for the two current
Polymarket markets completed as `PARTIAL` with 0 archived payloads. The current
fixture-style external market IDs returned `422` from Polymarket Gamma detail, and
targeted Polymarket `ORDERBOOK` is explicitly unsupported in DataOps v1 because the CLOB
book endpoint needs token-level identifiers. Do not repeat this exact shape expecting
coverage changes; add a token-aware read-only mapping first if Polymarket orderbook
coverage needs public follow-up.

Token-aware Polymarket follow-up is now deployed in Azure staging. It stores Gamma market
IDs, condition/question IDs, outcome labels, `enableOrderBook`, and YES/NO CLOB
token/asset IDs in a first-class mapping table. A tiny `MARKET_LIST` discovery pilot
created one real Polymarket market and two active token mappings. A one-market targeted
follow-up then archived one Gamma detail payload and two CLOB orderbook payloads:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=polymarket \
PUBLIC_READ_ENDPOINT_TYPES=MARKET_DETAIL,ORDERBOOK,PRICE_HISTORY \
PUBLIC_READ_MARKET_IDS=polymarket_market_... \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

The run completed as `PARTIAL`: orderbook, price, and liquidity coverage were created for
the selected market, while two public CLOB `PRICE_HISTORY` requests returned `400 Bad
Request` and were recorded as ingestion errors. Treat `PRICE_HISTORY` as not yet validated
for scheduled use. If a selected Polymarket market has no persisted Gamma ID or token
mappings, the collection run should remain `PARTIAL` with a safe missing-identifier error.
Do not fabricate token IDs, orderbook data, or price history, and do not schedule
public-read collection.

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

For migration plus counts in one operator-safe step:

```bash
DATABASE_URL="postgresql+psycopg://..." scripts/azure_migrate_and_verify.sh
```

The helper hides the database URL and does not mutate state beyond Alembic migrations.

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
strategy recommendations. Gap rows are append-only audit records; cumulative gap counts
may increase even when the latest coverage score improves. Use the latest coverage report
to assess current coverage and use gap history to understand what each detection pass
observed.

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

The CLI does not need a `--no-public-fetch` flag for this path; fixture mode plus the
absence of `--allow-network` keeps the cycle network-free.

Only after fixture coverage/gaps look sane, schedule tiny public-read jobs with explicit
operator approval. Keep early runs low-frequency with small `max_payloads`; increase scope
only after collection runs, coverage, and gaps remain explainable.

Do not schedule public-read collection from the current staging state. The next safe
automation step is fixture-only scheduling after budget and backup review.

## Still Prohibited

- Live trading
- Order routing or order placement
- Venue trading credentials
- Wallets or private keys
- Authenticated venue endpoints
- Real account IDs or real user positions
- MiroFish runtime execution
- Background collection daemons
