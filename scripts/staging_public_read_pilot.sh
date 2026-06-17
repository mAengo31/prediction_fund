#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_PUBLIC_READ_ONLY:-}" != "true" ]]; then
  echo "Public read-only pilot not run. Set CONFIRM_PUBLIC_READ_ONLY=true to opt in."
  exit 0
fi

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required; public read-only pilot was not run." >&2
  exit 1
fi

if [[ -z "${PREDICTION_DESK_API_TOKEN:-}" ]]; then
  echo "PREDICTION_DESK_API_TOKEN is required for the staging public-read pilot." >&2
  exit 1
fi

API_BASE_URL="${API_BASE_URL%/}"
PUBLIC_READ_VENUES="${PUBLIC_READ_VENUES:-kalshi}"
MAX_PAYLOADS="${MAX_PAYLOADS:-5}"

if ! [[ "${MAX_PAYLOADS}" =~ ^[0-9]+$ ]] || (( MAX_PAYLOADS < 1 || MAX_PAYLOADS > 10 )); then
  echo "MAX_PAYLOADS must be an integer from 1 through 10 for the staging pilot." >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

auth_args=(-H "Authorization: Bearer ${PREDICTION_DESK_API_TOKEN}")

request_json() {
  local name="$1"
  local method="$2"
  local path="$3"
  local payload="${4:-}"
  local outfile="${tmp_dir}/${name}.json"
  local url="${API_BASE_URL}${path}"
  local args=(-fsS -X "${method}" "${url}" -o "${outfile}" "${auth_args[@]}")

  if [[ "${method}" != "GET" ]]; then
    if [[ -z "${payload}" ]]; then
      payload="{}"
    fi
    args+=(-H "Content-Type: application/json" -d "${payload}")
  fi

  if ! curl "${args[@]}"; then
    echo "FAIL ${method} ${path}" >&2
    return 1
  fi
  echo "ok ${method} ${path}"
}

collection_payload="$(
  PUBLIC_READ_VENUES="${PUBLIC_READ_VENUES}" MAX_PAYLOADS="${MAX_PAYLOADS}" python - <<'PY'
from __future__ import annotations

import json
import os

venues = [item.strip() for item in os.environ["PUBLIC_READ_VENUES"].split(",") if item.strip()]
if not venues:
    raise SystemExit("PUBLIC_READ_VENUES resolved to an empty venue list")

print(
    json.dumps(
        {
            "venue_names": venues,
            "mode": "MANUAL_PUBLIC_FETCH",
            "allow_network": True,
            "max_payloads": int(os.environ["MAX_PAYLOADS"]),
            "metadata": {"source": "staging_public_read_pilot"},
        },
        separators=(",", ":"),
        sort_keys=True,
    )
)
PY
)"

request_json collection_run POST /api/v1/dataops/collection/run-once "${collection_payload}"

collection_run_id="$(
  python - "${tmp_dir}/collection_run.json" <<'PY'
from __future__ import annotations

import json
import sys

with open(sys.argv[1]) as handle:
    print(json.load(handle)["run"]["collection_run_id"])
PY
)"

request_json collection_run_detail GET "/api/v1/dataops/collection-runs/${collection_run_id}"
request_json coverage_compute POST /api/v1/dataops/coverage/compute \
  '{"scope_type":"GLOBAL"}'
request_json gaps_detect POST /api/v1/dataops/gaps/detect \
  '{"scope_type":"GLOBAL","expected_cadence_seconds":3600}'

python - "${tmp_dir}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1])


def load(name: str):
    with (root / f"{name}.json").open() as handle:
        return json.load(handle)


run = load("collection_run_detail")
coverage = load("coverage_compute")
gaps = load("gaps_detect")

print(
    "public_read_pilot result: "
    f"run={run['collection_run_id']} "
    f"status={run['status']} "
    f"venues={','.join(run['venue_names'])} "
    f"payloads={run['payloads_archived']} "
    f"markets_processed={run['markets_processed']} "
    f"errors={run['errors_count']} "
    f"coverage_score={coverage['coverage_score']} "
    f"detected_gaps={len(gaps)}"
)

if run["status"] in {"FAILED", "PARTIAL"} and run["payloads_archived"] == 0:
    raise SystemExit(
        "Public read-only pilot did not archive payloads. The endpoint may be unsupported "
        "or unavailable; fixture staging remains the validated path."
    )
PY
