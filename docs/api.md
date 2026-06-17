# prediction-desk API

The `prediction-desk` API is an internal research API. It exposes stored prediction-market
artifacts, deterministic resolution-corpus analysis, deterministic trust-verdict scoring,
point-in-time replay, canonical market data, fast-lane integrity assessments, contract
equivalence, equivalence-gated divergence context, pre-trade admissibility,
simulated-only paper execution, and deterministic strategy research. It does not trade,
place real orders, connect to venues, calculate real PnL, or call external APIs.

Market and trust-verdict routes are versioned under `/api/v1`. Operational routes remain
unversioned.

## Authentication

Authentication is controlled by runtime config:

- `REQUIRE_API_TOKEN=false`: bearer-token checks are skipped.
- `REQUIRE_API_TOKEN=true`: protected endpoints require
  `Authorization: Bearer <PREDICTION_DESK_API_TOKEN>`.
- `/healthz` is always public.
- `/readyz` follows the same token requirement as other protected endpoints.

Do not put real tokens in source control, Docker images, or Compose files.

## Request IDs And Errors

Every response includes `X-Request-ID`. If the caller provides `X-Request-ID`, the API
propagates it; otherwise the service generates one.

Common API failures use this envelope:

```json
{
  "error": {
    "code": "market_not_found",
    "message": "Market not found.",
    "request_id": "..."
  }
}
```

## Endpoints

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/healthz` | Public | Process liveness check. Does not touch the database. |
| `GET` | `/readyz` | Configurable | Database readiness check using `SELECT 1` plus migration-presence reporting. |
| `GET` | `/version` | Configurable | Service version, commit, and environment. |
| `GET` | `/api/v1/markets` | Configurable | Compact market list with optional filters. |
| `GET` | `/api/v1/markets/{market_id}` | Configurable | Full stored market object. |
| `GET` | `/api/v1/markets/{market_id}/rule-snapshots/latest` | Configurable | Latest stored rule snapshot. |
| `POST` | `/api/v1/markets/{market_id}/resolution/analyze-latest` | Configurable | Parse and score the latest rule snapshot, then persist the analysis. |
| `GET` | `/api/v1/markets/{market_id}/resolution/latest` | Configurable | Latest persisted resolution predicate and ambiguity assessment. |
| `GET` | `/api/v1/rule-snapshots/{rule_snapshot_id}/resolution` | Configurable | Persisted resolution analysis for one rule snapshot. |
| `POST` | `/api/v1/markets/{market_id}/rule-snapshots/diff-latest` | Configurable | Diff the latest two rule snapshots and persist the diff. |
| `GET` | `/api/v1/markets/{market_id}/trust-verdicts/latest` | Configurable | Latest stored trust verdict. |
| `POST` | `/api/v1/markets/{market_id}/trust-verdicts/recompute` | Configurable | Recompute and store a deterministic trust verdict from stored snapshots. |
| `GET` | `/api/v1/markets/{market_id}/market-data/latest` | Configurable | Latest canonical price, liquidity, and quality snapshots as of now or a supplied timestamp. |
| `GET` | `/api/v1/markets/{market_id}/market-data/prices` | Configurable | Paginated canonical price snapshots. |
| `GET` | `/api/v1/markets/{market_id}/market-data/liquidity` | Configurable | Paginated canonical liquidity snapshots. |
| `POST` | `/api/v1/markets/{market_id}/market-data/derive` | Configurable | Derive canonical market-data snapshots from stored orderbooks. |
| `POST` | `/api/v1/markets/{market_id}/data-quality/recompute` | Configurable | Compute and persist a market-data quality report. |
| `GET` | `/api/v1/markets/{market_id}/data-quality/latest` | Configurable | Latest persisted quality report as of now or a supplied timestamp. |
| `POST` | `/api/v1/integrity/analyze` | Configurable | Analyze one or more markets at one as-of timestamp. |
| `POST` | `/api/v1/integrity/runs` | Configurable | Run a synchronous integrity scan. |
| `GET` | `/api/v1/integrity/runs` | Configurable | List integrity scan runs. |
| `GET` | `/api/v1/integrity/runs/{integrity_run_id}` | Configurable | Read one integrity run. |
| `GET` | `/api/v1/integrity/runs/{integrity_run_id}/summary` | Configurable | Read one integrity run summary. |
| `GET` | `/api/v1/markets/{market_id}/integrity/latest` | Configurable | Latest integrity assessment as of now or a supplied timestamp. |
| `GET` | `/api/v1/markets/{market_id}/integrity/signals` | Configurable | Paginated integrity signals. |
| `GET` | `/api/v1/markets/{market_id}/integrity/assessments` | Configurable | Paginated integrity assessments. |
| `POST` | `/api/v1/markets/{market_id}/integrity/analyze` | Configurable | Build and persist one market integrity analysis. |
| `POST` | `/api/v1/equivalence/assess` | Configurable | Assess deterministic contract equivalence for one market pair. |
| `POST` | `/api/v1/equivalence/candidates` | Configurable | Generate deterministic candidate pairs. |
| `GET` | `/api/v1/equivalence/candidates` | Configurable | List candidate pairs. |
| `GET` | `/api/v1/equivalence/assessments` | Configurable | List persisted equivalence assessments. |
| `GET` | `/api/v1/equivalence/assessments/{equivalence_assessment_id}` | Configurable | Read one equivalence assessment. |
| `GET` | `/api/v1/equivalence/assessments/{equivalence_assessment_id}/outcomes` | Configurable | Read outcome mappings for one assessment. |
| `POST` | `/api/v1/equivalence/runs` | Configurable | Run a synchronous equivalence scan. |
| `GET` | `/api/v1/equivalence/runs` | Configurable | List equivalence runs. |
| `GET` | `/api/v1/equivalence/runs/{equivalence_run_id}` | Configurable | Read one equivalence run. |
| `GET` | `/api/v1/equivalence/runs/{equivalence_run_id}/summary` | Configurable | Read one equivalence run summary. |
| `GET` | `/api/v1/equivalence/classes` | Configurable | List equivalence classes. |
| `GET` | `/api/v1/markets/{market_id}/equivalence` | Configurable | List assessments involving one market. |
| `POST` | `/api/v1/divergence/analyze` | Configurable | Analyze equivalence-gated cross-venue divergence for one assessment or market. |
| `POST` | `/api/v1/divergence/runs` | Configurable | Run a synchronous divergence scan over selected equivalence assessments. |
| `GET` | `/api/v1/divergence/runs` | Configurable | List divergence runs. |
| `GET` | `/api/v1/divergence/runs/{divergence_run_id}` | Configurable | Read one divergence run. |
| `GET` | `/api/v1/divergence/runs/{divergence_run_id}/summary` | Configurable | Read one divergence run summary. |
| `GET` | `/api/v1/divergence/snapshots` | Configurable | List point-in-time divergence snapshots. |
| `GET` | `/api/v1/divergence/signals` | Configurable | List divergence signals. |
| `GET` | `/api/v1/divergence/assessments` | Configurable | List divergence assessments. |
| `GET` | `/api/v1/divergence/assessments/{divergence_assessment_id}` | Configurable | Read one divergence assessment. |
| `GET` | `/api/v1/markets/{market_id}/divergence/latest` | Configurable | Latest divergence assessment involving one market as of now or a supplied timestamp. |
| `GET` | `/api/v1/markets/{market_id}/divergence/assessments` | Configurable | List divergence assessments involving one market. |
| `GET` | `/api/v1/equivalence/assessments/{equivalence_assessment_id}/divergence/latest` | Configurable | Latest divergence assessment for one equivalence assessment. |
| `POST` | `/api/v1/equivalence/assessments/{equivalence_assessment_id}/divergence/analyze` | Configurable | Analyze divergence for one equivalence assessment. |
| `POST` | `/api/v1/pretrade/check` | Configurable | Evaluate one hypothetical trade intent for admissibility. |
| `POST` | `/api/v1/pretrade/check-market/{market_id}` | Configurable | Evaluate a default research-only intent for one market. |
| `GET` | `/api/v1/pretrade/decisions` | Configurable | List pre-trade decisions. |
| `GET` | `/api/v1/pretrade/decisions/{pretrade_decision_id}` | Configurable | Read one pre-trade decision. |
| `GET` | `/api/v1/markets/{market_id}/pretrade/latest` | Configurable | Latest pre-trade decision for a market as of now or a supplied timestamp. |
| `POST` | `/api/v1/pretrade/runs` | Configurable | Run synchronous default pre-trade checks. |
| `GET` | `/api/v1/pretrade/runs` | Configurable | List pre-trade runs. |
| `GET` | `/api/v1/pretrade/runs/{pretrade_run_id}` | Configurable | Read one pre-trade run. |
| `GET` | `/api/v1/pretrade/runs/{pretrade_run_id}/summary` | Configurable | Read one pre-trade run summary. |
| `POST` | `/api/v1/pretrade/policies/default` | Configurable | Create the deterministic default pre-trade policy if missing. |
| `GET` | `/api/v1/pretrade/policies` | Configurable | List pre-trade policies. |
| `GET` | `/api/v1/pretrade/policies/{policy_id}` | Configurable | Read one pre-trade policy. |
| `POST` | `/api/v1/pretrade/restrictions` | Configurable | Create a market restriction rule. |
| `GET` | `/api/v1/pretrade/restrictions` | Configurable | List market restriction rules. |
| `POST` | `/api/v1/pretrade/exposures` | Configurable | Create an abstract exposure snapshot. |
| `GET` | `/api/v1/pretrade/exposures` | Configurable | List abstract exposure snapshots. |
| `POST` | `/api/v1/paper/policies/default` | Configurable | Create the deterministic default paper policy if missing. |
| `GET` | `/api/v1/paper/policies` | Configurable | List simulated paper policies. |
| `GET` | `/api/v1/paper/policies/{paper_policy_id}` | Configurable | Read one simulated paper policy. |
| `POST` | `/api/v1/paper/simulate-intent` | Configurable | Simulate a hypothetical intent after pre-trade approval. |
| `GET` | `/api/v1/paper/orders` | Configurable | List simulated paper orders. |
| `GET` | `/api/v1/paper/orders/{paper_order_id}` | Configurable | Read one simulated paper order. |
| `GET` | `/api/v1/paper/fills` | Configurable | List simulated paper fills. |
| `GET` | `/api/v1/paper/positions` | Configurable | List simulated paper position snapshots. |
| `GET` | `/api/v1/markets/{market_id}/paper/position/latest` | Configurable | Latest simulated paper position as of now or a supplied timestamp. |
| `GET` | `/api/v1/paper/portfolio/latest` | Configurable | Latest simulated paper portfolio as of now or a supplied timestamp. |
| `GET` | `/api/v1/paper/portfolio/snapshots` | Configurable | List simulated paper portfolio snapshots. |
| `POST` | `/api/v1/paper/runs` | Configurable | Run a synchronous paper simulation batch. |
| `GET` | `/api/v1/paper/runs` | Configurable | List simulated paper runs. |
| `GET` | `/api/v1/paper/runs/{simulation_run_id}` | Configurable | Read one simulated paper run. |
| `GET` | `/api/v1/paper/runs/{simulation_run_id}/summary` | Configurable | Read one simulated paper run summary. |
| `POST` | `/api/v1/research/strategies/default` | Configurable | Create deterministic default research strategies if missing. |
| `GET` | `/api/v1/research/strategies` | Configurable | List research strategy definitions. |
| `GET` | `/api/v1/research/strategies/{strategy_id}` | Configurable | Read one research strategy definition. |
| `POST` | `/api/v1/research/features/build` | Configurable | Build as-of research feature snapshots for a market. |
| `GET` | `/api/v1/research/features` | Configurable | List research feature snapshots. |
| `POST` | `/api/v1/research/signals/generate` | Configurable | Generate deterministic research signals for a market. |
| `GET` | `/api/v1/research/signals` | Configurable | List stored research signals. |
| `POST` | `/api/v1/research/proposals/generate` | Configurable | Generate hypothetical research intent proposals. |
| `GET` | `/api/v1/research/proposals` | Configurable | List stored research proposals. |
| `POST` | `/api/v1/research/proposals/{proposal_id}/evaluate` | Configurable | Evaluate a proposal through pre-trade and optional paper simulation. |
| `GET` | `/api/v1/research/traces` | Configurable | List research decision traces. |
| `POST` | `/api/v1/research/runs` | Configurable | Run a synchronous strategy research simulation. |
| `GET` | `/api/v1/research/runs` | Configurable | List research runs. |
| `GET` | `/api/v1/research/runs/{research_run_id}` | Configurable | Read one research run. |
| `GET` | `/api/v1/research/runs/{research_run_id}/summary` | Configurable | Read one research run summary. |
| `GET` | `/api/v1/research/runs/{research_run_id}/attribution` | Configurable | Read one simulated research attribution report. |
| `GET` | `/api/v1/markets/{market_id}/research/latest` | Configurable | Latest research signals, proposals, and traces for one market. |
| `POST` | `/api/v1/replay/runs` | Configurable | Run a synchronous point-in-time admissibility replay. |
| `GET` | `/api/v1/replay/runs/{run_id}` | Configurable | Stored replay run metadata. |
| `GET` | `/api/v1/replay/runs/{run_id}/steps` | Configurable | Paginated replay steps. |
| `GET` | `/api/v1/replay/runs/{run_id}/summary` | Configurable | Stored replay summary. |
| `POST` | `/api/v1/ingestion/fixtures/{venue_name}` | Configurable | Ingest committed read-only venue fixtures. |
| `POST` | `/api/v1/ingestion/public-sample/{venue_name}` | Configurable | Manual read-only public sample ingestion. |
| `GET` | `/api/v1/ingestion/runs` | Configurable | List ingestion runs. |
| `GET` | `/api/v1/ingestion/runs/{ingestion_run_id}` | Configurable | Read one ingestion run. |
| `GET` | `/api/v1/ingestion/runs/{ingestion_run_id}/errors` | Configurable | Read ingestion errors. |
| `GET` | `/api/v1/ingestion/cursors` | Configurable | List run-once ingestion cursors. |
| `POST` | `/api/v1/ingestion/run-once` | Configurable | Run one fixture or explicit read-only public ingestion job. |
| `GET` | `/api/v1/venue-mappings` | Configurable | List external-to-canonical venue mappings. |

## Local Examples

Start the API locally:

```bash
prediction-desk init-db
prediction-desk load-sample-data
scripts/run_api.sh
```

Health:

```bash
curl http://localhost:8000/healthz
```

Readiness:

```bash
curl http://localhost:8000/readyz
```

List markets:

```bash
curl "http://localhost:8000/api/v1/markets?limit=100&offset=0"
```

Filter markets:

```bash
curl "http://localhost:8000/api/v1/markets?status=ACTIVE&venue_id=sample_research_venue"
```

Get one market:

```bash
curl http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01
```

Analyze the latest rule snapshot:

```bash
curl -X POST \
  http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01/resolution/analyze-latest
```

Read the latest persisted resolution analysis:

```bash
curl http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01/resolution/latest
```

Read resolution analysis for a specific rule snapshot:

```bash
curl \
  http://localhost:8000/api/v1/rule-snapshots/rule_sfo_rain_2026_09_01_v1/resolution
```

Diff the latest two rule snapshots for the sample rule-change market:

```bash
curl -X POST \
  http://localhost:8000/api/v1/markets/mkt_rate_cut_rule_change_2026/rule-snapshots/diff-latest
```

Recompute a trust verdict:

```bash
curl -X POST \
  http://localhost:8000/api/v1/markets/mkt_sfo_rain_2026_09_01/trust-verdicts/recompute
```

Run a tiny replay:

```bash
curl -X POST http://localhost:8000/api/v1/replay/runs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "sample replay",
    "policy_name": "trust_verdict_v1",
    "start_time": "2026-06-16T12:00:00Z",
    "end_time": "2026-06-16T13:00:00Z",
    "interval_seconds": 3600,
    "market_ids": ["mkt_cpi_yoy_at_least_3pct_2026_09"],
    "max_steps": 10,
    "persist_steps": true,
    "force_recompute_verdicts": true,
    "metadata": {}
  }'
```

Read replay outputs:

```bash
curl http://localhost:8000/api/v1/replay/runs/replay_run_...
curl http://localhost:8000/api/v1/replay/runs/replay_run_.../summary
curl "http://localhost:8000/api/v1/replay/runs/replay_run_.../steps?limit=50&offset=0"
```

Evaluate a hypothetical pre-trade intent:

```bash
curl -X POST http://localhost:8000/api/v1/pretrade/check \
  -H "Content-Type: application/json" \
  -d '{
    "market_id": "kalshi_market_kxweather_nyc_rain_20260930",
    "outcome_id": null,
    "venue_id": null,
    "strategy_context": "RESEARCH",
    "side": "BUY",
    "intent_type": "RESEARCH_ONLY",
    "requested_price": null,
    "requested_size_units": "1",
    "requested_notional_usd": null,
    "asof_timestamp": "2026-06-16T12:20:00Z",
    "policy_id": null,
    "force_recompute_context": false,
    "metadata": {}
  }'
```

Ingest read-only fixtures:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/fixtures/kalshi \
  -H "Content-Type: application/json" \
  -d '{"fixture_dir":null,"captured_at":null,"analyze_rules":true,"recompute_verdicts":true}'

curl -X POST http://localhost:8000/api/v1/ingestion/fixtures/polymarket \
  -H "Content-Type: application/json" \
  -d '{"fixture_dir":null,"captured_at":null,"analyze_rules":true,"recompute_verdicts":true}'
```

Manual public sample ingestion is disabled unless explicitly allowed:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/public-sample/kalshi \
  -H "Content-Type: application/json" \
  -d '{"limit":10,"allow_network":false,"analyze_rules":true,"recompute_verdicts":true}'
```

List ingestion artifacts:

```bash
curl http://localhost:8000/api/v1/ingestion/runs
curl http://localhost:8000/api/v1/ingestion/cursors
curl http://localhost:8000/api/v1/venue-mappings
```

Run one fixture ingestion job with canonical market-data derivation:

```bash
curl -X POST http://localhost:8000/api/v1/ingestion/run-once \
  -H "Content-Type: application/json" \
  -d '{
    "venue_name": "kalshi",
    "mode": "fixture",
    "limit": 10,
    "allow_network": false,
    "analyze_rules": true,
    "recompute_verdicts": true,
    "derive_market_data": true,
    "compute_quality": true,
    "metadata": {}
  }'
```

Read canonical market data and recompute quality:

```bash
curl http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/market-data/latest
curl "http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/market-data/prices?limit=50"
curl "http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/market-data/liquidity?limit=50"
curl -X POST \
  http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/data-quality/recompute \
  -H "Content-Type: application/json" \
  -d '{"asof_timestamp":"2026-06-16T12:45:00Z","freshness_threshold_seconds":3600,"wide_spread_threshold":"0.10"}'
curl "http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/data-quality/latest?asof_timestamp=2026-06-16T12:45:00Z"
```

Analyze fast-lane integrity signals:

```bash
curl -X POST \
  http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/integrity/analyze \
  -H "Content-Type: application/json" \
  -d '{"asof_timestamp":"2026-06-16T12:45:00Z","force":false,"thresholds":{}}'

curl "http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/integrity/latest?asof_timestamp=2026-06-16T12:45:00Z"
curl "http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/integrity/signals?limit=50"
```

Run an integrity scan and an integrity-gated replay:

```bash
curl -X POST http://localhost:8000/api/v1/integrity/runs \
  -H "Content-Type: application/json" \
  -d '{"name":"sample integrity scan","asof_timestamp":"2026-06-16T12:45:00Z","market_ids":["kalshi_market_kxweather_nyc_rain_20260930"],"max_steps":10,"force":false,"thresholds":{},"metadata":{}}'

curl -X POST http://localhost:8000/api/v1/replay/runs \
  -H "Content-Type: application/json" \
  -d '{"name":"integrity replay","policy_name":"integrity_gate_v1","start_time":"2026-06-16T12:45:00Z","end_time":"2026-06-16T13:45:00Z","interval_seconds":3600,"market_ids":["kalshi_market_kxweather_nyc_rain_20260930"],"max_steps":10,"persist_steps":true,"force_recompute_verdicts":false,"metadata":{}}'
```

Assess cross-venue contract equivalence:

```bash
curl -X POST http://localhost:8000/api/v1/equivalence/candidates \
  -H "Content-Type: application/json" \
  -d '{"market_ids":["kalshi_market_kxweather_nyc_rain_20260930","polymarket_market_0xrainnycsep2026"],"asof_timestamp":"2026-06-16T12:45:00Z","min_candidate_score":40,"max_pairs":10,"force":false}'

curl -X POST http://localhost:8000/api/v1/equivalence/assess \
  -H "Content-Type: application/json" \
  -d '{"left_market_id":"kalshi_market_kxweather_nyc_rain_20260930","right_market_id":"polymarket_market_0xrainnycsep2026","asof_timestamp":"2026-06-16T12:45:00Z","force":false,"config":{}}'

curl -X POST http://localhost:8000/api/v1/equivalence/runs \
  -H "Content-Type: application/json" \
  -d '{"name":"sample equivalence scan","asof_timestamp":"2026-06-16T12:45:00Z","market_ids":["kalshi_market_kxweather_nyc_rain_20260930","polymarket_market_0xrainnycsep2026"],"min_candidate_score":40,"max_pairs":10,"build_classes":true,"force":false,"metadata":{}}'

curl http://localhost:8000/api/v1/equivalence/classes
curl "http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/equivalence?limit=50"
```

With token auth enabled:

```bash
curl -H "Authorization: Bearer local-dev-token" http://localhost:8000/version
```

Resolution endpoints read stored rule snapshots and persist deterministic parser,
ambiguity, and diff artifacts. Trust-verdict recomputation reads the stored market, latest
rule snapshot, latest order book snapshot, and any safely generated ambiguity assessment.
Replay endpoints read stored snapshots at or before each replay timestamp and persist
admissibility decisions with deterministic hashes. Canonical market-data and integrity
as-of lookups use `available_at <= asof_timestamp`, not venue observation time. Integrity
signals are risk/admissibility signals, not alpha claims or proof of manipulation.
Equivalence assessments are contract-comparison/risk objects, not trading instructions.
Divergence assessments are equivalence-gated research context. They do not fetch venue data,
place real orders, calculate real PnL, or create any trading instruction. Paper execution
endpoints create simulated artifacts only and require pre-trade approval first. This API is
internal and is not a live execution service. Ingestion
endpoints archive and normalize public-shape data only; they do not use venue credentials
or authenticated trading endpoints.

### Divergence

```bash
curl -X POST http://localhost:8000/api/v1/divergence/analyze \
  -H "Content-Type: application/json" \
  -d '{"market_id":"kalshi_market_kxweather_nyc_rain_20260930","asof_timestamp":"2026-06-16T12:20:00Z","force":false,"config":{}}'

curl -X POST http://localhost:8000/api/v1/divergence/runs \
  -H "Content-Type: application/json" \
  -d '{"name":"sample divergence scan","asof_timestamp":"2026-06-16T12:20:00Z","market_ids":["kalshi_market_kxweather_nyc_rain_20260930"],"max_pairs":10,"force":false,"config":{},"metadata":{}}'

curl http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/divergence/latest
```

Endpoints:

- `POST /api/v1/divergence/analyze`
- `POST /api/v1/divergence/runs`
- `GET /api/v1/divergence/runs`
- `GET /api/v1/divergence/runs/{divergence_run_id}`
- `GET /api/v1/divergence/runs/{divergence_run_id}/summary`
- `GET /api/v1/divergence/snapshots`
- `GET /api/v1/divergence/signals`
- `GET /api/v1/divergence/assessments`
- `GET /api/v1/divergence/assessments/{divergence_assessment_id}`
- `GET /api/v1/markets/{market_id}/divergence/latest`
- `GET /api/v1/markets/{market_id}/divergence/assessments`
- `GET /api/v1/equivalence/assessments/{equivalence_assessment_id}/divergence/latest`
- `POST /api/v1/equivalence/assessments/{equivalence_assessment_id}/divergence/analyze`

### Paper Execution

Paper endpoints are simulated-only. `POST /paper/simulate-intent` first evaluates the
pre-trade gate, then creates a `PaperOrder` and any deterministic simulated fills allowed
by the paper policy and as-of market data.

```bash
curl -X POST http://localhost:8000/api/v1/paper/policies/default

curl -X POST http://localhost:8000/api/v1/paper/simulate-intent \
  -H "Content-Type: application/json" \
  -d '{"market_id":"kalshi_market_kxweather_nyc_rain_20260930","outcome_id":null,"venue_id":null,"strategy_context":"RESEARCH","side":"BUY","intent_type":"AGGRESSIVE_LIMIT","requested_price":"0.60","requested_size_units":"1","requested_notional_usd":null,"asof_timestamp":"2026-06-16T12:20:00Z","paper_policy_id":null,"force_recompute_pretrade":false,"metadata":{}}'

curl http://localhost:8000/api/v1/paper/orders
curl http://localhost:8000/api/v1/paper/fills
curl http://localhost:8000/api/v1/markets/kalshi_market_kxweather_nyc_rain_20260930/paper/position/latest
curl http://localhost:8000/api/v1/paper/portfolio/latest
```

Endpoints:

- `POST /api/v1/paper/policies/default`
- `GET /api/v1/paper/policies`
- `GET /api/v1/paper/policies/{paper_policy_id}`
- `POST /api/v1/paper/simulate-intent`
- `GET /api/v1/paper/orders`
- `GET /api/v1/paper/orders/{paper_order_id}`
- `GET /api/v1/paper/fills`
- `GET /api/v1/paper/positions`
- `GET /api/v1/markets/{market_id}/paper/position/latest`
- `GET /api/v1/paper/portfolio/latest`
- `GET /api/v1/paper/portfolio/snapshots`
- `POST /api/v1/paper/runs`
- `GET /api/v1/paper/runs`
- `GET /api/v1/paper/runs/{simulation_run_id}`
- `GET /api/v1/paper/runs/{simulation_run_id}/summary`

### Strategy Research

Research endpoints build as-of feature snapshots, generate research signals and
hypothetical proposals, evaluate proposals through pre-trade, optionally call paper
simulation, and store simulated attribution. They do not access live venues or bypass the
gate.

```bash
curl -X POST http://localhost:8000/api/v1/research/strategies/default

curl -X POST http://localhost:8000/api/v1/research/features/build \
  -H "Content-Type: application/json" \
  -d '{"market_id":"mkt_cpi_yoy_at_least_3pct_2026_09","asof_timestamp":"2026-06-16T12:00:00Z","force":true}'

curl -X POST http://localhost:8000/api/v1/research/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"market_id":"mkt_cpi_yoy_at_least_3pct_2026_09","asof_timestamp":"2026-06-16T12:00:00Z","strategy_ids":["research_strategy_baseline_research_only_v1"],"force":false}'

curl -X POST http://localhost:8000/api/v1/research/runs \
  -H "Content-Type: application/json" \
  -d '{"name":"sample research run","start_time":"2026-06-16T12:00:00Z","end_time":"2026-06-16T12:00:00Z","interval_seconds":3600,"strategy_ids":["research_strategy_baseline_research_only_v1"],"market_ids":["mkt_cpi_yoy_at_least_3pct_2026_09"],"max_steps":10,"max_proposals":10,"enable_paper_simulation":false,"initial_cash_simulated":"1000","metadata":{}}'
```

Endpoints:

- `POST /api/v1/research/strategies/default`
- `GET /api/v1/research/strategies`
- `GET /api/v1/research/strategies/{strategy_id}`
- `POST /api/v1/research/features/build`
- `GET /api/v1/research/features`
- `POST /api/v1/research/signals/generate`
- `GET /api/v1/research/signals`
- `POST /api/v1/research/proposals/generate`
- `GET /api/v1/research/proposals`
- `POST /api/v1/research/proposals/{proposal_id}/evaluate`
- `GET /api/v1/research/traces`
- `POST /api/v1/research/runs`
- `GET /api/v1/research/runs`
- `GET /api/v1/research/runs/{research_run_id}`
- `GET /api/v1/research/runs/{research_run_id}/summary`
- `GET /api/v1/research/runs/{research_run_id}/attribution`
- `GET /api/v1/markets/{market_id}/research/latest`
