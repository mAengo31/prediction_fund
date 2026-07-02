#!/usr/bin/env bash
set -euo pipefail

API_BASE="http://localhost:8000"
# Log path is script-relative so the repo can move without breaking collection.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$REPO_ROOT/logs/live_collection.log"
mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $1" | tee -a "$LOG"; }

log "=== live_collection starting ==="

# 1. Kalshi: fetch market catalog + orderbooks
log "Step 1: Kalshi market catalog"
curl -s -X POST "$API_BASE/api/v1/dataops/collection/run-once" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "MANUAL_PUBLIC_FETCH",
    "allow_network": true,
    "venue_names": ["kalshi"],
    "endpoint_types": ["MARKET_LIST", "MARKET_DETAIL", "ORDERBOOK"],
    "max_payloads": 20,
    "metadata": {"source": "scheduled_live_collection"}
  }' >> "$LOG" 2>&1
echo "" >> "$LOG"

# 2. Polymarket: fetch market catalog
log "Step 2: Polymarket market catalog"
curl -s -X POST "$API_BASE/api/v1/dataops/collection/run-once" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "MANUAL_PUBLIC_FETCH",
    "allow_network": true,
    "venue_names": ["polymarket"],
    "endpoint_types": ["MARKET_LIST"],
    "max_payloads": 5,
    "metadata": {"source": "scheduled_live_collection"}
  }' >> "$LOG" 2>&1
echo "" >> "$LOG"

# 3. Polymarket: fetch orderbooks + price history for all known markets
log "Step 3: Polymarket orderbooks + price history"
curl -s "$API_BASE/api/v1/markets" | python3 -c "
import json,sys
markets=[m['market_id'] for m in json.load(sys.stdin) if 'polymarket' in m.get('venue_id','')]
print(json.dumps(markets))
" > /tmp/pd_poly_ids.json

POLY_IDS=$(cat /tmp/pd_poly_ids.json)

curl -s -X POST "$API_BASE/api/v1/dataops/collection/run-once" \
  -H "Content-Type: application/json" \
  -d "{
    \"mode\": \"MANUAL_PUBLIC_FETCH\",
    \"allow_network\": true,
    \"venue_names\": [\"polymarket\"],
    \"endpoint_types\": [\"ORDERBOOK\", \"PRICE_HISTORY\"],
    \"market_ids\": $POLY_IDS,
    \"max_payloads\": 50,
    \"metadata\": {\"source\": \"scheduled_live_collection\"}
  }" >> "$LOG" 2>&1
echo "" >> "$LOG"

# 4. Integrity analysis on all markets
log "Step 4: Integrity analysis"
ALL_IDS=$(curl -s "$API_BASE/api/v1/markets" | python3 -c "
import json,sys
[print(m['market_id']) for m in json.load(sys.stdin)]
")
for mid in $ALL_IDS; do
  curl -s -X POST "$API_BASE/api/v1/markets/$mid/integrity/analyze" \
    -H "Content-Type: application/json" -d '{"force": false}' >> "$LOG" 2>&1
done
echo "" >> "$LOG"

# 5. Resolution analysis on all markets
log "Step 5: Resolution analysis"
for mid in $ALL_IDS; do
  curl -s -X POST "$API_BASE/api/v1/markets/$mid/resolution/analyze-latest" \
    -H "Content-Type: application/json" >> "$LOG" 2>&1
done
echo "" >> "$LOG"

# 6. Equivalence scan (cross-venue matching)
log "Step 6: Equivalence scan"
curl -s -X POST "$API_BASE/api/v1/equivalence/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "scheduled_equivalence_scan",
    "max_pairs": 1000,
    "build_classes": true,
    "force": false
  }' >> "$LOG" 2>&1
echo "" >> "$LOG"

# 7. Divergence scan (price gaps between venues)
log "Step 7: Divergence scan"
curl -s -X POST "$API_BASE/api/v1/divergence/runs" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "scheduled_divergence_scan",
    "max_pairs": 1000,
    "force": false
  }' >> "$LOG" 2>&1
echo "" >> "$LOG"

# 8. Pre-trade check on all markets (research intent)
log "Step 8: Pre-trade gate"
for mid in $ALL_IDS; do
  curl -s -X POST "$API_BASE/api/v1/pretrade/check" \
    -H "Content-Type: application/json" \
    -d "{
      \"market_id\": \"$mid\",
      \"strategy_context\": \"RESEARCH\",
      \"side\": \"BUY\",
      \"intent_type\": \"RESEARCH_ONLY\",
      \"requested_size_units\": \"1\",
      \"metadata\": {}
    }" >> "$LOG" 2>&1
done
echo "" >> "$LOG"

# 9. Build workbench queue
log "Step 9: Workbench queue"
curl -s -X POST "$API_BASE/api/v1/workbench/queues/build" \
  -H "Content-Type: application/json" \
  -d '{"queue_name": "default_review_queue", "limit": 100, "force": true}' >> "$LOG" 2>&1
echo "" >> "$LOG"

log "=== live_collection done ==="
