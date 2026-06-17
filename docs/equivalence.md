# Cross-Venue Equivalence Engine

Cross-venue price comparison is only meaningful after the contracts are comparable.
`prediction-desk` treats equivalence as a deterministic contract-comparison object, not
as a PnL, execution, or alpha signal.

The v1 engine uses canonical market metadata, outcomes, rule snapshots, resolution
predicates, ambiguity assessments, resolution sources, settlement authority text, thresholds,
time windows, and timezone evidence. It does not call venues, news APIs, LLMs, or any
external service.

## Models

- `EquivalenceCandidate`: a cheap pre-filter pair from title/key-term/category similarity.
- `MarketEquivalenceAssessment`: the persisted pairwise comparison with dimension scores,
  hard mismatch flags, status, permission, evidence, input hash, and output hash.
- `OutcomeEquivalenceMapping`: deterministic outcome relation mapping such as `SAME`,
  `INVERSE`, `PARTIAL`, `UNKNOWN`, or `NOT_EQUIVALENT`.
- `EquivalenceClass`: a deterministic grouping of markets whose pairwise assessments are
  comparable enough for research comparison.
- `EquivalenceRun`: a synchronous run-once scan that creates candidates, assessments,
  optional classes, and a summary.

## Dimensions

The engine scores:

- title similarity
- event identity
- outcome structure
- outcome mapping
- predicate similarity
- resolution source alignment
- settlement authority alignment
- temporal alignment
- threshold alignment
- timezone alignment
- ambiguity compatibility
- venue rule compatibility

Hard mismatch flags include resolution source mismatch, settlement authority mismatch,
deadline mismatch, timezone mismatch, threshold mismatch, high ambiguity, and insufficient
rule data. Missing or ambiguous rule data pushes toward `NEEDS_REVIEW` and
`MANUAL_REVIEW`.

## Permissions

- `COMPARABLE`: strong equivalence.
- `COMPARABLE_WITH_HAIRCUT`: near-equivalent contract, suitable only for conservative
  research comparison.
- `MANUAL_REVIEW`: related or insufficiently specified pair.
- `DO_NOT_COMPARE`: hard mismatch or low support.

The permission is an admissibility/risk label. It is not an instruction to trade.

## No-Lookahead Behavior

Assessments are generated at an explicit `asof_timestamp` and persisted with `available_at`.
Services fetch only rule snapshots, resolution analyses, ambiguity assessments, and market
state available at or before the as-of timestamp. Replay records latest equivalence metadata
in `ReplayStep.metadata` but does not change actions in v1.

## Trust Verdict Metadata

Trust verdict recompute stores equivalence metadata when assessments already exist as of the
verdict timestamp:

- comparable market count
- manual-review equivalence count
- do-not-compare equivalence count
- latest equivalence assessment IDs

Equivalence does not alter trust-verdict actions in v1. Cross-venue divergence signals are a
separate downstream research context.

When divergence assessments exist as of a verdict timestamp, trust verdicts store only
divergence metadata such as assessment IDs, status counts, and max divergence score. They do
not change actions based on divergence in v1.

## CLI

```bash
prediction-desk ingestion-run-once --venue kalshi
prediction-desk ingestion-run-once --venue polymarket

prediction-desk equivalence-candidates \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --market-id polymarket_market_0xrainnycsep2026 \
  --asof 2026-06-16T12:45:00Z

prediction-desk equivalence-assess \
  --left-market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --right-market-id polymarket_market_0xrainnycsep2026 \
  --asof 2026-06-16T12:45:00Z

prediction-desk equivalence-run \
  --market-id kalshi_market_kxweather_nyc_rain_20260930 \
  --market-id polymarket_market_0xrainnycsep2026 \
  --asof 2026-06-16T12:45:00Z \
  --max-pairs 10
```

## API

Equivalence endpoints live under `/api/v1/equivalence`:

- `POST /equivalence/assess`
- `POST /equivalence/candidates`
- `GET /equivalence/candidates`
- `GET /equivalence/assessments`
- `GET /equivalence/assessments/{equivalence_assessment_id}`
- `GET /equivalence/assessments/{equivalence_assessment_id}/outcomes`
- `POST /equivalence/runs`
- `GET /equivalence/runs`
- `GET /equivalence/runs/{equivalence_run_id}`
- `GET /equivalence/runs/{equivalence_run_id}/summary`
- `GET /equivalence/classes`
- `GET /markets/{market_id}/equivalence`

## Limitations

v1 uses conservative deterministic heuristics and simple text matching. It does not infer
semantic equivalence using LLMs, web search, venue calls, or news. It does not use price
discrepancies to infer equivalence, and it does not compute execution, spread trading,
PnL, EV, or trading instructions.

Later phases can use these objects for cross-venue divergence signals, market-making filters,
pre-trade gates, execution simulator inputs, and MiroFish slow-lane feature snapshots.

See [divergence_signals.md](divergence_signals.md) for the downstream equivalence-gated
divergence layer. See [pretrade_gate.md](pretrade_gate.md) for how equivalence and
divergence context feed admissibility decisions.
