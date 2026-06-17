# Azure Staging

Azure staging is a read-only, non-executing research environment for prediction-desk. It
must not include live trading, order routing, venue trading credentials, wallets, private
keys, real account IDs, real positions, MiroFish runtime execution, LLM calls, or public-read
collection schedules.

## Current Staging Deployment

The first Azure staging deployment is active in:

- Resource group: `prediction-desk-staging-cus-rg`
- Region: `centralus`
- API: `https://prediction-desk-staging-api.bluebush-22f9863f.centralus.azurecontainerapps.io`
- PostgreSQL Flexible Server: `prediction-desk-staging-pg-cus-3bbbab`
- ACR: `predictiondesk3bbbab44cusacr`

Alembic migrations have passed through revision `20260617_0013`, and fixture staging smoke
has passed. Public-read collection has not been run. Failed partial resource groups from
restricted-region attempts, `prediction-desk-staging-rg` and
`prediction-desk-staging-wus2-rg`, should be deleted after explicit operator approval.

Current hardening status:

- API bearer-token auth is enabled.
- `/docs` and `/openapi.json` return `404` in staging.
- PostgreSQL backup retention is 7 days and PITR metadata is present.
- Restore testing has not been performed.
- No Azure budget alert was found by CLI; create one before public-read pilots.
- Only the Azure-services PostgreSQL firewall rule remains after operator validation.

## Architecture

- Azure Container Apps serves the FastAPI API.
- Azure Database for PostgreSQL Flexible Server stores persistent staging data.
- Azure Container Registry stores the Docker image.
- Azure Container Apps Jobs can run optional fixture-only DataOps validation.
- Azure Container Apps secrets hold `DATABASE_URL` and `PREDICTION_DESK_API_TOKEN` for
  immediate staging. Key Vault with managed identity is a later hardening step.
- Azure Cost Management budgets should be enabled before increasing scale, storage, or job
  cadence.

## Required Tools

- Azure CLI with Container Apps and Bicep support.
- Docker locally only if you choose local build/push; the provided helper uses `az acr build`.
- `psql` is optional for manual database inspection.

## One-Time Setup

```bash
az login
az account set --subscription "<subscription id>"
az account show --output table
```

Set operator shell values without committing them:

```bash
export AZURE_RESOURCE_GROUP=prediction-desk-staging-cus-rg
export AZURE_LOCATION=centralus
export AZURE_CONTAINER_REGISTRY=predictiondesk3bbbab44cusacr
export AZURE_CONTAINER_APP_NAME=prediction-desk-staging-api
export AZURE_POSTGRES_SERVER_NAME=prediction-desk-staging-pg-cus-3bbbab
export AZURE_POSTGRES_ADMIN_PASSWORD="<secret>"
export PREDICTION_DESK_API_TOKEN="<secret>"
export IMAGE_TAG="$(git rev-parse --short HEAD)"
```

The example uses `centralus` because this staging subscription was restricted from
PostgreSQL Flexible Server provisioning in `eastus` and `westus2`. Check regional
availability before changing it:

```bash
az rest --method get \
  --url "https://management.azure.com/subscriptions/$(az account show --query id -o tsv)/providers/Microsoft.DBforPostgreSQL/locations/<region>/capabilities?api-version=2024-08-01" \
  --query 'value[0].{restricted:restricted, reason:reason}'
```

Deploy infrastructure and app only with explicit confirmation:

```bash
CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

The script creates/updates the resource group, deploys the Bicep infrastructure, builds
and pushes the image to ACR, and deploys the API Container App.

## Environment Variables

Runtime env vars:

```bash
APP_ENV=staging
REQUIRE_API_TOKEN=true
ENABLE_OPENAPI_DOCS=false
DATABASE_URL=<managed Postgres URL>
PREDICTION_DESK_API_TOKEN=<secret>
LOG_LEVEL=INFO
APP_VERSION=<optional git sha or release tag>
GIT_COMMIT=<optional git sha>
```

`DATABASE_URL` should be SQLAlchemy-compatible and include `sslmode=require`. URL-encode
the password if it contains special characters.

## Infrastructure Template

Azure files live under [../deploy/azure](../deploy/azure):

- `main.bicep`
- `parameters.staging.json.example`
- `staging.env.example`
- `commands.md`

The Bicep template defines ACR, Log Analytics, Container Apps Environment, PostgreSQL
Flexible Server, the staging API Container App, Container Apps secrets, and an optional
fixture-only DataOps Job.

## Migrations

Run migrations from a secure operator shell:

```bash
export DATABASE_URL="postgresql+psycopg://predictiondeskadmin:<encoded-password>@<server>.postgres.database.azure.com:5432/prediction_desk?sslmode=require"
scripts/azure_migrate_and_verify.sh
```

If the migration host is outside Azure, add a temporary PostgreSQL firewall rule for the
operator IP before running migrations, then remove it after validation if it is no longer
needed.

The helper hides `DATABASE_URL`, runs Alembic, and prints read-only table counts.

## Staging Smoke

```bash
export API_BASE_URL="https://<container-app-fqdn>"
export PREDICTION_DESK_API_TOKEN="<secret>"
scripts/azure_staging_smoke.sh
```

This wraps `scripts/staging_smoke.sh` and validates health, readiness, market readback,
DataOps defaults, fixture collection, coverage, and gaps. It does not call public venue
endpoints.

## DB Inspection

```bash
scripts/azure_inspect_counts.sh
```

Requires `DATABASE_URL` and is read-only.

## Fixture-Only DataOps Job

The optional job command is:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

It is fixture-only, does not set `--allow-network`, does not require venue credentials, and
does not call trading endpoints. Enable it only after fixture smoke passes and backups are
confirmed:

```bash
DEPLOY_FIXTURE_DATAOPS_JOB=true CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

## Public-Read Pilot

Public-read collection is manual only and must not be scheduled in this round.

```bash
API_BASE_URL="https://<container-app-fqdn>" \
PREDICTION_DESK_API_TOKEN="<secret>" \
CONFIRM_PUBLIC_READ_ONLY=true \
PUBLIC_READ_VENUES=kalshi \
MAX_PAYLOADS=5 \
scripts/staging_public_read_pilot.sh
```

Run it only after staging deploy, migrations, fixture smoke, backup confirmation, and
operator approval.

## Cost Guardrails

- Use small staging SKUs: Basic ACR, `Standard_B1ms` PostgreSQL, 0-1 API replicas.
- Set Azure Cost Management budgets and alerts before deployment.
- Keep fixture job cadence low.
- Do not schedule public-read collection yet.
- Delete or stop staging resources when not in use.
- Increase storage, replicas, or job cadence only after coverage/gaps and cost telemetry
  are understood.

Create a budget before running public-read pilots:

1. In Azure Portal, open **Cost Management + Billing**.
2. Select the active subscription.
3. Open **Budgets** and create a monthly cost budget for staging.
4. Scope it to `prediction-desk-staging-cus-rg` when available.
5. Add alert thresholds at 50%, 80%, and 100%.
6. Add the operator email recipient, then save.

The local Azure CLI can create the budget object, but notification setup is easier to
verify in the portal:

```bash
az consumption budget create \
  --budget-name prediction-desk-staging-monthly \
  --category cost \
  --amount 25 \
  --time-grain monthly \
  --start-date 2026-06-01 \
  --end-date 2027-06-01 \
  --resource-group-filter prediction-desk-staging-cus-rg
```

Do not increase public-read scope, app replicas, or scheduled job cadence until those
alerts are visible in Azure Cost Management.

## Backup Guidance

The Bicep template sets PostgreSQL backup retention to 7 days by default. Confirm backups
in the Azure portal before public-read pilots or scheduled validation jobs.

## GitHub Actions

`.github/workflows/azure-staging.yml` is manual dispatch only. It uses OIDC through
`azure/login` and expects these GitHub secrets:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_RESOURCE_GROUP`
- `AZURE_LOCATION`
- `AZURE_CONTAINER_REGISTRY`
- `AZURE_CONTAINER_APP_NAME`
- `AZURE_POSTGRES_SERVER_NAME`
- `AZURE_POSTGRES_ADMIN_PASSWORD`
- `PREDICTION_DESK_API_TOKEN`

Configure a federated credential in Azure for the GitHub repository before using the
workflow.

## Prohibited

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
