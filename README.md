# Prediction Desk

**Prediction Desk** is a cloud-deployed, non-executing prediction-market trading-station and research platform for building a quant fund around prediction markets.

The project is currently focused on **live-market paper validation**, not historical-only backtesting. Because prediction markets are heavily path-dependent, liquidity-sensitive, and contract-resolution-sensitive, the next research phase should test hypotheses against **current live public market data** using paper trading and pre-trade controls before any real execution is considered.

---

## Current Status

### Deployed Staging Environment

The system is deployed to Azure staging.

```text
API:
  Azure Container Apps

Database:
  Azure PostgreSQL Flexible Server

Registry:
  Azure Container Registry

Scheduled job:
  Azure Container Apps Job

Current scheduled collection:
  Fixture-only DataOps job every 12 hours

Public-read collection:
  Manually tested
  Not scheduled

Live trading:
  Not implemented
  Not enabled
```

Current staging API:

```text
https://prediction-desk-staging-api.bluebush-22f9863f.centralus.azurecontainerapps.io
```

Staging security posture:

```text
Bearer-token auth: required
/docs: disabled
/openapi.json: disabled
Public-read schedule: held
Venue credentials: none
Wallets/private keys: none
Order routing: none
Live execution: none
```

---

## What Has Been Built

### 1. Core Platform

The project has a production-style internal service architecture:

```text
FastAPI internal API
CLI
PostgreSQL persistence
Alembic migrations
Docker
Azure Container Apps deployment
Azure PostgreSQL deployment
Smoke scripts
DB inspection scripts
Bearer-token API auth
```

The system can run locally, in Docker Compose, and in Azure staging.

---

### 2. Canonical Prediction-Market Data Model

The system normalizes prediction-market data into canonical objects:

```text
Venue
Event
Market
Outcome
MarketRuleSnapshot
OrderBookSnapshot
MarketPriceSnapshot
MarketLiquiditySnapshot
MarketDataQualityReport
RawVenuePayload
VenueMarketMapping
VenueOutcomeTokenMapping
```

The Polymarket path is now token-aware:

```text
Gamma market ID
condition ID
question ID
YES / NO outcome token IDs
CLOB asset IDs
enableOrderBook status
```

---

### 3. Read-Only Venue Ingestion

Supported public-read ingestion paths:

```text
Kalshi:
  MARKET_LIST
  MARKET_DETAIL
  ORDERBOOK

Polymarket:
  MARKET_DETAIL
  ORDERBOOK by token / asset ID
  PRICE_HISTORY by token / asset ID
```

Public-read collection has been manually validated for both Kalshi and Polymarket. Public-read scheduling is still held.

Current validated Polymarket path:

```text
MARKET_DETAIL
ORDERBOOK
PRICE_HISTORY
```

Recent validated Polymarket pilot:

```text
Payloads archived: 5
  1 MARKET_DETAIL
  2 ORDERBOOK
  2 PRICE_HISTORY

Errors: 0
Price snapshots added: 52
Orderbooks added: 2
Liquidity snapshots added: 2
```

---

### 4. DataOps Layer

The DataOps layer manages controlled collection and coverage:

```text
Market universes
Collection plans
Collection runs
Backfill jobs and segments
Coverage reports
Data gaps
Retention-policy objects
DataOps cycles
```

Current Azure scheduled job:

```text
Job:
  pd-fixture-dataops-job

Cadence:
  every 12 hours

Command:
  /app/scripts/run_fixture_dataops_job.sh

Actual command inside container:
  prediction-desk dataops-cycle --mode FIXTURE
```

This job does **not** run public-read collection.

---

### 5. Data Quality and Gap Detection

The system tracks market-data coverage and gaps.

Typical coverage fields:

```text
markets_with_rules
markets_with_orderbooks
markets_with_price_snapshots
markets_with_liquidity_snapshots
markets_with_quality_reports
coverage_score
gap counts by type
```

Known current staging condition:

```text
Orderbook coverage: complete for current staging set
Price coverage: complete for current staging set
Liquidity coverage: complete for current staging set
Rule snapshot coverage: incomplete
```

Known rule limitation:

```text
Several Kalshi public detail payloads expose rules_primary and rules_secondary,
but the fields are empty. The system correctly does not fabricate rule snapshots.
```

---

### 6. Resolution Corpus

The resolution corpus treats market rule text as contract data.

It supports:

```text
MarketRuleSnapshot hashing
ResolutionPredicate parsing
AmbiguityAssessment
RuleSnapshotDiff
Resolution-risk scoring
```

This is meant to catch contract ambiguity, settlement ambiguity, source ambiguity, deadline ambiguity, and rule changes.

---

### 7. Fast-Lane Integrity Signals

The integrity layer detects market-state risks:

```text
Empty book
Crossed book
One-sided book
Wide spread
Spread widening
Depth collapse
Price jump
Stale market data
Low data quality
Extreme book imbalance
Rule-change context
```

These are review and admissibility signals, not alpha claims.

---

### 8. Cross-Venue Equivalence

The equivalence engine compares markets across venues.

It assesses:

```text
title similarity
event identity
outcome structure
outcome mapping
predicate similarity
resolution source alignment
settlement authority alignment
temporal alignment
threshold alignment
timezone alignment
ambiguity compatibility
venue-rule compatibility
```

Outputs include:

```text
EQUIVALENT
NEAR_EQUIVALENT
RELATED
NEEDS_REVIEW
NOT_EQUIVALENT
```

Comparison permission:

```text
COMPARABLE
COMPARABLE_WITH_HAIRCUT
MANUAL_REVIEW
DO_NOT_COMPARE
```

---

### 9. Cross-Venue Divergence

Once markets are comparable, the divergence layer compares aligned prices and context.

It supports:

```text
SAME outcome price alignment
INVERSE outcome price alignment
spread-adjusted gap
stale-side context
low-liquidity context
low-data-quality context
high-integrity-risk context
```

Divergence outputs are review artifacts only. The system does **not** call these “arbitrage” and does **not** recommend trades from them.

---

### 10. Pre-Trade Gate

The pre-trade gate evaluates hypothetical trade intents.

Possible actions:

```text
ALLOW
ALLOW_SMALLER_SIZE
PASSIVE_ONLY
MANUAL_REVIEW
NO_TRADE
```

Inputs:

```text
market status
trust verdict
resolution risk
market-data quality
integrity risk
equivalence context
divergence context
restrictions
abstract exposure limits
intent type
```

The pre-trade gate does not place orders.

---

### 11. Paper Execution Simulator

The paper simulator creates simulated-only objects:

```text
PaperOrder
PaperFill
PaperLedgerEntry
PaperPositionSnapshot
PaperPortfolioSnapshot
PaperSimulationRun
```

Rules:

```text
Pre-trade gate must pass before simulation
No live orders
No venue order IDs
No real account IDs
No wallets
No private keys
Long-only by default
All PnL/equity outputs are simulated
```

---

### 12. Research Harness

The research harness can evaluate strategy hypotheses through:

```text
ResearchFeatureSnapshot
ResearchSignal
ResearchIntentProposal
ResearchDecisionTrace
ResearchRun
ResearchRunSummary
ResearchAttributionReport
```

Default research strategies exist, but they are scaffolds:

```text
baseline_research_only_v1
trust_verdict_allow_filter_v1
integrity_pass_filter_v1
divergence_research_hypothesis_v1
composite_conservative_research_v1
scenario_context_research_v1
```

They are not production alpha models.

---

### 13. Scenario / MiroFish-Style Slow-Lane Features

The system can import MiroFish-style reports as local scenario artifacts.

Supported:

```text
ScenarioSeedBundle
ScenarioSimulationSpec
ScenarioArtifact
ScenarioFeatureSnapshot
ScenarioRun
```

Not supported yet:

```text
Live MiroFish execution
LLM calls
Zep / GraphRAG calls
Scenario-driven trading decisions
```

Scenario features are research context only.

---

### 14. Desk Decision Workbench

The workbench is the first trading-station surface.

It supports:

```text
DeskWatchlist
MarketReviewQueueItem
MarketDecisionCard
CrossVenueComparisonCard
DeskReviewNote
WorkbenchRun
WorkbenchRunSummary
```

It can build:

```text
latest active review queue
market decision cards
cross-venue comparison cards
desk notes
workbench status summaries
```

Queue items include diagnostics:

```text
score_components
score_explanation
hard_escalators
soft_escalators
dampeners
```

Queue review workflow supports:

```text
NEW
IN_REVIEW
RESOLVED
DISMISSED
WATCHING
```

Review outcomes include:

```text
DATA_ISSUE_CONFIRMED
FALSE_POSITIVE
NEEDS_MORE_DATA
STRATEGY_CANDIDATE
CONTRACT_RISK_CONFIRMED
DIVERGENCE_REVIEWED
PRETRADE_BLOCK_CONFIRMED
WATCHLIST_ONLY
DISMISSED_NO_ACTION
OTHER
```

---

### 15. Vendor Dataset Evaluation

The vendor-data evaluator can inspect third-party historical data samples before purchasing or importing them.

Supported:

```text
VendorDatasetSource
VendorSampleFile
VendorSchemaInspection
VendorDataValidationReport
VendorImportDryRun
VendorEvaluationReport
VendorSchemaMappingConfig
```

Supported local file types:

```text
CSV
JSON
JSONL
Parquet
```

Capabilities:

```text
local file loading
URL rejection
file hashing
schema inspection
timestamp detection
token ID detection
price/size validation
orderbook/trade/price-history classification
dry-run canonical import
vendor evaluation scoring
mapping config support
large-file sampling
```

Vendor data is currently:

```text
dry-run only
not written into canonical market-data tables
not pulled from vendor APIs
not production-imported
```

---

## Current Operating Mode

The system is currently operating in this safe mode:

```text
Fixture-only schedule:
  active

Public-read schedule:
  held

Live trading:
  absent

Vendor imports:
  dry-run only

Workbench:
  active and usable

Daily desk review:
  ready
```

Recommended daily workflow:

```text
1. Run or inspect workbench status.
2. Review CRITICAL and HIGH queue items.
3. Mark items WATCHING / RESOLVED / DISMISSED / IN_REVIEW.
4. Add desk notes.
5. Track which reasons are useful or noisy.
```

---

## Why We Are Not Testing Live Profit Yet

We should test profit, but the next version of that test should be **live-market paper validation**, not historical-only backtesting.

Prediction markets are path-dependent and sensitive to:

```text
liquidity
orderbook staleness
resolution wording
token mapping
market-specific settlement rules
spread and fill assumptions
public data latency
venue-specific quirks
```

A naive historical backtest can easily produce fake edge.

The system was built first to prevent fake edge from:

```text
non-equivalent contracts
missing token IDs
bad timestamp semantics
stale data
ambiguous rules
thin books
crossed books
unfillable quotes
missing coverage
```

Now that the system exists, the next real objective is:

```text
Live-market paper validation
```

Not live execution.

---

## Next Technical Direction

The next major phase is to test simple hypotheses against live public market data in paper mode.

Suggested next phase:

```text
Live Paper Strategy Smoke Test v1
```

Inputs:

```text
current public Polymarket orderbooks
current public Polymarket price history
current market-data quality
integrity signals
pre-trade gate
paper simulator
workbench review queue
```

Example hypotheses:

```text
1. Book imbalance predicts short-horizon mid-price movement.
2. Wide-spread markets should be avoided by paper strategies.
3. Divergence NEEDS_REVIEW markets should not pass automated pre-trade.
4. Low-quality markets produce bad or unfillable paper signals.
5. Scenario context should create review priority, not direct proposals.
```

Expected outputs:

```text
paper-only signals
pre-trade decisions
simulated paper orders
simulated fills or no-fills
simulated position snapshots
reason-code attribution
desk review cards
```

Still prohibited:

```text
live orders
wallets
private keys
authenticated venue trading
capital deployment
```

---

# API Usage

## Base URL

Local:

```bash
export API_BASE_URL="http://localhost:8000"
```

Azure staging:

```bash
export API_BASE_URL="https://prediction-desk-staging-api.bluebush-22f9863f.centralus.azurecontainerapps.io"
```

## Authentication

Staging requires a bearer token.

```bash
export PREDICTION_DESK_API_TOKEN="<your-token>"
```

Use:

```bash
-H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Example:

```bash
curl -s "$API_BASE_URL/api/v1/markets" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Unauthenticated or invalid-token calls to protected endpoints return:

```text
401 Unauthorized
```

Staging also disables:

```text
/docs
/openapi.json
```

---

## Health and Readiness

```bash
curl -s "$API_BASE_URL/healthz"
curl -s "$API_BASE_URL/readyz" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
service status
version
environment
database readiness
migration status when available
```

---

## Markets

List markets:

```bash
curl -s "$API_BASE_URL/api/v1/markets" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Get one market:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
market ID
venue ID
event ID
title
market type
status
close time
settlement time
metadata
```

---

## DataOps

Create defaults:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/dataops/defaults" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

List universes:

```bash
curl -s "$API_BASE_URL/api/v1/dataops/universes" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

List collection plans:

```bash
curl -s "$API_BASE_URL/api/v1/dataops/collection-plans" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Run fixture collection once:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/dataops/collection/run-once" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "FIXTURE",
    "allow_network": false,
    "venue_names": ["kalshi", "polymarket"],
    "max_payloads": 20,
    "metadata": {"source": "manual_fixture_run"}
  }'
```

Manual public-read collection is available but gated:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/dataops/collection/run-once" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "MANUAL_PUBLIC_FETCH",
    "allow_network": true,
    "venue_names": ["polymarket"],
    "endpoint_types": ["MARKET_DETAIL", "ORDERBOOK", "PRICE_HISTORY"],
    "market_ids": ["<market_id>"],
    "max_payloads": 5,
    "metadata": {"source": "manual_public_read_pilot"}
  }'
```

Do not schedule public-read collection yet.

Compute coverage:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/dataops/coverage/compute" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scope_type": "GLOBAL"}'
```

Detect gaps:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/dataops/gaps/detect" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
coverage score
markets with rules
markets with orderbooks
markets with price snapshots
markets with liquidity snapshots
markets with quality reports
missing rule gaps
missing orderbook gaps
missing price gaps
missing liquidity gaps
stale market data gaps
```

---

## Market Data

Latest market data:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/market-data/latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Price snapshots:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/market-data/prices?limit=100" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Liquidity snapshots:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/market-data/liquidity?limit=100" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Data quality:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/data-quality/latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
latest price
bid
ask
mid
spread
orderbook depth
liquidity
quality score
quality reason codes
staleness
missing side / empty book / crossed book flags
```

---

## Resolution Corpus

Analyze latest market rules:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/markets/<market_id>/resolution/analyze-latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Get latest resolution analysis:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/resolution/latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
rule snapshot
resolution predicate
ambiguity assessment
ambiguity score
reason codes
evidence spans
```

---

## Integrity Signals

Analyze market integrity:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/markets/<market_id>/integrity/analyze" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

Latest integrity:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/integrity/latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
integrity risk score
integrity severity
action hint
empty/crossed/one-sided/wide-spread/stale signals
price jump
depth collapse
reason codes
```

---

## Equivalence

Run equivalence scan:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/equivalence/runs" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "manual equivalence scan",
    "max_pairs": 1000,
    "build_classes": true,
    "force": false
  }'
```

List assessments:

```bash
curl -s "$API_BASE_URL/api/v1/equivalence/assessments?limit=100" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
equivalence status
comparison permission
overall score
confidence score
dimension scores
outcome mappings
source/deadline/threshold/timezone mismatch flags
```

---

## Divergence

Run divergence scan:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/divergence/runs" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "manual divergence scan",
    "max_pairs": 1000,
    "force": false
  }'
```

Latest market divergence:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/divergence/latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
aligned price gap
spread-adjusted gap
equivalence context
stale side
weaker side
data quality context
integrity context
divergence status
review action hint
```

---

## Pre-Trade Gate

Check hypothetical intent:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/pretrade/check" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "<market_id>",
    "outcome_id": null,
    "venue_id": null,
    "strategy_context": "RESEARCH",
    "side": "BUY",
    "intent_type": "RESEARCH_ONLY",
    "requested_price": null,
    "requested_size_units": "1",
    "requested_notional_usd": null,
    "policy_id": null,
    "force_recompute_context": false,
    "metadata": {}
  }'
```

Available information:

```text
pretrade action
final allowed size
hard blockers
warnings
reason codes
resolution risk
quality score
integrity risk
divergence score
exposure risk
```

---

## Paper Simulation

Create default paper policy:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/paper/policies/default" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Simulate hypothetical intent:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/paper/simulate-intent" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "<market_id>",
    "outcome_id": null,
    "venue_id": null,
    "strategy_context": "RESEARCH",
    "side": "BUY",
    "intent_type": "RESEARCH_ONLY",
    "requested_price": null,
    "requested_size_units": "1",
    "paper_policy_id": null,
    "force_recompute_pretrade": false,
    "metadata": {}
  }'
```

Available information:

```text
paper order status
simulated fills
simulated ledger entries
simulated position snapshot
simulated portfolio snapshot
simulated PnL fields
```

All paper outputs are simulated.

---

## Research Harness

Create default strategies:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/research/strategies/default" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Generate signals:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/research/signals/generate" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "<market_id>",
    "force": false
  }'
```

Run research:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/research/runs" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "manual research run",
    "start_time": "2026-06-18T00:00:00Z",
    "end_time": "2026-06-18T01:00:00Z",
    "interval_seconds": 3600,
    "max_steps": 100,
    "max_proposals": 100,
    "enable_paper_simulation": true,
    "initial_cash_simulated": "1000",
    "force": false,
    "metadata": {}
  }'
```

Available information:

```text
research strategies
features
signals
hypothetical proposals
pretrade outcomes
paper simulation linkage
simulated attribution
```

---

## Scenario Features

Import local scenario fixtures:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/scenario/import-fixtures" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "force": false
  }'
```

Latest scenario feature:

```bash
curl -s "$API_BASE_URL/api/v1/markets/<market_id>/scenario/latest" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Available information:

```text
scenario confidence
scenario uncertainty
sentiment score
consensus score
polarization score
narrative risk
shock risk
key scenario labels
reason codes
```

Scenario features do not directly change trading decisions.

---

## Replay

Run replay:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/replay/runs" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "manual replay",
    "policy_name": "pretrade_gate_v1",
    "start_time": "2026-06-18T00:00:00Z",
    "end_time": "2026-06-18T01:00:00Z",
    "interval_seconds": 3600,
    "max_steps": 100,
    "persist_steps": true,
    "force_recompute_verdicts": false,
    "metadata": {}
  }'
```

Available information:

```text
replay steps
as-of decisions
trust verdicts
pretrade decisions
paper metadata
research metadata
scenario metadata
input/output hashes
summary counts
```

---

## Workbench

Workbench status:

```bash
curl -s "$API_BASE_URL/api/v1/workbench/status" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Build queue:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/workbench/queues/build" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "queue_name": "default_review_queue",
    "limit": 100,
    "force": false
  }'
```

Latest queue:

```bash
curl -s "$API_BASE_URL/api/v1/workbench/queues/latest?limit=20" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Queue summary:

```bash
curl -s "$API_BASE_URL/api/v1/workbench/queues/summary" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN"
```

Build decision card:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/workbench/markets/<market_id>/decision-card" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

Update queue item status:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/workbench/queues/items/<queue_item_id>/status" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "review_status": "WATCHING",
    "reviewed_by": "operator",
    "review_outcome": "NEEDS_MORE_DATA",
    "review_reason": "Known data gap under review.",
    "note_text": "No trading action.",
    "tags": ["staging", "review"]
  }'
```

Available information:

```text
active queue items
priority buckets
review statuses
reason codes
hard escalators
soft escalators
dampeners
decision cards
comparison cards
desk notes
review outcomes
```

---

## Vendor Data Evaluation

Register source:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/vendor-data/sources" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_name": "Kaggle",
    "dataset_name": "polymarket_sample",
    "dataset_version": "sample_v1",
    "license_status": "SAMPLE_ONLY",
    "metadata": {}
  }'
```

Load sample:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/vendor-data/samples/load" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_source_id": "<vendor_source_id>",
    "file_path": "sample_data/vendor_samples/polymarket_price_history_sample.csv",
    "max_size_mb": 100
  }'
```

Inspect sample:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/vendor-data/samples/<sample_file_id>/inspect" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Validate sample:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/vendor-data/samples/<sample_file_id>/validate" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

Dry-run import:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/vendor-data/samples/<sample_file_id>/dry-run-import" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sample_kind": "ORDERBOOK",
    "max_rows": 10000
  }'
```

Evaluate vendor:

```bash
curl -s -X POST "$API_BASE_URL/api/v1/vendor-data/evaluate" \
  -H "Authorization: Bearer $PREDICTION_DESK_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_source_id": "<vendor_source_id>",
    "sample_file_ids": ["<sample_file_id>"]
  }'
```

Available information:

```text
schema inspection
token identifier detection
timestamp detection
price validation
orderbook/trade classification
dry-run would-create counts
vendor evaluation scores
strengths
weaknesses
questions for vendor
recommendation
```

Vendor-data imports are currently dry-run only.

---

## CLI Examples

Workbench status:

```bash
prediction-desk workbench-status
```

Latest queue:

```bash
prediction-desk workbench-queue --latest
```

Build a decision card:

```bash
prediction-desk workbench-card --market-id <market_id>
```

Run fixture DataOps locally:

```bash
prediction-desk dataops-cycle --mode FIXTURE
```

Run vendor sample evaluation:

```bash
prediction-desk vendor-register-source \
  --vendor-name Kaggle \
  --dataset-name polymarket_sample \
  --dataset-version sample_v1 \
  --license-status SAMPLE_ONLY
```

---

## Key Safety Boundaries

The project currently does **not** support:

```text
live trading
real order placement
order cancellation
authenticated Polymarket CLOB trading
venue trading credentials
wallets
private keys
real account IDs
real positions
capital allocation
public-read scheduling
vendor production import
```

Anything that looks like execution is either:

```text
pre-trade review
paper simulation
research signal
workbench review artifact
```

---

## Current Project Classification

Current classification:

```text
Cloud-deployed prediction-market trading-station and research platform
with public-read ingestion, paper simulation, vendor-data evaluation,
and desk workbench review workflow.
```

Not yet:

```text
validated profitable trading system
live execution system
fund-ready production trading desk
```

---

## Next Milestone

The next major milestone should be:

```text
Live Paper Strategy Smoke Test v1
```

Goal:

```text
Use actual current public market data, not historical-only data,
to generate paper signals, pass them through pre-trade,
simulate paper outcomes, and review them in the workbench.
```

This should answer:

```text
Can the system generate a defensible paper-trading report from live market conditions?
Do spread, liquidity, and integrity filters make a difference?
Do paper fills occur under conservative assumptions?
Do workbench queue items help the human desk prioritize?
```

Still no live execution.

---

## Development Commands

Install:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
python -m ruff check .
python -m mypy
```

Run migrations:

```bash
DATABASE_URL=sqlite:////tmp/prediction_desk_dev.db scripts/migrate.sh
```

Docker smoke:

```bash
docker compose config
scripts/smoke_local.sh
scripts/smoke_docker.sh
```

Azure workbench status:

```bash
scripts/staging_workbench_status.sh
```

---

## Operational Notes

Current Azure scheduled fixture job:

```text
Job:
  pd-fixture-dataops-job

Cron:
  0 */12 * * *

Command:
  /app/scripts/run_fixture_dataops_job.sh

Mode:
  FIXTURE

Public-read:
  not scheduled
```

The fixture job is a staging heartbeat. It is not the main source of real research data.

The workbench should be used daily to capture human review feedback.

---

## Business Direction

The business is not “scrape prediction-market data.”

The business is:

```text
Build a prediction-market trading station that filters fake edge,
prioritizes real review candidates,
and eventually routes only admissible, risk-controlled opportunities
toward paper and then live execution.
```

The moat should be:

```text
contract interpretation
token-aware normalization
market-data quality
integrity analysis
equivalence/divergence logic
pre-trade admissibility
paper-execution realism
human review feedback
strategy evaluation discipline
```

Data is fuel. The decision engine is the product.
