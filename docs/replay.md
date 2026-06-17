# Point-In-Time Replay Harness v1

The replay harness answers:

> At timestamp T, using only data available at or before T, what trust verdict and
> admissibility action would the system have produced for this market?

Replay v1 is an admissibility and research replay engine. It is not a PnL engine, an
execution simulator, or a trading service.

## No-Lookahead Rule

Every replay lookup is as-of safe:

- Rule snapshots use `captured_at <= asof_timestamp`.
- Order book snapshots use `captured_at <= asof_timestamp`.
- Canonical price and liquidity snapshots use `available_at <= asof_timestamp`.
- `observed_at` alone never makes historical market data available for replay.
- Resolution predicate and ambiguity analysis use the selected as-of rule snapshot.
- Trust verdicts generated during replay use the replay timestamp, not wall-clock time.
- Replay bookkeeping uses `created_at` only for replay run, step, and summary records.

The runner uses inclusive timestamps: `start_time <= T <= end_time`.

Read-only fixture ingestion can create historical rule snapshots and orderbooks for replay,
but the runner still applies the same as-of filters and never calls live venues.

## Models

`ReplayRun` records the run configuration, policy, market set, interval, max-step guardrail,
and status.

`ReplayStep` records one market decision at one timestamp, including selected snapshot IDs,
rule hash, resolution analysis IDs, trust verdict ID, latest canonical market-data IDs and
quality metadata, latest integrity assessment metadata, scores, action, reason codes,
latest equivalence assessment IDs/counts, input hash, output hash, and any step error.

`ReplayRunSummary` aggregates step counts, action counts, average scores, admissibility
rates, and v1 exposure units.

`ReplayDecision` is the policy output. It is Pydantic-only and is not persisted separately.

## Policies

`allow_all_v1` always returns `ALLOW` and `allowed_size_multiplier=1.0`. It is a baseline
for comparing policy effect.

`trust_verdict_v1` uses the deterministic `TrustVerdict` action and maps actions to v1
allowed-size multipliers:

- `ALLOW`: `1.0`
- `ALLOW_SMALLER_SIZE`: `0.5`
- `PASSIVE_ONLY`: `0.25`
- `MANUAL_REVIEW`: `0.0`
- `NO_TRADE`: `0.0`

`resolution_risk_only_v1` isolates the impact of resolution risk and ambiguity:

- resolution risk `>= 80`: `NO_TRADE`
- resolution risk `>= 50`: `MANUAL_REVIEW`
- otherwise: `ALLOW`

`integrity_gate_v1` uses the latest integrity assessment available at the replay timestamp:

- missing assessment: `MANUAL_REVIEW`
- `NO_TRADE` action hint: `NO_TRADE`
- `MANUAL_REVIEW` action hint: `MANUAL_REVIEW`
- `PASSIVE_ONLY` action hint: `PASSIVE_ONLY`
- `ALLOW_SMALLER_SIZE` action hint: `ALLOW_SMALLER_SIZE`
- `ALLOW` or `NONE`: `ALLOW`

`pretrade_gate_v1` builds a default `RESEARCH_ONLY` trade intent for each market and
timestamp, runs the pre-trade gate, and maps the resulting pre-trade action to replay
actions. Replay step metadata includes the pre-trade decision ID, final allowed size, hard
blockers, warnings, and reason codes.

Equivalence metadata is recorded on replay steps when available, including latest assessment
IDs involving the market and comparable/manual-review/do-not-compare counts. V1 replay
policies do not change actions based on equivalence.

Divergence metadata is also recorded when as-of divergence assessments exist, including
latest assessment IDs, watch/material/needs-review/do-not-compare counts, and max
divergence score. V1 replay policies do not change actions based on divergence.

Research metadata is recorded when as-of research outputs exist, including latest signal,
proposal, and trace IDs plus pre-trade action counts. `research_policy_v1` maps the latest
stored research trace pre-trade action to a replay action, but it does not generate new
signals, proposals, paper orders, or fills inside replay.

Scenario metadata is recorded when an as-of scenario feature exists, including the latest
scenario feature snapshot ID, confidence score, uncertainty score, and reason codes. V1
replay policies do not change actions based on scenario features.

## Metrics

Replay v1 calculates:

- total steps and errored steps
- action counts
- average trust-verdict scores
- no-trade, manual-review, passive-only, and allow rates
- allowed and blocked exposure units
- markets replayed

Exposure units are not capital and not PnL. V1 does not calculate returns, Sharpe ratios,
fills, slippage, or performance metrics.

## CLI

```bash
prediction-desk replay-run \
  --policy trust_verdict_v1 \
  --start 2026-06-16T12:00:00+00:00 \
  --end 2026-06-16T13:00:00+00:00 \
  --interval-seconds 3600 \
  --market-id mkt_cpi_yoy_at_least_3pct_2026_09 \
  --max-steps 10 \
  --name "sample replay"

prediction-desk replay-summary --run-id replay_run_...
prediction-desk replay-steps --run-id replay_run_... --limit 50
```

## API

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

curl http://localhost:8000/api/v1/replay/runs/replay_run_...
curl http://localhost:8000/api/v1/replay/runs/replay_run_.../summary
curl "http://localhost:8000/api/v1/replay/runs/replay_run_.../steps?limit=50&offset=0"
```

## Future Phases

Later phases can add:

- historical venue adapters that write captured snapshots into the same point-in-time model
- richer simulated execution research on top of the paper simulator
- simulated risk attribution
- MiroFish/scenario simulation as a slow-lane feature source

Those are intentionally outside Replay Harness v1. The current replay layer can attach
paper position and portfolio metadata when simulated paper artifacts already exist, and
`paper_sim_gate_v1` checks paper context without simulating fills inside replay.

See [ingestion.md](ingestion.md) for the raw payload archive and fixture-backed venue
normalization path that can feed replay inputs. See [market_data.md](market_data.md) for
canonical price/liquidity snapshots and `available_at` semantics.
See [integrity_signals.md](integrity_signals.md) for fast-lane integrity assessments and
the `integrity_gate_v1` policy. See [equivalence.md](equivalence.md) for cross-venue
contract comparison metadata recorded in replay steps. See
[divergence_signals.md](divergence_signals.md) for equivalence-gated divergence metadata.
See [pretrade_gate.md](pretrade_gate.md) for the `pretrade_gate_v1` replay policy and
[paper_execution.md](paper_execution.md) for simulated-only paper execution metadata. See
[strategy_research.md](strategy_research.md) for research trace metadata and
`research_policy_v1`.
