#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
MARKET_ID="${MARKET_ID:-mkt_sfo_rain_2026_09_01}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-prediction-desk-smoke}"
POSTGRES_PORT="${POSTGRES_PORT:-55432}"
export POSTGRES_PORT
compose=(docker compose -p "${COMPOSE_PROJECT_NAME}")

fail() {
  echo "smoke_docker failed: $*" >&2
  echo "Recent app logs:" >&2
  "${compose[@]}" logs --tail=80 app >&2 || true
  echo "Recent postgres logs:" >&2
  "${compose[@]}" logs --tail=80 postgres >&2 || true
  exit 1
}

curl_json() {
  local method="$1"
  local url="$2"
  local output
  output="$(curl -fsS -X "${method}" "${url}")" || fail "${method} ${url}"
  printf '%s\n' "${output}"
}

wait_for_http() {
  local url="$1"
  local attempts=60
  local sleep_seconds=2
  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  fail "Timed out waiting for ${url}"
}

echo "Building Docker image and starting Postgres..."
"${compose[@]}" down --volumes --remove-orphans >/dev/null 2>&1 || true
"${compose[@]}" build || fail "docker compose build"
"${compose[@]}" up -d postgres || fail "docker compose up postgres"

echo "Running migrations..."
"${compose[@]}" run --rm migrate || fail "docker compose run migrate"

echo "Loading sample data..."
"${compose[@]}" run --rm app prediction-desk load-sample-data || fail "load sample data"

echo "Starting API..."
"${compose[@]}" up -d app || fail "docker compose up app"
wait_for_http "${API_BASE_URL}/healthz"

health="$(curl_json GET "${API_BASE_URL}/healthz")"
ready="$(curl_json GET "${API_BASE_URL}/readyz")"
markets="$(curl_json GET "${API_BASE_URL}/api/v1/markets")"
verdict="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/trust-verdicts/recompute")"

python - "$health" "$ready" "$markets" "$verdict" <<'PY'
import json
import sys

health, ready, markets, verdict = (json.loads(arg) for arg in sys.argv[1:])
assert health["status"] == "ok", health
assert ready["status"] == "ok", ready
assert ready["database"] == "ok", ready
assert ready["migrated"] is True, ready
assert any(market["market_id"] == "mkt_sfo_rain_2026_09_01" for market in markets), markets
assert verdict["market_id"] == "mkt_sfo_rain_2026_09_01", verdict
assert verdict["action"] == "ALLOW", verdict
PY

echo "Docker smoke passed for ${COMPOSE_PROJECT_NAME}: healthz, readyz, /api/v1/markets, and verdict recompute succeeded."
