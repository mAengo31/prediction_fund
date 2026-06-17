#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required for Azure staging smoke." >&2
  exit 1
fi

echo "Running Azure staging fixture smoke against configured API_BASE_URL."
scripts/staging_smoke.sh
