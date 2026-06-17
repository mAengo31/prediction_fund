#!/usr/bin/env bash
set -euo pipefail

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI is required. Install it, then run: az login" >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "Azure CLI is not authenticated. Run: az login" >&2
  exit 1
fi

AZURE_RESOURCE_GROUP="${AZURE_RESOURCE_GROUP:-prediction-desk-staging-rg}"
ACR_NAME="${AZURE_CONTAINER_REGISTRY:-${ACR_NAME:-}}"
IMAGE_NAME="${IMAGE_NAME:-prediction-desk}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"

if [[ -z "${ACR_NAME}" ]]; then
  echo "AZURE_CONTAINER_REGISTRY or ACR_NAME is required." >&2
  exit 1
fi

if ! az acr show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${ACR_NAME}" >/dev/null; then
  echo "ACR ${ACR_NAME} was not found in ${AZURE_RESOURCE_GROUP}. Deploy infrastructure first." >&2
  exit 1
fi

echo "Building and pushing ${IMAGE_NAME}:${IMAGE_TAG} to ACR ${ACR_NAME}."
az acr build \
  --resource-group "${AZURE_RESOURCE_GROUP}" \
  --registry "${ACR_NAME}" \
  --image "${IMAGE_NAME}:${IMAGE_TAG}" \
  .

login_server="$(az acr show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${ACR_NAME}" --query loginServer -o tsv)"
echo "Image pushed: ${login_server}/${IMAGE_NAME}:${IMAGE_TAG}"
