#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${API_BASE_URL:-}" ]]; then
  echo "API_BASE_URL is required; workbench status was not read." >&2
  exit 1
fi

python - <<'PY'
from __future__ import annotations

import json
import os
from urllib import parse, request

api_base_url = os.environ["API_BASE_URL"].rstrip("/")
api_token = os.environ.get("PREDICTION_DESK_API_TOKEN")
queue_name = os.environ.get("WORKBENCH_QUEUE_NAME")
headers = {"Content-Type": "application/json"}
if api_token:
    headers["Authorization"] = f"Bearer {api_token}"


def api_get(path: str):
    req = request.Request(api_base_url + path, headers=headers, method="GET")
    with request.urlopen(req, timeout=60) as response:
        body = response.read()
        return json.loads(body) if body else None


query = parse.urlencode({"queue_name": queue_name} if queue_name else {})
suffix = f"?{query}" if query else ""
status = api_get(f"/api/v1/workbench/status{suffix}")
latest = api_get(f"/api/v1/workbench/queues/latest{suffix}")
print(
    "workbench_status "
    f"latest_items={status.get('latest_queue_item_count')} "
    f"priority_counts={json.dumps(status.get('priority_bucket_counts', {}), sort_keys=True)} "
    f"review_status_counts={json.dumps(status.get('review_status_counts', {}), sort_keys=True)} "
    f"unresolved_critical={status.get('unresolved_critical_count')} "
    f"unresolved_high={status.get('unresolved_high_count')} "
    f"coverage_score={status.get('latest_coverage_score')} "
    f"gap_counts={json.dumps(status.get('latest_gap_counts', {}), sort_keys=True)} "
    f"public_read_schedule={status.get('public_read_schedule_status')}"
)
print("top_queue_items")
for item in latest[:10]:
    metadata = item.get("metadata") or {}
    print(
        json.dumps(
            {
                "queue_item_id": item["queue_item_id"],
                "market_id": item["market_id"],
                "priority_score": item["priority_score"],
                "priority_bucket": item["priority_bucket"],
                "review_status": item["review_status"],
                "primary_reason_code": item["primary_reason_code"],
                "review_action": metadata.get("recommended_next_review_action"),
                "hard_escalators": metadata.get("hard_escalators", []),
                "soft_escalators": metadata.get("soft_escalators", []),
            },
            sort_keys=True,
        )
    )
PY
