#!/usr/bin/env bash
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-sqlite:///prediction_desk.db}"
PORT="${PORT:-8000}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:${PORT}}"
MARKET_ID="${MARKET_ID:-mkt_sfo_rain_2026_09_01}"

echo "Preparing local database at ${DATABASE_URL}"
DATABASE_URL="${DATABASE_URL}" prediction-desk init-db
DATABASE_URL="${DATABASE_URL}" prediction-desk load-sample-data

echo "Starting local API on port ${PORT}"
DATABASE_URL="${DATABASE_URL}" PORT="${PORT}" scripts/run_api.sh &
api_pid=$!
trap 'kill "${api_pid}" >/dev/null 2>&1 || true' EXIT

for _ in $(seq 1 60); do
  if curl -fsS "${API_BASE_URL}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS "${API_BASE_URL}/healthz" >/dev/null
curl -fsS "${API_BASE_URL}/readyz" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/trust-verdicts/recompute" \
  >/dev/null

echo "Local smoke passed on ${API_BASE_URL}."
