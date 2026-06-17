#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required; staging smoke was not run." >&2
  exit 1
fi

API_BASE_URL="${API_BASE_URL%/}"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

auth_args=()
if [[ -n "${PREDICTION_DESK_API_TOKEN:-}" ]]; then
  auth_args=(-H "Authorization: Bearer ${PREDICTION_DESK_API_TOKEN}")
fi

request_json() {
  local name="$1"
  local method="$2"
  local path="$3"
  local payload="${4:-}"
  local outfile="${tmp_dir}/${name}.json"
  local url="${API_BASE_URL}${path}"
  local args=(-fsS -X "${method}" "${url}" -o "${outfile}")

  if [[ "${method}" != "GET" ]]; then
    if [[ -z "${payload}" ]]; then
      payload="{}"
    fi
    args+=(-H "Content-Type: application/json" -d "${payload}")
  fi
  if [[ "${#auth_args[@]}" -gt 0 ]]; then
    args+=("${auth_args[@]}")
  fi

  if ! curl "${args[@]}"; then
    echo "FAIL ${method} ${path}" >&2
    return 1
  fi
  echo "ok ${method} ${path}"
}

request_json health GET /healthz
request_json ready GET /readyz
request_json markets GET /api/v1/markets
request_json dataops_defaults POST /api/v1/dataops/defaults '{}'
request_json universes GET /api/v1/dataops/universes
request_json collection_plans GET /api/v1/dataops/collection-plans
request_json collection_run POST /api/v1/dataops/collection/run-once \
  '{"mode":"FIXTURE","allow_network":false,"max_payloads":10,"metadata":{"source":"staging_smoke"}}'
request_json coverage_compute POST /api/v1/dataops/coverage/compute \
  '{"scope_type":"GLOBAL"}'
request_json gaps_detect POST /api/v1/dataops/gaps/detect \
  '{"scope_type":"GLOBAL","expected_cadence_seconds":3600}'
request_json coverage GET /api/v1/dataops/coverage
request_json gaps GET /api/v1/dataops/gaps

python - "${tmp_dir}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1])


def load(name: str):
    with (root / f"{name}.json").open() as handle:
        return json.load(handle)


markets = load("markets")
universes = load("universes")
plans = load("collection_plans")
collection_run = load("collection_run")["run"]
coverage_report = load("coverage_compute")
gaps = load("gaps_detect")
coverage_list = load("coverage")
gaps_list = load("gaps")

print(
    "staging_smoke ok: "
    f"markets={len(markets)} "
    f"universes={len(universes)} "
    f"collection_plans={len(plans)} "
    f"collection_run={collection_run['collection_run_id']} "
    f"collection_status={collection_run['status']} "
    f"payloads={collection_run['payloads_archived']} "
    f"coverage_score={coverage_report['coverage_score']} "
    f"detected_gaps={len(gaps)} "
    f"stored_coverage_reports={len(coverage_list)} "
    f"stored_gaps={len(gaps_list)}"
)
PY
