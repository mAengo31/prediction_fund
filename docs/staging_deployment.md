# Staging Deployment

The current staging target is Microsoft Azure. Use Azure Container Apps for the API, Azure
Database for PostgreSQL Flexible Server for persistent data, Azure Container Registry for
the image, and optional Azure Container Apps Jobs for fixture-only DataOps validation.

This staging environment is read-only and non-executing. It must not include live trading,
order routing, venue credentials, wallets, private keys, real account IDs, real positions,
MiroFish runtime execution, LLM calls, or public-read schedules.

## Azure Deployment Packet

Use [azure_staging.md](azure_staging.md) for the full operator runbook.

Azure deployment files:

- [../deploy/azure/main.bicep](../deploy/azure/main.bicep)
- [../deploy/azure/parameters.staging.json.example](../deploy/azure/parameters.staging.json.example)
- [../deploy/azure/staging.env.example](../deploy/azure/staging.env.example)
- [../deploy/azure/commands.md](../deploy/azure/commands.md)

Azure helper scripts:

- `scripts/azure_deploy_staging.sh`
- `scripts/azure_build_push.sh`
- `scripts/azure_migrate_and_verify.sh`
- `scripts/azure_staging_smoke.sh`
- `scripts/azure_inspect_counts.sh`

## Required Runtime Environment

```bash
APP_ENV=staging
REQUIRE_API_TOKEN=true
ENABLE_OPENAPI_DOCS=false
DATABASE_URL=<managed Postgres URL>
PREDICTION_DESK_API_TOKEN=<secret>
LOG_LEVEL=INFO
APP_VERSION=<optional>
GIT_COMMIT=<optional>
```

Do not commit or print real values.

## Deployment Sequence

```bash
az login
az account set --subscription "<subscription id>"
export AZURE_RESOURCE_GROUP=prediction-desk-staging-cus-rg
export AZURE_LOCATION=centralus
export AZURE_CONTAINER_REGISTRY=predictiondesk3bbbab44cusacr
export AZURE_CONTAINER_APP_NAME=prediction-desk-staging-api
export AZURE_POSTGRES_SERVER_NAME=prediction-desk-staging-pg-cus-3bbbab
export AZURE_POSTGRES_ADMIN_PASSWORD="<secret>"
export PREDICTION_DESK_API_TOKEN="<secret>"
export IMAGE_TAG="$(git rev-parse --short HEAD)"
CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

Run migrations:

```bash
export DATABASE_URL="postgresql+psycopg://predictiondeskadmin:<encoded-password>@<server>.postgres.database.azure.com:5432/prediction_desk?sslmode=require"
scripts/azure_migrate_and_verify.sh
```

Run fixture smoke:

```bash
export API_BASE_URL="https://<container-app-fqdn>"
scripts/azure_staging_smoke.sh
```

Inspect counts:

```bash
scripts/azure_inspect_counts.sh
```

## Fixture Job

The safe validation job is:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Enable the optional Azure Container Apps Job only after fixture smoke and backup checks
pass:

```bash
DEPLOY_FIXTURE_DATAOPS_JOB=true CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

## Public-Read Pilot

Do not schedule public-read collection. The manual pilot requires:

```bash
CONFIRM_PUBLIC_READ_ONLY=true MAX_PAYLOADS=5 scripts/staging_public_read_pilot.sh
```

Run it only after staging deploy, migrations, fixture smoke, and backup confirmation.

## Legacy Render Template

`deploy/render.yaml` remains in the repo as a legacy template, but Azure is now the active
staging target.
