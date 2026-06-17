# Cross-Venue Divergence Signals v1

Cross-venue divergence signals compare prices only after the equivalence engine has said
the contracts are comparable enough for research comparison. A price gap without contract
equivalence is treated as uninterpretable context, not as a signal.

This layer is for research and admissibility review. It does not place orders, size trades,
simulate fills, calculate PnL, estimate EV, or issue trading instructions. It does not call
venues, news, LLMs, or external services.

## Models

`CrossVenueDivergenceSnapshot` is the point-in-time aligned comparison for one outcome
mapping across two equivalent markets. It records the equivalence assessment, outcome
mapping, as-of timestamp, input price/liquidity/quality/integrity IDs, aligned prices,
mid gaps, spread-adjusted gap, data-quality context, and deterministic hashes.

`CrossVenueDivergenceSignal` is one triggered issue such as a price gap, stale side,
low-liquidity context, low data quality, high integrity risk, or equivalence context that
requires review.

`CrossVenueDivergenceAssessment` aggregates signals into category scores, a status,
severity, action hint, reason codes, and deterministic hashes.

`CrossVenueDivergenceRun` and `CrossVenueDivergenceRunSummary` record synchronous run-once
scans. They are not daemons.

## Price Alignment

Outcome mappings determine how the right side is aligned:

- `SAME`: right price, bid, and ask are used directly.
- `INVERSE`: right price is converted to `1 - right_price`; right bid/ask are converted
  conservatively with `aligned_bid = 1 - right_ask` and `aligned_ask = 1 - right_bid`.
- `PARTIAL`, `UNKNOWN`, and `NOT_EQUIVALENT`: prices are not aligned.

The snapshot computes signed and absolute mid/price gaps, gap bps, combined spread, and
spread-adjusted gap. Spread-adjusted gap subtracts half of combined spread from the absolute
mid gap and floors at zero.

## Signals

Implemented v1 signals include:

- `DO_NOT_COMPARE_CONTEXT`
- `MANUAL_REVIEW_EQUIVALENCE_CONTEXT`
- `EQUIVALENT_PRICE_GAP`
- `SPREAD_ADJUSTED_DIVERGENCE`
- `STALE_SIDE_DIVERGENCE`
- `LOW_LIQUIDITY_DIVERGENCE`
- `LOW_DATA_QUALITY_DIVERGENCE`
- `HIGH_INTEGRITY_RISK_DIVERGENCE`
- `COMPARABLE_WITH_HAIRCUT_DIVERGENCE`
- `PERSISTENT_DIVERGENCE`

Default thresholds are deterministic: watch gap `0.03`, material gap `0.05`, critical gap
`0.10`, spread-adjusted gap `0.02`, low quality below `70`, and high integrity risk at
`70` or above.

## Status And Action Hints

Statuses are `NO_DIVERGENCE`, `WATCH`, `MATERIAL_DIVERGENCE`, `NEEDS_REVIEW`, and
`DO_NOT_COMPARE`.

Action hints are not trading commands. The most restrictive hint wins:

`DO_NOT_COMPARE > MANUAL_REVIEW > RESEARCH > WATCH > NONE`

Low equivalence confidence, stale data, weak liquidity, low quality, or integrity context
pushes assessments toward review instead of comparable price-gap interpretation.

## No-Lookahead Behavior

Divergence uses only data available at or before the as-of timestamp:

- market-data snapshots use `available_at <= asof_timestamp`
- data-quality reports use `available_at <= asof_timestamp`
- integrity assessments use `available_at <= asof_timestamp`
- equivalence assessments use `available_at <= asof_timestamp`

`observed_at` alone never makes market data available for replay.

## Trust Verdicts And Replay

Trust-verdict recompute attaches divergence metadata when assessments exist as of the
verdict timestamp. It records assessment IDs, status counts, and max divergence score, but
does not change actions in v1.

Replay steps attach divergence metadata available at the replay timestamp. Replay policies
do not change decisions based on divergence in v1.

The pre-trade gate can use divergence context for admissibility review. In cross-venue
comparison context, missing divergence/equivalence context forces review, and
`DO_NOT_COMPARE` divergence context blocks the hypothetical intent.

## CLI

```bash
prediction-desk divergence-analyze \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --asof 2026-06-16T12:20:00Z

prediction-desk divergence-run \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --asof 2026-06-16T12:20:00Z \
  --max-pairs 10

prediction-desk divergence-latest --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk divergence-signals --market-id kalshi_market_kxweather_nyc_rain_20260930
prediction-desk divergence-assessments --market-id kalshi_market_kxweather_nyc_rain_20260930
```

## API

Divergence endpoints live under `/api/v1`:

- `POST /divergence/analyze`
- `POST /divergence/runs`
- `GET /divergence/runs`
- `GET /divergence/runs/{divergence_run_id}`
- `GET /divergence/runs/{divergence_run_id}/summary`
- `GET /divergence/snapshots`
- `GET /divergence/signals`
- `GET /divergence/assessments`
- `GET /divergence/assessments/{divergence_assessment_id}`
- `GET /markets/{market_id}/divergence/latest`
- `GET /markets/{market_id}/divergence/assessments`
- `GET /equivalence/assessments/{equivalence_assessment_id}/divergence/latest`
- `POST /equivalence/assessments/{equivalence_assessment_id}/divergence/analyze`

## Future Use

This layer supports pre-trade gate context and simulated paper-execution context. It can
later support market-making filters, strategy research, and MiroFish slow-lane feature
snapshots. Real execution remains out of scope in v1.

See [pretrade_gate.md](pretrade_gate.md) for the downstream admissibility gate and
[paper_execution.md](paper_execution.md) for simulated-only paper execution. See
[strategy_research.md](strategy_research.md) for how divergence context can become a
hypothetical research signal without bypassing the gate.
