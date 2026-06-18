#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_DISABLE_FIXTURE_SCHEDULE:-}" != "true" ]]; then
  echo "Set CONFIRM_DISABLE_FIXTURE_SCHEDULE=true to delete the fixture-only schedule." >&2
  exit 0
fi

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-prediction-desk-staging-cus-rg}"
AZURE_FIXTURE_JOB_NAME="${AZURE_FIXTURE_JOB_NAME:-pd-fixture-dataops-job}"

az account show --query id -o tsv >/dev/null

if az containerapp job show \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --name "${AZURE_FIXTURE_JOB_NAME}" >/dev/null 2>&1; then
  az containerapp job delete \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AZURE_FIXTURE_JOB_NAME}" \
    --yes
  echo "fixture_schedule deleted: job=${AZURE_FIXTURE_JOB_NAME}"
else
  echo "fixture_schedule not found: job=${AZURE_FIXTURE_JOB_NAME}"
fi
