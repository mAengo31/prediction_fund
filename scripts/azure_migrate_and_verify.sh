#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required. Retrieve it securely from Azure Container Apps secrets or your secret store." >&2
  exit 1
fi

echo "Running Azure staging migrations with DATABASE_URL hidden."
scripts/staging_migrate_and_verify.sh
