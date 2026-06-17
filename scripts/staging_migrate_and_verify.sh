#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required; staging migration was not run." >&2
  exit 1
fi

echo "Running Alembic migrations against configured DATABASE_URL (value hidden)."
scripts/migrate.sh
echo "Migrations completed."

if [[ "${SKIP_DB_COUNTS:-false}" == "true" ]]; then
  echo "Skipping DB count inspection because SKIP_DB_COUNTS=true."
  exit 0
fi

echo "Inspecting table counts with configured DATABASE_URL (value hidden)."
python scripts/inspect_db_counts.py
