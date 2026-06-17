#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_AZURE_STAGING_DEPLOY:-}" != "true" ]]; then
  echo "Azure staging deploy not run. Set CONFIRM_AZURE_STAGING_DEPLOY=true to create/update paid resources."
  exit 0
fi

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI is required. Install it, then run: az login" >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "Azure CLI is not authenticated. Run: az login" >&2
  exit 1
fi

echo "Ensuring Microsoft.App provider is registered for Azure Container Apps."
az provider register -n Microsoft.App --wait

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-prediction-desk-staging-rg}"
AZURE_LOCATION="${AZURE_LOCATION:-eastus}"
AZURE_CONTAINER_REGISTRY="${AZURE_CONTAINER_REGISTRY:-}"
AZURE_CONTAINER_APP_NAME="${AZURE_CONTAINER_APP_NAME:-prediction-desk-staging-api}"
AZURE_POSTGRES_SERVER_NAME="${AZURE_POSTGRES_SERVER_NAME:-}"
AZURE_POSTGRES_DATABASE="${AZURE_POSTGRES_DATABASE:-prediction_desk}"
AZURE_POSTGRES_ADMIN_USER="${AZURE_POSTGRES_ADMIN_USER:-predictiondeskadmin}"
IMAGE_NAME="${IMAGE_NAME:-prediction-desk}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
APP_VERSION="${APP_VERSION:-${IMAGE_TAG}}"
GIT_COMMIT="${GIT_COMMIT:-$(git rev-parse --short HEAD 2>/dev/null || echo '')}"
DEPLOY_FIXTURE_DATAOPS_JOB="${DEPLOY_FIXTURE_DATAOPS_JOB:-false}"

missing=()
[[ -z "${AZURE_CONTAINER_REGISTRY}" ]] && missing+=("AZURE_CONTAINER_REGISTRY")
[[ -z "${AZURE_POSTGRES_SERVER_NAME}" ]] && missing+=("AZURE_POSTGRES_SERVER_NAME")
[[ -z "${AZURE_POSTGRES_ADMIN_PASSWORD:-}" ]] && missing+=("AZURE_POSTGRES_ADMIN_PASSWORD")
[[ -z "${PREDICTION_DESK_API_TOKEN:-}" ]] && missing+=("PREDICTION_DESK_API_TOKEN")

if (( ${#missing[@]} > 0 )); then
  echo "Missing required environment variables: ${missing[*]}" >&2
  exit 1
fi

echo "Creating/updating resource group ${AZURE_RESOURCE_GROUP} in ${AZURE_LOCATION}."
az group create \
  --name "${AZURE_RESOURCE_GROUP}" \
  --location "${AZURE_LOCATION}" \
  --output none

common_parameters=(
  location="${AZURE_LOCATION}"
  acrName="${AZURE_CONTAINER_REGISTRY}"
  containerAppName="${AZURE_CONTAINER_APP_NAME}"
  postgresServerName="${AZURE_POSTGRES_SERVER_NAME}"
  postgresDatabaseName="${AZURE_POSTGRES_DATABASE}"
  postgresAdminUser="${AZURE_POSTGRES_ADMIN_USER}"
  postgresAdminPassword="${AZURE_POSTGRES_ADMIN_PASSWORD}"
  predictionDeskApiToken="${PREDICTION_DESK_API_TOKEN}"
  imageName="${IMAGE_NAME}"
  imageTag="${IMAGE_TAG}"
  appVersion="${APP_VERSION}"
  gitCommit="${GIT_COMMIT}"
)

echo "Deploying Azure infrastructure without Container App first."
az deployment group create \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --template-file deploy/azure/main.bicep \
  --parameters "${common_parameters[@]}" deployContainerApp=false \
  --output none

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP}" \
AZURE_CONTAINER_REGISTRY="${AZURE_CONTAINER_REGISTRY}" \
IMAGE_NAME="${IMAGE_NAME}" \
IMAGE_TAG="${IMAGE_TAG}" \
  scripts/azure_build_push.sh

echo "Deploying Azure Container App using the pushed image."
az deployment group create \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --template-file deploy/azure/main.bicep \
  --parameters "${common_parameters[@]}" \
    deployContainerApp=true \
    deployFixtureDataOpsJob="${DEPLOY_FIXTURE_DATAOPS_JOB}" \
  --output json

echo "Azure staging deployment command completed. Run migrations and fixture smoke next."
