#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required for Azure count inspection." >&2
  exit 1
fi

echo "Inspecting Azure staging database counts with DATABASE_URL hidden."
python scripts/inspect_db_counts.py "$@"
