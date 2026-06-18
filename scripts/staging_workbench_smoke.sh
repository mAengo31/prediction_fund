#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required; workbench smoke was not run." >&2
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

request_json markets GET /api/v1/markets

market_id="$(
  python - "${tmp_dir}/markets.json" <<'PY'
from __future__ import annotations

import json
import sys

with open(sys.argv[1]) as handle:
    markets = json.load(handle)

if not markets:
    raise SystemExit("no markets available for workbench smoke")

print(markets[0]["market_id"])
PY
)"

run_payload="$(
  python - "${market_id}" <<'PY'
from __future__ import annotations

import json
import sys

print(json.dumps({
    "name": "staging workbench smoke",
    "market_ids": [sys.argv[1]],
    "limit": 10,
    "force": False,
    "metadata": {"source": "staging_workbench_smoke"},
}))
PY
)"

queue_payload="$(
  python - "${market_id}" <<'PY'
from __future__ import annotations

import json
import sys

print(json.dumps({
    "market_ids": [sys.argv[1]],
    "queue_name": "staging_workbench_smoke",
    "limit": 10,
    "force": False,
}))
PY
)"

note_payload="$(
  python - "${market_id}" <<'PY'
from __future__ import annotations

import json
import sys

print(json.dumps({
    "market_id": sys.argv[1],
    "author": "staging-smoke",
    "note_type": "OBSERVATION",
    "text": "Staging validation note: workbench smoke completed. No trading action.",
    "tags": ["staging", "workbench", "validation"],
    "metadata": {"source": "staging_workbench_smoke"},
}))
PY
)"

request_json workbench_run POST /api/v1/workbench/runs "${run_payload}"
request_json workbench_runs GET /api/v1/workbench/runs
request_json queue_build POST /api/v1/workbench/queues/build "${queue_payload}"
request_json queue_items GET /api/v1/workbench/queues/items
request_json decision_card POST "/api/v1/workbench/markets/${market_id}/decision-card" '{}'
request_json latest_card GET "/api/v1/workbench/markets/${market_id}/decision-card/latest"
request_json note_create POST /api/v1/workbench/notes "${note_payload}"
request_json notes GET /api/v1/workbench/notes

python - "${tmp_dir}" "${market_id}" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
market_id = sys.argv[2]


def load(name: str):
    with (root / f"{name}.json").open() as handle:
        return json.load(handle)


run_result = load("workbench_run")
queue_items = load("queue_build")
listed_queue_items = load("queue_items")
card = load("decision_card")
latest_card = load("latest_card")
note = load("note_create")
notes = load("notes")

summary = run_result["summary"]
print(
    "staging_workbench_smoke ok: "
    f"market_id={market_id} "
    f"run_id={run_result['run']['workbench_run_id']} "
    f"run_queue_items={summary['total_queue_items']} "
    f"run_cards={summary['total_decision_cards']} "
    f"queue_items={len(queue_items)} "
    f"stored_queue_items={len(listed_queue_items)} "
    f"decision_card={card['decision_card_id']} "
    f"latest_card={latest_card['decision_card_id']} "
    f"review_action={card['recommended_next_review_action']} "
    f"note_id={note['note_id']} "
    f"stored_notes={len(notes)}"
)
PY
