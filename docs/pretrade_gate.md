# Pre-Trade Gate v1

The pre-trade gate evaluates a hypothetical `TradeIntent` and returns an admissibility
decision. It is a risk-control and research layer. It does not create, route, sign, place,
cancel, or prepare real venue orders.

## Purpose

The gate answers:

> At timestamp T, using only data available at or before T, would this hypothetical intent
> be allowed, reduced, restricted to passive use, sent to manual review, or blocked?

It combines stored trust verdicts, resolution risk, canonical market-data quality,
integrity assessments, equivalence/divergence context, venue/market restrictions, and
abstract exposure limits.

## Models

`TradeIntent` is a hypothetical request. It includes market/outcome/venue references,
strategy context, side, intent type, requested price, requested size units, as-of timestamp,
and metadata. It intentionally excludes venue order IDs, account IDs, wallet addresses,
private keys, and credentials.

`PreTradePolicy` stores deterministic gate thresholds. The default v1 policy is
`default_pretrade_policy` / `v1`, with conservative size caps, required active markets,
required rule snapshots, optional trust-verdict and market-data quality requirements, and
limits for resolution, integrity, divergence, staleness, and spread context.

`MarketRestrictionRule` stores active restriction rules. `NO_TRADE` is a hard blocker,
`MANUAL_REVIEW` forces review, `PASSIVE_ONLY` restricts intent type, and `SIZE_LIMIT`
reduces the maximum allowed size when configured.

`ExposureSnapshot` is abstract exposure state for policy testing. It is not linked to real
exchange accounts and stores no account identifiers or credentials.

`PreTradeInputSnapshot` records every as-of input reference used by the gate: rule snapshot,
trust verdict, market-data quality, integrity, equivalence, divergence, price/liquidity,
exposure, policy, restrictions, scores, counts, and deterministic input hash.

`PreTradeDecision` records the final action, final allowed size, hard blockers, warnings,
reason codes, evidence, and deterministic output hash.

`PreTradeRun` and `PreTradeRunSummary` support synchronous batch checks over selected
markets.

## Actions

- `ALLOW`: requested size is allowed.
- `ALLOW_SMALLER_SIZE`: allowed size is below requested size.
- `PASSIVE_ONLY`: only passive/research-safe use is allowed; aggressive or market-like
  intents become manual review.
- `MANUAL_REVIEW`: do not allow automated use.
- `NO_TRADE`: hard block.

Hard blockers are separated from warnings. Hard blockers override soft scores.

## No-Lookahead Behavior

All lookups are as-of safe:

- rule snapshots use `captured_at <= asof_timestamp`
- trust verdicts use `asof_timestamp <= intent.asof_timestamp`
- market-data, quality, integrity, equivalence, divergence, and pre-trade decisions use
  `available_at <= asof_timestamp`
- exposure snapshots use `asof_timestamp <= intent.asof_timestamp`
- restriction rules respect active/effective time windows

Missing critical data pushes toward `MANUAL_REVIEW` or `NO_TRADE` depending on policy.

## Inputs To The Gate

Resolution risk can block or force review when it exceeds policy limits.

Market-data quality can force review for low scores, stale data, or excessive spread.

Integrity assessments can force review or block when action hints and risk scores are
severe.

Equivalence and divergence are required for `CROSS_VENUE_COMPARISON` context. Missing
context forces manual review. `DO_NOT_COMPARE` divergence context blocks.

Exposure limits use abstract units only. Unknown exposure is allowed by the default v1 policy
with `UNKNOWN_EXPOSURE_ALLOWED_BY_POLICY`, but stricter policies can force review.

## CLI

```bash
prediction-desk pretrade-create-default-policy

prediction-desk pretrade-check \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --strategy-context RESEARCH \
  --intent-type RESEARCH_ONLY \
  --requested-size-units 1

prediction-desk pretrade-run \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --asof 2026-06-16T12:20:00Z \
  --max-checks 10

prediction-desk pretrade-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk pretrade-decisions --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk pretrade-add-restriction --restriction-type NO_TRADE --scope-type MARKET \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 --reason-code MANUAL_BLOCK
prediction-desk pretrade-add-exposure --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --market-exposure-units 0
```

## API

Pre-trade endpoints live under `/api/v1`:

- `POST /pretrade/check`
- `POST /pretrade/check-market/{market_id}`
- `GET /pretrade/decisions`
- `GET /pretrade/decisions/{pretrade_decision_id}`
- `GET /markets/{market_id}/pretrade/latest`
- `POST /pretrade/runs`
- `GET /pretrade/runs`
- `GET /pretrade/runs/{pretrade_run_id}`
- `GET /pretrade/runs/{pretrade_run_id}/summary`
- `POST /pretrade/policies/default`
- `GET /pretrade/policies`
- `GET /pretrade/policies/{policy_id}`
- `POST /pretrade/restrictions`
- `GET /pretrade/restrictions`
- `POST /pretrade/exposures`
- `GET /pretrade/exposures`

Example check:

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

## Replay

Replay policy `pretrade_gate_v1` builds a default `RESEARCH_ONLY` intent at each replay
timestamp and runs the pre-trade gate. Replay steps record the pre-trade decision ID, final
allowed size, hard blockers, warnings, and reason codes in metadata. This remains an
admissibility replay; it does not simulate fills or calculate PnL.

Paper execution uses this gate as a prerequisite. A paper order can only be accepted after
the gate has produced an admissible simulated-only decision under the active pre-trade
policy.

## Future Use

This layer supports the paper execution simulator and can later feed an execution
management system, strategy research workflows, market-making filters, and MiroFish
slow-lane feature snapshots. Real order routing and real account exposure remain outside
v1.

The strategy research harness converts `ResearchIntentProposal` objects into `TradeIntent`
objects and must pass through this gate before optional paper simulation.

See [paper_execution.md](paper_execution.md) for the simulated-only downstream layer and
[strategy_research.md](strategy_research.md) for research hypotheses and proposal traces.
