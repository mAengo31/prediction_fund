# Deployment

## A. Deployment Philosophy

`prediction-desk` is currently a read-only/internal research API. It exposes stored market
artifacts and deterministic trust-verdict scoring for replayable analysis.

It is not a trading system. This deployment surface intentionally includes no live trading,
no venue credentials, no private keys, no wallets, and no order placement.

## B. Local Docker Compose

Build the containers:

```bash
docker compose build
```

Run Postgres and the API:

```bash
docker compose up -d postgres app
```

Run migrations:

```bash
docker compose run --rm app scripts/migrate.sh
```

Load sample data:

```bash
docker compose run --rm app prediction-desk load-sample-data
```

Call health endpoints:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

Call sample endpoints:

```bash
curl http://localhost:8000/markets
curl -X POST \
  http://localhost:8000/markets/mkt_sfo_rain_2026_09_01/trust-verdicts/recompute
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

## C. Staging Deployment Recommendation

Use a containerized deployment for staging. Render is acceptable for low-friction staging.
Fly.io is acceptable for app runtime, but prefer managed Postgres elsewhere unless you are
deliberately choosing unmanaged Postgres.

Recommended staging settings:

- Store `PREDICTION_DESK_API_TOKEN` as a platform secret or environment variable.
- Set `APP_ENV=staging`.
- Set `REQUIRE_API_TOKEN=true`.
- Set `ENABLE_OPENAPI_DOCS=false` unless intentionally exposing docs.
- Set `DATABASE_URL` to a managed Postgres connection string.
- Set `GIT_COMMIT` during image build or release.

## D. Production Research Deployment Target

The production research target should be:

- AWS ECS/Fargate service.
- RDS Postgres.
- Secrets Manager for tokens and database credentials.
- Private networking/VPC.
- Centralized logs and metrics.
- No public write access.

Bearer-token auth is temporary. Replace it with stronger service authentication or SSO before
real production use.

## E. Access Model

- Local: localhost.
- Staging: token-protected HTTPS endpoint.
- Production research: private/internal endpoint behind VPN/SSO or private networking.
- Future UI clients should call this API and should not bypass it by reading database tables
  directly.

## F. Out Of Scope For Deployment

- Execution services.
- Exchange credentials.
- Wallet custody.
- Trading keys.
- Autonomous order placement.
- Live venue adapters.
