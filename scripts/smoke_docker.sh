#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
MARKET_ID="${MARKET_ID:-mkt_sfo_rain_2026_09_01}"
DIFF_MARKET_ID="${DIFF_MARKET_ID:-mkt_rate_cut_rule_change_2026}"
INGESTED_MARKET_ID="${INGESTED_MARKET_ID:-kalshi_market_kxweather_nyc_rain_20260930}"
EQUIVALENT_MARKET_ID="${EQUIVALENT_MARKET_ID:-polymarket_market_0xrainnycsep2026}"
DIVERGENCE_ASOF="${DIVERGENCE_ASOF:-2026-06-16T12:20:00Z}"
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
kalshi_ingestion="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/ingestion/run-once" \
    -H "Content-Type: application/json" \
    -d '{"venue_name":"kalshi","mode":"fixture","limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true,"derive_market_data":true,"compute_quality":true,"metadata":{}}'
)" || fail "POST ${API_BASE_URL}/api/v1/ingestion/run-once kalshi"
polymarket_ingestion="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/ingestion/run-once" \
    -H "Content-Type: application/json" \
    -d '{"venue_name":"polymarket","mode":"fixture","limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true,"derive_market_data":true,"compute_quality":true,"metadata":{}}'
)" || fail "POST ${API_BASE_URL}/api/v1/ingestion/run-once polymarket"
ingestion_runs="$(curl_json GET "${API_BASE_URL}/api/v1/ingestion/runs")"
ingestion_cursors="$(curl_json GET "${API_BASE_URL}/api/v1/ingestion/cursors")"
venue_mappings="$(curl_json GET "${API_BASE_URL}/api/v1/venue-mappings")"
markets="$(curl_json GET "${API_BASE_URL}/api/v1/markets")"
market_data_latest="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/latest"
)"
market_data_prices="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/prices"
)"
market_data_liquidity="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/liquidity"
)"
market_data_derive="$(
  curl_json POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/market-data/derive"
)"
data_quality="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/data-quality/recompute" \
    -H "Content-Type: application/json" \
    -d '{"asof_timestamp":"2026-06-16T12:45:00Z","freshness_threshold_seconds":3600,"wide_spread_threshold":"0.10"}'
)" || fail "POST ${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/data-quality/recompute"
data_quality_latest="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/data-quality/latest?asof_timestamp=2026-06-16T12:45:00Z"
)"
integrity_analysis="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/integrity/analyze" \
    -H "Content-Type: application/json" \
    -d '{"asof_timestamp":"2026-06-16T12:45:00Z","force":false,"thresholds":{}}'
)" || fail "POST ${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/integrity/analyze"
integrity_latest="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/integrity/latest?asof_timestamp=2026-06-16T12:45:00Z"
)"
analysis="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/resolution/analyze-latest")"
ingested_analysis="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/resolution/analyze-latest")"
equivalent_analysis="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${EQUIVALENT_MARKET_ID}/resolution/analyze-latest")"
resolution="$(curl_json GET "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/resolution/latest")"
equivalence_candidates="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/candidates" \
    -H "Content-Type: application/json" \
    -d "{\"market_ids\":[\"${INGESTED_MARKET_ID}\",\"${EQUIVALENT_MARKET_ID}\"],\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"min_candidate_score\":40,\"max_pairs\":10,\"force\":false}"
)" || fail "POST ${API_BASE_URL}/api/v1/equivalence/candidates"
equivalence_assessment="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/assess" \
    -H "Content-Type: application/json" \
    -d "{\"left_market_id\":\"${INGESTED_MARKET_ID}\",\"right_market_id\":\"${EQUIVALENT_MARKET_ID}\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"force\":false,\"config\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/equivalence/assess"
equivalence_assessment_id="$(python - "$equivalence_assessment" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["assessment"]["equivalence_assessment_id"])
PY
)"
equivalence_run="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke equivalence\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"market_ids\":[\"${INGESTED_MARKET_ID}\",\"${EQUIVALENT_MARKET_ID}\"],\"min_candidate_score\":40,\"max_pairs\":10,\"build_classes\":true,\"force\":false,\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/equivalence/runs"
equivalence_run_id="$(python - "$equivalence_run" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["equivalence_run_id"])
PY
)"
equivalence_summary="$(
  curl_json GET "${API_BASE_URL}/api/v1/equivalence/runs/${equivalence_run_id}/summary"
)"
equivalence_classes="$(curl_json GET "${API_BASE_URL}/api/v1/equivalence/classes")"
divergence_analysis="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/equivalence/assessments/${equivalence_assessment_id}/divergence/analyze" \
    -H "Content-Type: application/json" \
    -d "{\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"force\":false,\"config\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/equivalence/assessments/${equivalence_assessment_id}/divergence/analyze"
divergence_run="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/divergence/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke divergence\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"equivalence_assessment_ids\":[\"${equivalence_assessment_id}\"],\"max_pairs\":10,\"force\":false,\"config\":{},\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/divergence/runs"
divergence_run_id="$(python - "$divergence_run" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["divergence_run_id"])
PY
)"
divergence_summary="$(
  curl_json GET "${API_BASE_URL}/api/v1/divergence/runs/${divergence_run_id}/summary"
)"
divergence_latest="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/divergence/latest?asof_timestamp=${DIVERGENCE_ASOF}"
)"
diff="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${DIFF_MARKET_ID}/rule-snapshots/diff-latest")"
verdict="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/trust-verdicts/recompute")"
ingested_verdict="$(curl_json POST "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/trust-verdicts/recompute")"
pretrade_policy="$(curl_json POST "${API_BASE_URL}/api/v1/pretrade/policies/default")"
pretrade_check="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/check" \
    -H "Content-Type: application/json" \
    -d "{\"market_id\":\"${INGESTED_MARKET_ID}\",\"strategy_context\":\"CROSS_VENUE_COMPARISON\",\"side\":\"BUY\",\"intent_type\":\"RESEARCH_ONLY\",\"requested_size_units\":\"1\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/pretrade/check"
pretrade_restriction="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/restrictions" \
    -H "Content-Type: application/json" \
    -d "{\"restriction_type\":\"MANUAL_REVIEW\",\"scope_type\":\"MARKET\",\"market_id\":\"${INGESTED_MARKET_ID}\",\"reason_code\":\"SMOKE_MANUAL_REVIEW\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/pretrade/restrictions"
pretrade_exposure="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/exposures" \
    -H "Content-Type: application/json" \
    -d "{\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"source\":\"MANUAL\",\"market_id\":\"${INGESTED_MARKET_ID}\",\"venue_id\":\"kalshi\",\"strategy_context\":\"RESEARCH\",\"market_exposure_units\":\"0\",\"event_exposure_units\":\"0\",\"venue_exposure_units\":\"0\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/pretrade/exposures"
pretrade_run="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/pretrade/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke pretrade\",\"asof_timestamp\":\"${DIVERGENCE_ASOF}\",\"market_ids\":[\"${INGESTED_MARKET_ID}\"],\"max_checks\":10,\"default_requested_size_units\":\"1\",\"strategy_context\":\"RESEARCH\",\"intent_type\":\"RESEARCH_ONLY\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/pretrade/runs"
pretrade_latest="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${INGESTED_MARKET_ID}/pretrade/latest?asof_timestamp=${DIVERGENCE_ASOF}"
)"
paper_policy="$(curl_json POST "${API_BASE_URL}/api/v1/paper/policies/default")"
paper_simulation="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/paper/simulate-intent" \
    -H "Content-Type: application/json" \
    -d "{\"market_id\":\"${MARKET_ID}\",\"strategy_context\":\"RESEARCH\",\"side\":\"BUY\",\"intent_type\":\"AGGRESSIVE_LIMIT\",\"requested_price\":\"0.60\",\"requested_size_units\":\"1\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/paper/simulate-intent"
python - "$paper_policy" "$paper_simulation" <<'PY'
import json
import sys

policy = json.loads(sys.argv[1])
simulation = json.loads(sys.argv[2])
assert policy["policy_name"] == "default_paper_execution_policy", policy
assert simulation["order"]["status"] == "FILLED", simulation
assert simulation["fills"], simulation
assert simulation["portfolio_snapshot"]["is_simulated"], simulation
PY
paper_orders="$(curl_json GET "${API_BASE_URL}/api/v1/paper/orders")"
paper_fills="$(curl_json GET "${API_BASE_URL}/api/v1/paper/fills")"
paper_position="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/paper/position/latest?asof_timestamp=2026-06-16T12:00:00Z"
)"
paper_portfolio="$(
  curl_json GET "${API_BASE_URL}/api/v1/paper/portfolio/latest?asof_timestamp=2026-06-16T12:00:00Z"
)"
paper_run="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/paper/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke paper\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\"],\"max_orders\":10,\"initial_cash_simulated\":\"1000\",\"default_order_size_units\":\"1\",\"default_intent_type\":\"RESEARCH_ONLY\",\"default_strategy_context\":\"RESEARCH\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/paper/runs"
paper_run_id="$(python - "$paper_orders" "$paper_fills" "$paper_position" "$paper_portfolio" "$paper_run" <<'PY'
import json
import sys

orders, fills, position, portfolio, run = (json.loads(arg) for arg in sys.argv[1:])
assert orders, orders
assert fills, fills
assert position["is_simulated"], position
assert portfolio["is_simulated"], portfolio
assert run["summary"]["total_orders"] == 2, run
print(run["run"]["simulation_run_id"])
PY
)"
paper_run_summary="$(curl_json GET "${API_BASE_URL}/api/v1/paper/runs/${paper_run_id}/summary")"
research_strategies="$(curl_json POST "${API_BASE_URL}/api/v1/research/strategies/default")"
scenario_seed="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/scenario/seeds/build" \
    -H "Content-Type: application/json" \
    -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"force\":false}"
)" || fail "POST ${API_BASE_URL}/api/v1/scenario/seeds/build"
scenario_artifacts="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/scenario/import-fixtures" \
    -H "Content-Type: application/json" \
    -d "{\"market_ids\":[\"${MARKET_ID}\"],\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"force\":false}"
)" || fail "POST ${API_BASE_URL}/api/v1/scenario/import-fixtures"
scenario_artifact_id="$(python - "$scenario_seed" "$scenario_artifacts" <<'PY'
import json
import sys

seed = json.loads(sys.argv[1])
artifacts = json.loads(sys.argv[2])
assert seed["seed_bundle_id"], seed
assert artifacts, artifacts
print(artifacts[0]["scenario_artifact_id"])
PY
)"
scenario_feature="$(
  curl_json POST "${API_BASE_URL}/api/v1/scenario/artifacts/${scenario_artifact_id}/normalize"
)"
scenario_latest="$(
  curl_json GET "${API_BASE_URL}/api/v1/markets/${MARKET_ID}/scenario/latest?asof_timestamp=2026-06-16T12:00:00Z"
)"
scenario_run="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/scenario/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke scenario\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"market_ids\":[\"${MARKET_ID}\"],\"mode\":\"IMPORT_FIXTURES\",\"max_items\":10,\"force\":false,\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/scenario/runs"
python - "$scenario_feature" "$scenario_latest" "$scenario_run" <<'PY'
import json
import sys

feature, latest, run = (json.loads(arg) for arg in sys.argv[1:])
assert feature["scenario_feature_snapshot_id"], feature
assert latest["scenario_feature_snapshot_id"] == feature["scenario_feature_snapshot_id"], latest
assert run["summary"]["total_features"] >= 1, run
PY
dataops_defaults="$(curl_json POST "${API_BASE_URL}/api/v1/dataops/defaults")"
dataops_universes="$(curl_json GET "${API_BASE_URL}/api/v1/dataops/universes")"
dataops_universe_id="$(python - "$dataops_defaults" "$dataops_universes" <<'PY'
import json
import sys

defaults = json.loads(sys.argv[1])
universes = json.loads(sys.argv[2])
assert defaults["universes"], defaults
assert defaults["collection_plans"], defaults
for universe in universes:
    if universe["universe_name"] == "all_active_prediction_markets_v1":
        print(universe["universe_id"])
        break
else:
    raise AssertionError(universes)
PY
)"
dataops_members="$(
  curl_json POST "${API_BASE_URL}/api/v1/dataops/universes/${dataops_universe_id}/build?asof_timestamp=2026-06-16T12:20:00Z"
)"
dataops_member_list="$(
  curl_json GET "${API_BASE_URL}/api/v1/dataops/universes/${dataops_universe_id}/members"
)"
dataops_plans="$(curl_json GET "${API_BASE_URL}/api/v1/dataops/collection-plans")"
dataops_collection="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/dataops/collection/run-once" \
    -H "Content-Type: application/json" \
    -d '{"venue_names":["kalshi"],"mode":"FIXTURE","allow_network":false,"max_payloads":10,"metadata":{"smoke":true}}'
)" || fail "POST ${API_BASE_URL}/api/v1/dataops/collection/run-once"
dataops_backfill_job="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/dataops/backfill/jobs" \
    -H "Content-Type: application/json" \
    -d "{\"venue_name\":\"kalshi\",\"market_ids\":[\"${INGESTED_MARKET_ID}\"],\"endpoint_types\":[\"ORDERBOOK\"],\"start_time\":\"2026-06-16T11:00:00Z\",\"end_time\":\"2026-06-16T12:00:00Z\",\"allow_network\":false,\"max_segments\":10,\"metadata\":{\"smoke\":true}}"
)" || fail "POST ${API_BASE_URL}/api/v1/dataops/backfill/jobs"
dataops_backfill_job_id="$(python - "$dataops_backfill_job" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["backfill_job_id"])
PY
)"
dataops_backfill_run="$(
  curl_json POST "${API_BASE_URL}/api/v1/dataops/backfill/jobs/${dataops_backfill_job_id}/run"
)"
dataops_backfill_segments="$(
  curl_json GET "${API_BASE_URL}/api/v1/dataops/backfill/jobs/${dataops_backfill_job_id}/segments"
)"
dataops_coverage="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/dataops/coverage/compute" \
    -H "Content-Type: application/json" \
    -d '{"scope_type":"GLOBAL","asof_timestamp":"2026-06-16T12:20:00Z"}'
)" || fail "POST ${API_BASE_URL}/api/v1/dataops/coverage/compute"
dataops_gaps="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/dataops/gaps/detect" \
    -H "Content-Type: application/json" \
    -d '{"scope_type":"GLOBAL","asof_timestamp":"2026-06-16T12:20:00Z","expected_cadence_seconds":3600}'
)" || fail "POST ${API_BASE_URL}/api/v1/dataops/gaps/detect"
python - "$dataops_members" "$dataops_member_list" "$dataops_plans" "$dataops_collection" \
  "$dataops_backfill_run" "$dataops_backfill_segments" "$dataops_coverage" \
  "$dataops_gaps" <<'PY'
import json
import sys

members, member_list, plans, collection, backfill, segments, coverage, gaps = (
    json.loads(arg) for arg in sys.argv[1:]
)
assert members, members
assert member_list, member_list
assert plans, plans
assert collection["run"]["allow_network"] is False, collection
assert backfill["segments"][0]["status"] == "SKIPPED_UNSUPPORTED", backfill
assert segments[0]["status"] == "SKIPPED_UNSUPPORTED", segments
assert coverage["total_markets"] >= 1, coverage
assert isinstance(gaps, list), gaps
PY
research_features="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/research/features/build" \
    -H "Content-Type: application/json" \
    -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"force\":true}"
)" || fail "POST ${API_BASE_URL}/api/v1/research/features/build"
research_signals="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/research/signals/generate" \
    -H "Content-Type: application/json" \
    -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"strategy_ids\":[\"research_strategy_scenario_context_research_v1\"]}"
)" || fail "POST ${API_BASE_URL}/api/v1/research/signals/generate"
research_proposals="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/research/proposals/generate" \
    -H "Content-Type: application/json" \
    -d "{\"market_id\":\"${MARKET_ID}\",\"asof_timestamp\":\"2026-06-16T12:00:00Z\",\"strategy_ids\":[\"research_strategy_baseline_research_only_v1\"]}"
)" || fail "POST ${API_BASE_URL}/api/v1/research/proposals/generate"
research_proposal_id="$(python - "$research_strategies" "$research_features" "$research_signals" "$research_proposals" <<'PY'
import json
import sys

strategies, features, signals, proposals = (json.loads(arg) for arg in sys.argv[1:])
assert any(item["strategy_name"] == "baseline_research_only_v1" for item in strategies), strategies
assert features, features
assert signals, signals
assert proposals, proposals
print(proposals[0]["proposal_id"])
PY
)"
research_trace="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/research/proposals/${research_proposal_id}/evaluate" \
    -H "Content-Type: application/json" \
    -d '{"enable_paper_simulation":true,"paper_policy_id":null}'
)" || fail "POST ${API_BASE_URL}/api/v1/research/proposals/${research_proposal_id}/evaluate"
research_run="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/research/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke research\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T12:00:00Z\",\"interval_seconds\":3600,\"strategy_ids\":[\"research_strategy_baseline_research_only_v1\"],\"market_ids\":[\"${MARKET_ID}\"],\"max_steps\":10,\"max_proposals\":10,\"enable_paper_simulation\":false,\"initial_cash_simulated\":\"1000\",\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/research/runs"
research_run_id="$(python - "$research_trace" "$research_run" <<'PY'
import json
import sys

trace = json.loads(sys.argv[1])
run = json.loads(sys.argv[2])
assert trace["pretrade_action"] == "ALLOW", trace
assert run["summary"]["total_proposals"] == 1, run
print(run["run"]["research_run_id"])
PY
)"
research_summary="$(curl_json GET "${API_BASE_URL}/api/v1/research/runs/${research_run_id}/summary")"
research_attribution="$(curl_json GET "${API_BASE_URL}/api/v1/research/runs/${research_run_id}/attribution")"
replay="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke replay\",\"policy_name\":\"trust_verdict_v1\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\",\"${INGESTED_MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":true,\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/replay/runs"
replay_run_id="$(python - "$replay" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
replay_summary="$(curl_json GET "${API_BASE_URL}/api/v1/replay/runs/${replay_run_id}/summary")"
replay_steps="$(curl_json GET "${API_BASE_URL}/api/v1/replay/runs/${replay_run_id}/steps")"
integrity_replay="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
    -H "Content-Type: application/json" \
    -d '{"name":"docker smoke integrity replay","policy_name":"integrity_gate_v1","start_time":"2026-06-16T12:45:00Z","end_time":"2026-06-16T13:45:00Z","interval_seconds":3600,"market_ids":["kalshi_market_kxweather_nyc_rain_20260930"],"max_steps":10,"persist_steps":true,"force_recompute_verdicts":false,"metadata":{}}'
)" || fail "POST ${API_BASE_URL}/api/v1/replay/runs integrity gate"
integrity_replay_run_id="$(python - "$integrity_replay" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
integrity_replay_summary="$(
  curl_json GET "${API_BASE_URL}/api/v1/replay/runs/${integrity_replay_run_id}/summary"
)"
pretrade_replay="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke pretrade replay\",\"policy_name\":\"pretrade_gate_v1\",\"start_time\":\"${DIVERGENCE_ASOF}\",\"end_time\":\"2026-06-16T13:20:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${INGESTED_MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/replay/runs pretrade gate"
pretrade_replay_run_id="$(python - "$pretrade_replay" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
pretrade_replay_steps="$(
  curl_json GET "${API_BASE_URL}/api/v1/replay/runs/${pretrade_replay_run_id}/steps"
)"
paper_replay="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke paper replay\",\"policy_name\":\"paper_sim_gate_v1\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/replay/runs paper gate"
paper_replay_run_id="$(python - "$paper_replay" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
paper_replay_steps="$(
  curl_json GET "${API_BASE_URL}/api/v1/replay/runs/${paper_replay_run_id}/steps"
)"
python - "$paper_run_summary" "$paper_replay_steps" <<'PY'
import json
import sys

summary = json.loads(sys.argv[1])
steps = json.loads(sys.argv[2])
assert summary["total_orders"] == 2, summary
assert any(step["metadata"].get("latest_paper_position_snapshot_id") for step in steps), steps
PY
research_replay="$(
  curl -fsS -X POST "${API_BASE_URL}/api/v1/replay/runs" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"docker smoke research replay\",\"policy_name\":\"research_policy_v1\",\"start_time\":\"2026-06-16T12:00:00Z\",\"end_time\":\"2026-06-16T13:00:00Z\",\"interval_seconds\":3600,\"market_ids\":[\"${MARKET_ID}\"],\"max_steps\":10,\"persist_steps\":true,\"force_recompute_verdicts\":false,\"metadata\":{}}"
)" || fail "POST ${API_BASE_URL}/api/v1/replay/runs research policy"
research_replay_run_id="$(python - "$research_replay" <<'PY'
import json
import sys

print(json.loads(sys.argv[1])["run"]["run_id"])
PY
)"
research_replay_steps="$(
  curl_json GET "${API_BASE_URL}/api/v1/replay/runs/${research_replay_run_id}/steps"
)"
python - "$research_summary" "$research_attribution" "$research_replay_steps" <<'PY'
import json
import sys

summary = json.loads(sys.argv[1])
attribution = json.loads(sys.argv[2])
steps = json.loads(sys.argv[3])
assert summary["total_proposals"] == 1, summary
assert attribution["by_strategy"], attribution
assert any(step["metadata"].get("latest_research_trace_ids") for step in steps), steps
PY

python - "$health" "$ready" "$kalshi_ingestion" "$polymarket_ingestion" \
  "$ingestion_runs" "$ingestion_cursors" "$venue_mappings" "$markets" \
  "$market_data_latest" "$market_data_prices" "$market_data_liquidity" \
  "$market_data_derive" "$data_quality" "$data_quality_latest" \
  "$integrity_analysis" "$integrity_latest" "$analysis" "$ingested_analysis" \
  "$equivalent_analysis" "$resolution" "$equivalence_candidates" \
  "$equivalence_assessment" "$equivalence_run" "$equivalence_summary" \
  "$equivalence_classes" "$divergence_analysis" "$divergence_run" \
  "$divergence_summary" "$divergence_latest" "$diff" "$verdict" "$ingested_verdict" \
  "$pretrade_policy" "$pretrade_check" "$pretrade_restriction" \
  "$pretrade_exposure" "$pretrade_run" "$pretrade_latest" "$replay" \
  "$replay_summary" "$replay_steps" "$integrity_replay" \
  "$integrity_replay_summary" "$pretrade_replay" "$pretrade_replay_steps" \
  "${MARKET_ID}" <<'PY'
import json
import sys

(
    health,
    ready,
    kalshi_ingestion,
    polymarket_ingestion,
    ingestion_runs,
    ingestion_cursors,
    venue_mappings,
    markets,
    market_data_latest,
    market_data_prices,
    market_data_liquidity,
    market_data_derive,
    data_quality,
    data_quality_latest,
    integrity_analysis,
    integrity_latest,
    analysis,
    ingested_analysis,
    equivalent_analysis,
    resolution,
    equivalence_candidates,
    equivalence_assessment,
    equivalence_run,
    equivalence_summary,
    equivalence_classes,
    divergence_analysis,
    divergence_run,
    divergence_summary,
    divergence_latest,
    diff,
    verdict,
    ingested_verdict,
    pretrade_policy,
    pretrade_check,
    pretrade_restriction,
    pretrade_exposure,
    pretrade_run,
    pretrade_latest,
    replay,
    replay_summary,
    replay_steps,
    integrity_replay,
    integrity_replay_summary,
    pretrade_replay,
    pretrade_replay_steps,
    market_id,
) = (
    *[json.loads(arg) for arg in sys.argv[1:-1]],
    sys.argv[-1],
)
assert health["status"] == "ok", health
assert ready["status"] == "ok", ready
assert ready["database"] == "ok", ready
assert ready["migrated"] is True, ready
assert kalshi_ingestion["ingestion"]["run"]["status"] == "COMPLETED", kalshi_ingestion
assert polymarket_ingestion["ingestion"]["run"]["status"] == "COMPLETED", polymarket_ingestion
assert kalshi_ingestion["price_snapshots_created"] >= 3, kalshi_ingestion
assert kalshi_ingestion["liquidity_snapshots_created"] >= 3, kalshi_ingestion
assert len(ingestion_runs) >= 2, ingestion_runs
assert ingestion_cursors, ingestion_cursors
assert any(
    mapping["canonical_market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
    for mapping in venue_mappings
), venue_mappings
assert any(market["market_id"] == market_id for market in markets), markets
assert any(
    market["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
    for market in markets
), markets
assert market_data_latest["price_snapshot"], market_data_latest
assert market_data_latest["liquidity_snapshot"], market_data_latest
assert len(market_data_prices) >= 3, market_data_prices
assert len(market_data_liquidity) >= 3, market_data_liquidity
assert market_data_derive["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
assert data_quality["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
assert data_quality_latest["quality_report_id"] == data_quality["quality_report_id"]
assert integrity_analysis["assessment"]["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
assert integrity_latest["integrity_assessment_id"] == integrity_analysis["assessment"]["integrity_assessment_id"]
assert integrity_analysis["signals"], integrity_analysis
assert analysis["predicate"]["parse_status"] == "PARSED", analysis
assert ingested_analysis["predicate"]["parse_status"] == "PARSED", ingested_analysis
assert equivalent_analysis["predicate"]["parse_status"] == "PARSED", equivalent_analysis
assert resolution["predicate"]["predicate_id"] == analysis["predicate"]["predicate_id"], resolution
assert equivalence_candidates, equivalence_candidates
assert equivalence_assessment["assessment"]["overall_score"] >= 70, equivalence_assessment
assert equivalence_assessment["assessment"]["comparison_permission"] in {
    "COMPARABLE",
    "COMPARABLE_WITH_HAIRCUT",
}, equivalence_assessment
assert equivalence_run["summary"]["total_assessments"] >= 1, equivalence_run
assert equivalence_summary["equivalence_run_id"] == equivalence_run["run"]["equivalence_run_id"]
assert equivalence_classes, equivalence_classes
assert divergence_analysis["assessment"]["status"] in {
    "WATCH",
    "MATERIAL_DIVERGENCE",
}, divergence_analysis
assert divergence_analysis["assessment"]["overall_divergence_score"] > 0, divergence_analysis
assert divergence_run["summary"]["total_assessments"] >= 1, divergence_run
assert divergence_summary["divergence_run_id"] == divergence_run["run"]["divergence_run_id"]
assert divergence_latest["status"] in {"WATCH", "MATERIAL_DIVERGENCE"}, divergence_latest
assert "RESOLUTION_SOURCE_CHANGED" in diff["semantic_change_flags"], diff
assert verdict["market_id"] == market_id, verdict
assert verdict["action"] == "ALLOW", verdict
assert ingested_verdict["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930", ingested_verdict
assert ingested_verdict["metadata"].get("integrity", {}).get("assessment_id"), ingested_verdict
assert ingested_verdict["metadata"].get("equivalence", {}).get("comparable_market_count") == 1
assert ingested_verdict["metadata"].get("divergence", {}).get("divergence_assessment_ids")
assert pretrade_policy["policy_name"] == "default_pretrade_policy", pretrade_policy
assert pretrade_check["decision"]["pretrade_decision_id"], pretrade_check
assert pretrade_check["input_snapshot"]["latest_divergence_assessment_ids"], pretrade_check
assert pretrade_restriction["reason_code"] == "SMOKE_MANUAL_REVIEW", pretrade_restriction
assert pretrade_exposure["exposure_snapshot_id"], pretrade_exposure
assert pretrade_run["summary"]["total_decisions"] == 1, pretrade_run
assert pretrade_latest["pretrade_decision_id"], pretrade_latest
assert replay["summary"]["total_steps"] == 4, replay
assert replay_summary["run_id"] == replay["run"]["run_id"], replay_summary
assert any(
    step["market_id"] == "kalshi_market_kxweather_nyc_rain_20260930"
    and step["metadata"].get("latest_price_snapshot_id")
    and step["metadata"].get("latest_liquidity_snapshot_id")
    and step["metadata"].get("count_comparable_markets") == 1
    and step["metadata"].get("latest_divergence_assessment_ids")
    for step in replay_steps
), replay_steps
assert any(
    step["market_id"] == market_id
    and step["metadata"].get("latest_research_signal_ids")
    and step["metadata"].get("latest_research_proposal_ids")
    and step["metadata"].get("latest_research_trace_ids")
    and step["metadata"].get("latest_scenario_feature_snapshot_id")
    for step in replay_steps
), replay_steps
assert integrity_replay["run"]["policy_name"] == "integrity_gate_v1", integrity_replay
assert integrity_replay_summary["run_id"] == integrity_replay["run"]["run_id"], integrity_replay_summary
assert pretrade_replay["run"]["policy_name"] == "pretrade_gate_v1", pretrade_replay
assert any(
    step["metadata"].get("pretrade_decision_id") for step in pretrade_replay_steps
), pretrade_replay_steps
PY

echo "Docker smoke passed for ${COMPOSE_PROJECT_NAME}: healthz, readyz, ingestion, market data, quality, integrity, equivalence, divergence, pretrade, paper, scenario, dataops, research, verdict, and replay succeeded."
