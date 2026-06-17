# Deployment Templates

These files are safe deployment templates for the internal `prediction-desk` research API.
They intentionally contain no exchange credentials, no private keys, no wallet material, and
no trading secrets.

## Local Docker Compose

Use Docker Compose for local end-to-end Postgres validation:

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

Or run the deterministic smoke path:

```bash
scripts/smoke_docker.sh
```

## Staging Render-Style Deployment

`deploy/render.yaml` is a template for a low-friction staging deployment:

- Web service runs the Docker image.
- Managed Postgres is referenced through `DATABASE_URL`.
- `PREDICTION_DESK_API_TOKEN` is marked as a secret placeholder.
- `REQUIRE_API_TOKEN=true`.
- `ENABLE_OPENAPI_DOCS=false`.
- Public-read collection is not scheduled.
- The optional fixture-only cron template is commented until an operator enables it.

Run migrations as an explicit release/manual command:

```bash
DATABASE_URL="postgresql+psycopg://..." scripts/staging_migrate_and_verify.sh
```

Run fixture staging smoke after deployment:

```bash
API_BASE_URL="https://your-staging-api.example.com" \
PREDICTION_DESK_API_TOKEN="..." \
scripts/staging_smoke.sh
```

The safe scheduled validation command, if later enabled, is:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Do not configure venue credentials in staging for this project stage. Do not schedule
public-read collection. Public-read pilot remains manual and requires
`CONFIRM_PUBLIC_READ_ONLY=true`.

See [../docs/staging_deployment.md](../docs/staging_deployment.md) and
[../docs/staging_dataops_pilot.md](../docs/staging_dataops_pilot.md) for the operator
runbooks.

If the Render CLI is authenticated, validate the blueprint before applying it:

```bash
render blueprints validate deploy/render.yaml --output json
```

## Production Research Target

The intended production research shape is:

- AWS ECS/Fargate for the API container.
- RDS Postgres.
- AWS Secrets Manager for API token and database credentials.
- Private networking/VPC.
- Internal load balancer or private endpoint.
- Centralized logs and metrics.

Bearer-token auth is a temporary staging mechanism. Replace it with SSO, service-to-service
auth, or another managed identity boundary before production research use.

## Access Model

- Local: localhost only.
- Staging: token-protected HTTPS endpoint.
- Production research: private/internal endpoint over VPN, SSO, or private networking.
- Future UI clients should call this API and should not bypass it with direct database access.

## What Remains Private

Keep these out of the repository and out of images:

- API tokens.
- Database passwords.
- Cloud credentials.
- Exchange credentials.
- Wallet keys or seed material.
- Private signing keys.

## Non-Trading Boundary

This service is not an execution service. It exposes stored canonical data, deterministic
resolution analysis, trust-verdict recomputation, and point-in-time admissibility replay.
It also supports read-only fixture/manual-public ingestion for archived public market data.
It also exposes canonical market data, integrity assessments, contract equivalence, and
equivalence-gated divergence context as research artifacts only. It must not place orders,
create wallets, hold keys, call venue trading APIs, calculate PnL, or run LLM-backed rule
parsing in this stage.
