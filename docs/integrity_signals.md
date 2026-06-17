# Fast-Lane Integrity Signals v1

Fast-lane integrity signals are deterministic risk and admissibility signals. They are not
alpha claims, performance forecasts, or proof of manipulation. They are designed to help
answer whether a market should be allowed, size-reduced, passive-only, manually reviewed,
or blocked at a point in time.

This layer does not call news APIs, venue APIs, LLMs, MiroFish, or external services. It
does not place orders, simulate fills, calculate PnL, or use credentials.

## No-Lookahead Rule

Integrity features use only data available at or before the as-of timestamp:

- canonical price/liquidity snapshots use `available_at <= asof_timestamp`
- data-quality reports use as-of report timestamps
- rule snapshots use `captured_at <= asof_timestamp`
- rule diffs use `created_at <= asof_timestamp`

`observed_at` alone never makes market data replay-available.

## Models

`MarketFeatureSnapshot` is the deterministic feature view for one market at one as-of
timestamp. It records latest and previous price/liquidity IDs, quality report ID, rule
snapshot hash, rule-diff ID, spread, depth, imbalance, freshness, price changes, spread
changes, depth changes, rule-change age, and a deterministic input hash.

`IntegritySignal` is one triggered heuristic. It records category, severity, score,
action hint, reason code, message, evidence, input hash, and output hash.

`IntegrityAssessment` aggregates signals into category scores, an overall risk score, max
severity, most restrictive action hint, reason codes, and deterministic hashes.

`IntegrityRun` and `IntegrityRunSummary` record synchronous run-once scans across one
timestamp or a historical interval. They are not daemons.

## Signal Categories And Thresholds

Implemented v1 signals:

- `EMPTY_BOOK`: critical orderbook-structure risk, `NO_TRADE`
- `CROSSED_BOOK`: critical orderbook-structure risk, `NO_TRADE`
- `ONE_SIDED_BOOK`: liquidity anomaly, `PASSIVE_ONLY`
- `WIDE_SPREAD`: spread above `0.10` by default, `PASSIVE_ONLY`
- `SPREAD_WIDENING`: spread increase above `0.05` by default
- `DEPTH_COLLAPSE`: depth change at or below `-50%` by default
- `PRICE_JUMP`: absolute price or mid move above `0.05` warning or `0.10` error
- `STALE_MARKET_DATA`: freshness above the configured seconds threshold
- `EXTREME_BOOK_IMBALANCE`: heuristic manipulation-risk proxy only, not proof
- `LOW_DATA_QUALITY`: quality score below `70`, `40`, or `20`
- `RULE_CHANGED_RECENTLY`: rule diff within the feature lookback window
- `RULE_CHANGE_PRICE_COUPLING`: recent rule change plus price move above `0.05`

All thresholds are deterministic and can be supplied per request or run.

## Aggregation And Action Hints

Aggregation uses max score by category and max category score for overall risk. Severity is
the maximum severity among triggered signals. Action hint is the most restrictive hint:

`NO_TRADE > MANUAL_REVIEW > PASSIVE_ONLY > ALLOW_SMALLER_SIZE > ALLOW/NONE`

Reason codes are de-duplicated and sorted.

## Trust Verdicts

Trust-verdict recomputation preserves existing behavior when no integrity assessment is
available. When an assessment exists as of the verdict timestamp, the verdict:

- adds integrity reason codes
- stores the assessment ID and scores in metadata
- applies the action hint conservatively
- raises risk scores where appropriate
- reduces quality-style scores such as price integrity and information freshness by
  corresponding integrity risk

## Replay

Replay steps record the latest integrity assessment available at the replay timestamp in
step metadata. The `integrity_gate_v1` replay policy uses integrity action hints directly.
If no assessment exists, it returns `MANUAL_REVIEW` with `MISSING_INTEGRITY_ASSESSMENT`.

## CLI

```bash
prediction-desk integrity-analyze --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk integrity-run --asof 2026-06-16T12:45:00Z --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk integrity-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk integrity-signals --market-id kalshi_market_kxweather_nyc_rain_20260930
```

## API

Integrity endpoints are under `/api/v1`:

- `POST /api/v1/integrity/analyze`
- `POST /api/v1/integrity/runs`
- `GET /api/v1/integrity/runs`
- `GET /api/v1/integrity/runs/{integrity_run_id}`
- `GET /api/v1/integrity/runs/{integrity_run_id}/summary`
- `GET /api/v1/markets/{market_id}/integrity/latest`
- `GET /api/v1/markets/{market_id}/integrity/signals`
- `GET /api/v1/markets/{market_id}/integrity/assessments`
- `POST /api/v1/markets/{market_id}/integrity/analyze`

## Future Use

This layer now coexists with cross-venue equivalence. Integrity assessments describe
market-data/rule-change risk; equivalence assessments describe whether contracts are
comparable enough to compare. Neither is an alpha claim, execution instruction, or proof of
manipulation.

Cross-venue divergence assessments can attach integrity context when a comparable pair has
stale data, low quality, wide spreads, or high integrity risk on either side. Integrity still
does not create a trade instruction; it only informs admissibility and review context.

Later phases can combine integrity and equivalence with market-making filters, pre-trade
gates, execution simulation, and future MiroFish slow-lane feature snapshots. Those are not
implemented in v1.

See [equivalence.md](equivalence.md) for the contract-comparison model and
[divergence_signals.md](divergence_signals.md) for equivalence-gated divergence context.
See [pretrade_gate.md](pretrade_gate.md) for how integrity assessments feed the
admissibility gate.
