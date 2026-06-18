#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_ENABLE_FIXTURE_SCHEDULE:-}" != "true" ]]; then
  echo "Set CONFIRM_ENABLE_FIXTURE_SCHEDULE=true to create/update the fixture-only schedule." >&2
  exit 0
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required but will not be printed." >&2
  exit 1
fi

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-prediction-desk-staging-cus-rg}"
AZURE_CONTAINER_APP_NAME="${AZURE_CONTAINER_APP_NAME:-prediction-desk-staging-api}"
AZURE_FIXTURE_JOB_NAME="${AZURE_FIXTURE_JOB_NAME:-pd-fixture-dataops-job}"
AZURE_FIXTURE_JOB_CRON="${AZURE_FIXTURE_JOB_CRON:-0 */12 * * *}"
AZURE_FIXTURE_JOB_COMMAND="${AZURE_FIXTURE_JOB_COMMAND:-/app/scripts/run_fixture_dataops_job.sh}"

az account show --query id -o tsv >/dev/null

APP_JSON="$(az containerapp show \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --name "${AZURE_CONTAINER_APP_NAME}" \
  -o json)"

IMAGE="$(python -c 'import json,sys; print(json.load(sys.stdin)["properties"]["template"]["containers"][0]["image"])' <<<"${APP_JSON}")"
ENVIRONMENT_ID="$(python -c 'import json,sys; print(json.load(sys.stdin)["properties"]["environmentId"])' <<<"${APP_JSON}")"
ENVIRONMENT_NAME="${AZURE_CONTAINER_APP_ENVIRONMENT:-${ENVIRONMENT_ID##*/}}"
REGISTRY_SERVER="${AZURE_REGISTRY_SERVER:-${IMAGE%%/*}}"
REGISTRY_IDENTITY="$(python -c 'import json,sys; registries=json.load(sys.stdin)["properties"]["configuration"].get("registries") or []; print((registries[0] or {}).get("identity") or "")' <<<"${APP_JSON}")"

create_identity_args=()
if [[ -n "${REGISTRY_IDENTITY}" ]]; then
  create_identity_args=(
    --mi-user-assigned "${REGISTRY_IDENTITY}"
    --registry-identity "${REGISTRY_IDENTITY}"
  )
fi

if az containerapp job show \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --name "${AZURE_FIXTURE_JOB_NAME}" >/dev/null 2>&1; then
  az containerapp job update \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AZURE_FIXTURE_JOB_NAME}" \
    --image "${IMAGE}" \
    --cron-expression "${AZURE_FIXTURE_JOB_CRON}" \
    --secrets "prediction-desk-database-url=${DATABASE_URL}" \
    --set-env-vars \
      APP_ENV=staging \
      REQUIRE_API_TOKEN=true \
      ENABLE_OPENAPI_DOCS=false \
      DATABASE_URL=secretref:prediction-desk-database-url \
      LOG_LEVEL=INFO \
    --command "${AZURE_FIXTURE_JOB_COMMAND}"
else
  az containerapp job create \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AZURE_FIXTURE_JOB_NAME}" \
    --environment "${ENVIRONMENT_NAME}" \
    --trigger-type Schedule \
    --cron-expression "${AZURE_FIXTURE_JOB_CRON}" \
    --replica-timeout 1800 \
    --replica-retry-limit 1 \
    --replica-completion-count 1 \
    --parallelism 1 \
    --image "${IMAGE}" \
    --registry-server "${REGISTRY_SERVER}" \
    "${create_identity_args[@]}" \
    --secrets "prediction-desk-database-url=${DATABASE_URL}" \
    --env-vars \
      APP_ENV=staging \
      REQUIRE_API_TOKEN=true \
      ENABLE_OPENAPI_DOCS=false \
      DATABASE_URL=secretref:prediction-desk-database-url \
      LOG_LEVEL=INFO \
    --command "${AZURE_FIXTURE_JOB_COMMAND}"
fi

echo "fixture_schedule ready: job=${AZURE_FIXTURE_JOB_NAME} cron='${AZURE_FIXTURE_JOB_CRON}' command=${AZURE_FIXTURE_JOB_COMMAND} mode=FIXTURE public_read=held"
