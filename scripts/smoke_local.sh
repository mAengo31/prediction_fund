#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  DATABASE_URL="sqlite:////tmp/prediction_desk_smoke_local.db"
  rm -f /tmp/prediction_desk_smoke_local.db
fi
PORT="${PORT:-8010}"
API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:${PORT}}"
MARKET_ID="${MARKET_ID:-mkt_sfo_rain_2026_09_01}"
DIFF_MARKET_ID="${DIFF_MARKET_ID:-mkt_rate_cut_rule_change_2026}"
INGESTED_MARKET_ID="${INGESTED_MARKET_ID:-kalshi_market_kxweather_nyc_rain_20260930}"
EQUIVALENT_MARKET_ID="${EQUIVALENT_MARKET_ID:-polymarket_market_0xrainnycsep2026}"
DIVERGENCE_ASOF="${DIVERGENCE_ASOF:-2026-06-16T12:20:00Z}"

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
curl -fsS -X POST "${API_BASE_URL}/api/v1/ingestion/run-once" \
  -H "Content-Type: application/json" \
  -d '{"venue_name":"kalshi","mode":"fixture","limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true,"derive_market_data":true,"compute_quality":true,"metadata":{}}' \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/ingestion/run-once" \
  -H "Content-Type: application/json" \
  -d '{"venue_name":"polymarket","mode":"fixture","limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true,"derive_market_data":true,"compute_quality":true,"metadata":{}}' \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/ingestion/runs" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/ingestion/cursors" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/venue-mappings" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/derive" \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/latest" \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/prices" \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/liquidity" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/data-quality/recompute" \
  -H "Content-Type: application/json" \
  -d '{"asof_timestamp":"2026-06-16T12:45:00Z","freshness_threshold_seconds":3600,"wide_spread_threshold":"0.10"}' \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/data-quality/latest?asof_timestamp=2026-06-16T12:45:00Z" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/integrity/analyze" \
  -H "Content-Type: application/json" \
  -d '{"asof_timestamp":"2026-06-16T12:45:00Z","force":false,"thresholds":{}}' \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/integrity/latest?asof_timestamp=2026-06-16T12:45:00Z" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/resolution/analyze-latest" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/resolution/analyze-latest" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${EQUIVALENT_MARKET_ID}/resolution/analyze-latest" \
  >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/resolution/latest" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/candidates" \
  -H "Content-Type: application/json" \
  -d "{\"market_ids\":[\"${INGESTED_MARKET_ID}\",\"${EQUIVALENT_MARKET_ID}\"],\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"min_candidate_score\":40,\"max_pairs\":10,\"force\":false}" \
  >/dev/null
equivalence_assessment="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/assess" \
  -H "Content-Type: application/json" \
  -d "{\"left_market_id\":\"${INGESTED_MARKET_ID}\",\"right_market_id\":\"${EQUIVALENT_MARKET_ID}\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"force\":false,\"config\":{}}")"
python - "${equivalence_assessment}" <<'PY'
import json
import sys

assessment = json.loads(sys.argv[1])["assessment"]
assert assessment["overall_score"] >= 70, assessment
assert assessment["comparison_permission"] in {"COMPARABLE", "COMPARABLE_WITH_HAIRCUT"}, assessment
PY
equivalence_assessment_id="$(python - "${equivalence_assessment}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["assessment"]["equivalence_assessment_id"])
PY
)"
equivalence_run="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke equivalence\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"market_ids\":[\"${INGESTED_MARKET_ID}\",\"${EQUIVALENT_MARKET_ID}\"],\"min_candidate_score\":40,\"max_pairs\":10,\"build_classes\":true,\"force\":false,\"metadata\":{}}")"
equivalence_run_id="$(python - "${equivalence_run}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["equivalence_run_id"])
PY
)"
curl -fsS "${API_BASE_URL}/api/v1/equivalence/runs/${equivalence_run_id}/summary" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/equivalence/classes" >/dev/null
divergence_analysis="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/assessments/${equivalence_assessment_id}/divergence/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"force\":false,\"config\":{}}")"
python - "${divergence_analysis}" <<'PY'
import json
import sys

analysis = json.loads(sys.argv[1])
assessment = analysis["assessment"]
assert assessment["status"] in {"WATCH", "MATERIAL_DIVERGENCE"}, assessment
assert assessment["overall_divergence_score"] > 0, assessment
PY
divergence_run="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/divergence/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke divergence\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"equivalence_assessment_ids\":[\"${equivalence_assessment_id}\"],\"max_pairs\":10,\"force\":false,\"config\":{},\"metadata\":{}}")"
divergence_run_id="$(python - "${divergence_run}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["divergence_run_id"])
PY
)"
curl -fsS "${API_BASE_URL}/api/v1/divergence/runs/${divergence_run_id}/summary" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/divergence/latest?asof_timestamp=${DIVERGENCE_ASOF}" >/dev/null
curl -fsS -X POST \
  "${API_BASE_URL}/api/v1/markets/${DIFF_MARKET_ID}/rule-snapshots/diff-latest" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/trust-verdicts/recompute" \
  >/dev/null
ingested_verdict="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/trust-verdicts/recompute")"
python - "${ingested_verdict}" <<'PY'
import json
import sys

verdict = json.loads(sys.argv[1])
assert verdict["metadata"].get("integrity", {}).get("assessment_id"), verdict
assert verdict["metadata"].get("equivalence", {}).get("comparable_market_count") == 1, verdict
assert verdict["metadata"].get("divergence", {}).get("divergence_assessment_ids"), verdict
PY
curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/policies/default" >/dev/null
pretrade_check="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/check" \
  -H "Content-Type: application/json" \
  -d "{\"market_id\":\"${INGESTED_MARKET_ID}\",\"strategy_context\":\"CROSS_VENUE_COMPARISON\",\"side\":\"BUY\",\"intent_type\":\"RESEARCH_ONLY\",\"requested_size_units\":\"1\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"metadata\":{}}")"
python - "${pretrade_check}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["decision"]["pretrade_decision_id"], payload
assert payload["input_snapshot"]["latest_divergence_assessment_ids"], payload
PY
curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/restrictions" \
  -H "Content-Type: application/json" \
  -d "{\"restriction_type\":\"MANUAL_REVIEW\",\"scope_type\":\"MARKET\",\"market_id\":\"${INGESTED_MARKET_ID}\",\"reason_code\":\"SMOKE_MANUAL_REVIEW\",\"metadata\":{}}" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/exposures" \
  -H "Content-Type: application/json" \
  -d "{\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"source\":\"MANUAL\",\"market_id\":\"${INGESTED_MARKET_ID}\",\"venue_id\":\"kalshi\",\"strategy_context\":\"RESEARCH\",\"market_exposure_units\":\"0\",\"event_exposure_units\":\"0\",\"venue_exposure_units\":\"0\",\"metadata\":{}}" \
  >/dev/null
pretrade_run="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke pretrade\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"market_ids\":[\"${INGESTED_MARKET_ID}\"],\"max_checks\":10,\"default_requested_size_units\":\"1\",\"strategy_context\":\"RESEARCH\",\"intent_type\":\"RESEARCH_ONLY\",\"metadata\":{}}")"
python - "${pretrade_run}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["summary"]["total_decisions"] == 1, payload
PY
curl -fsS "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/pretrade/latest?asof_timestamp=${DIVERGENCE_ASOF}" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/paper/policies/default" >/dev/null
paper_simulation="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/paper/simulate-intent" \
  -H "Content-Type: application/json" \
  -d "{\"market_id\":\"${MARKET_ID}\",\"strategy_context\":\"RESEARCH\",\"side\":\"BUY\",\"intent_type\":\"AGGRESSIVE_LIMIT\",\"requested_price\":\"0.60\",\"requested_size_units\":\"1\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"metadata\":{}}")"
python - "${paper_simulation}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["order"]["status"] == "FILLED", payload
assert payload["fills"], payload
assert payload["portfolio_snapshot"]["is_simulated"], payload
PY
curl -fsS "${API_BASE_URL}/api/v1/paper/orders" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/paper/fills" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/paper/position/latest?asof_timestamp=2026-06-16T12:00:00Z" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/paper/portfolio/latest?asof_timestamp=2026-06-16T12:00:00Z" >/dev/null
paper_run="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/paper/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke paper\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\"],\"max_orders\":10,\"initial_cash_simulated\":\"1000\",\"default_order_size_units\":\"1\",\"default_intent_type\":\"RESEARCH_ONLY\",\"default_strategy_context\":\"RESEARCH\",\"metadata\":{}}")"
paper_run_id="$(python - "${paper_run}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["summary"]["total_orders"] == 2, payload
print(payload["run"]["simulation_run_id"])
PY
)"
curl -fsS "${API_BASE_URL}/api/v1/paper/runs/${paper_run_id}/summary" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/research/strategies/default" >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/research/features/build" \
  -H "Content-Type: application/json" \
  -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"force\":true}" \
  >/dev/null
curl -fsS -X POST "${API_BASE_URL}/api/v1/research/signals/generate" \
  -H "Content-Type: application/json" \
  -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\"}" \
  >/dev/null
research_proposals="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/research/proposals/generate" \
  -H "Content-Type: application/json" \
  -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"strategy_ids\":[\"research_strategy_baseline_research_only_v1\"]}")"
research_proposal_id="$(python - "${research_proposals}" <<'PY'
import json
import sys

proposals = json.loads(sys.argv[1])
assert proposals, proposals
print(proposals[0]["proposal_id"])
PY
)"
research_trace="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/research/proposals/${research_proposal_id}/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"enable_paper_simulation":true,"paper_policy_id":null}')"
python - "${research_trace}" <<'PY'
import json
import sys

trace = json.loads(sys.argv[1])
assert trace["pretrade_action"] == "ALLOW", trace
assert trace["proposal_id"], trace
PY
research_run="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/research/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke research\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T12:00:00Z\",\"interval_seconds\":3600,\"strategy_ids\":[\"research_strategy_baseline_research_only_v1\"],\"market_ids\":[\"${MARKET_ID}\"],\"max_steps\":10,\"max_proposals\":10,\"enable_paper_simulation\":false,\"initial_cash_simulated\":\"1000\",\"metadata\":{}}")"
research_run_id="$(python - "${research_run}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
assert payload["summary"]["total_proposals"] == 1, payload
print(payload["run"]["research_run_id"])
PY
)"
curl -fsS "${API_BASE_URL}/api/v1/research/runs/${research_run_id}/summary" >/dev/null
curl -fsS "${API_BASE_URL}/api/v1/research/runs/${research_run_id}/attribution" >/dev/null
replay_response="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke replay\",\"policy_name\":\"trust_verdict_v1\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\",\"${INGESTED_MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":true,\"metadata\":{}}")"
replay_run_id="$(python - "${replay_response}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
curl -fsS "${API_BASE_URL}/api/v1/replay/runs/${replay_run_id}/summary" >/dev/null
replay_steps="$(curl -fsS "${API_BASE_URL}/api/v1/replay/runs/${replay_run_id}/steps")"
python - "${replay_steps}" "${INGESTED_MARKET_ID}" "${MARKET_ID}" <<'PY'
import json
import sys

steps = json.loads(sys.argv[1])
ingested_market_id = sys.argv[2]
market_id = sys.argv[3]
assert any(
    step["market_id"] == ingested_market_id
    and step["metadata"].get("latest_price_snapshot_id")
    and step["metadata"].get("latest_liquidity_snapshot_id")
    and step["metadata"].get("count_comparable_markets") == 1
    and step["metadata"].get("latest_divergence_assessment_ids")
    for step in steps
), steps
assert any(
    step["market_id"] == market_id
    and step["metadata"].get("latest_research_signal_ids")
    and step["metadata"].get("latest_research_proposal_ids")
    and step["metadata"].get("latest_research_trace_ids")
    for step in steps
), steps
PY
integrity_replay_response="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke integrity replay\",\"policy_name\":\"integrity_gate_v1\",\"start_time\":\"2026-06-16T12:45:00Z\",\"end_time\":\"2026-06-16T13:45:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${INGESTED_MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}")"
integrity_replay_run_id="$(python - "${integrity_replay_response}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
curl -fsS "${API_BASE_URL}/api/v1/replay/runs/${integrity_replay_run_id}/summary" >/dev/null
pretrade_replay_response="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke pretrade replay\",\"policy_name\":\"pretrade_gate_v1\",\"start_time\":\"${DIVERGENCE_ASOF}\",\"end_time\":\"2026-06-16T13:20:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${INGESTED_MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}")"
pretrade_replay_run_id="$(python - "${pretrade_replay_response}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
pretrade_replay_steps="$(curl -fsS "${API_BASE_URL}/api/v1/replay/runs/${pretrade_replay_run_id}/steps")"
python - "${pretrade_replay_steps}" <<'PY'
import json
import sys

steps = json.loads(sys.argv[1])
assert any(step["metadata"].get("pretrade_decision_id") for step in steps), steps
PY
paper_replay_response="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke paper replay\",\"policy_name\":\"paper_sim_gate_v1\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}")"
paper_replay_run_id="$(python - "${paper_replay_response}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
paper_replay_steps="$(curl -fsS "${API_BASE_URL}/api/v1/replay/runs/${paper_replay_run_id}/steps")"
python - "${paper_replay_steps}" <<'PY'
import json
import sys

steps = json.loads(sys.argv[1])
assert any(step["metadata"].get("latest_paper_position_snapshot_id") for step in steps), steps
PY
research_replay_response="$(curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"local smoke research replay\",\"policy_name\":\"research_policy_v1\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}")"
research_replay_run_id="$(python - "${research_replay_response}" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
research_replay_steps="$(curl -fsS "${API_BASE_URL}/api/v1/replay/runs/${research_replay_run_id}/steps")"
python - "${research_replay_steps}" <<'PY'
import json
import sys

steps = json.loads(sys.argv[1])
assert any(step["metadata"].get("latest_research_trace_ids") for step in steps), steps
PY

echo "Local smoke passed on ${API_BASE_URL}: ingestion, market data, integrity, equivalence, divergence, pretrade, paper, research, verdict, and replay succeeded."
