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

## Azure Staging Deployment

Azure is the current staging target:

- Azure Container Apps for the FastAPI API.
- Azure Database for PostgreSQL Flexible Server for persistent staging data.
- Azure Container Registry for the Docker image.
- Azure Container Apps Jobs for optional fixture-only DataOps validation.
- Azure Container Apps secrets for immediate staging secrets.

Use:

- [azure/main.bicep](azure/main.bicep)
- [azure/parameters.staging.json.example](azure/parameters.staging.json.example)
- [azure/staging.env.example](azure/staging.env.example)
- [azure/commands.md](azure/commands.md)

Deploy only with explicit confirmation:

```bash
CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

Run migrations and fixture smoke:

```bash
DATABASE_URL="postgresql+psycopg://..." scripts/azure_migrate_and_verify.sh
API_BASE_URL="https://<container-app-fqdn>" scripts/azure_staging_smoke.sh
```

The safe optional fixture validation job command is:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Do not configure venue credentials in staging. Do not schedule public-read collection.
Public-read pilot remains manual and requires `CONFIRM_PUBLIC_READ_ONLY=true`.

See [../docs/azure_staging.md](../docs/azure_staging.md),
[../docs/staging_deployment.md](../docs/staging_deployment.md), and
[../docs/staging_dataops_pilot.md](../docs/staging_dataops_pilot.md) for the operator
runbooks.

## Legacy Render Template

`deploy/render.yaml` remains only as a legacy safe template. Azure is the active staging
target. Do not use the Render template unless the staging target changes again.

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
