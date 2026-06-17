# Azure Staging Commands

These commands are operator-facing. Replace placeholders in your shell or deployment
platform. Do not paste real tokens, database URLs, passwords, or Azure credentials into
logs or commits.

## 1. Login And Select Subscription

```bash
az login
az account set --subscription "<subscription id>"
az account show --output table
```

## 2. Set Local Variables

```bash
export AZURE_RESOURCE_GROUP=prediction-desk-staging-cus-rg
export AZURE_LOCATION=centralus
export AZURE_CONTAINER_REGISTRY=predictiondesk3bbbab44cusacr
export AZURE_CONTAINER_APP_NAME=prediction-desk-staging-api
export AZURE_POSTGRES_SERVER_NAME=prediction-desk-staging-pg-cus-3bbbab
export AZURE_POSTGRES_ADMIN_PASSWORD="<do-not-commit>"
export PREDICTION_DESK_API_TOKEN="<do-not-commit>"
export IMAGE_TAG="$(git rev-parse --short HEAD)"
```

This staging subscription was restricted from PostgreSQL Flexible Server provisioning in
`eastus` and `westus2`; `centralus` was validated for the first deployment. If you change
regions, check PostgreSQL capabilities first.

## 3. Deploy Infrastructure And App

This creates paid Azure resources only when explicitly confirmed:

```bash
CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

The script:

1. Creates or updates the resource group.
2. Deploys infrastructure without the app first.
3. Builds/pushes the Docker image to ACR.
4. Deploys/updates the Container App.

The optional fixture DataOps job is not created unless
`DEPLOY_FIXTURE_DATAOPS_JOB=true` is also set.

## 4. Run Migrations

Set a SQLAlchemy-compatible Postgres URL. URL-encode the password if needed:

```bash
export DATABASE_URL="postgresql+psycopg://predictiondeskadmin:<encoded-password>@<server>.postgres.database.azure.com:5432/prediction_desk?sslmode=require"
scripts/azure_migrate_and_verify.sh
```

If your workstation IP is not allowed by the PostgreSQL firewall, add a temporary rule in
the portal or by CLI, then remove it after migration.

```bash
PUBLIC_IP="$(curl -fsS https://api.ipify.org)"
az postgres flexible-server firewall-rule create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --server-name "$AZURE_POSTGRES_SERVER_NAME" \
  --name temporary-operator-migration-ip \
  --start-ip-address "$PUBLIC_IP" \
  --end-ip-address "$PUBLIC_IP"
```

## 5. Run Fixture Smoke

```bash
export API_BASE_URL="https://<container-app-fqdn>"
scripts/azure_staging_smoke.sh
```

`PREDICTION_DESK_API_TOKEN` is used if set and is not printed.

## 6. Inspect Counts

```bash
scripts/azure_inspect_counts.sh
```

Requires `DATABASE_URL` and is read-only.

## 7. Optional Fixture-Only DataOps Job

Only after fixture smoke and backup checks pass:

```bash
DEPLOY_FIXTURE_DATAOPS_JOB=true CONFIRM_AZURE_STAGING_DEPLOY=true scripts/azure_deploy_staging.sh
```

This creates a scheduled Container Apps Job that runs:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

It does not enable public-read collection.

## 8. Manual Public-Read Pilot

Do not schedule this. Run only after explicit approval:

```bash
CONFIRM_PUBLIC_READ_ONLY=true MAX_PAYLOADS=5 scripts/staging_public_read_pilot.sh
```

## 9. Cost Controls

```bash
az consumption budget create --help
az monitor metrics list --help
```

Set a budget in Azure Cost Management before increasing replicas, storage, job cadence, or
public-read scope.
