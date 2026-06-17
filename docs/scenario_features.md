# Slow-Lane Scenario Features

Scenario features are a slow-lane research context source. V1 imports local, synthetic
MiroFish-style JSON reports or manually supplied local JSON files, normalizes their scores,
and exposes the resulting feature snapshot to the research harness.

V1 does not run MiroFish, call LLM APIs, call external services, or execute browser
automation. Imported artifacts are treated as simulated, uncertain, and hypothesis-forming
context only.

## Models

`ScenarioSeedBundle` is the deterministic market-context packet. It is built from stored
market metadata, the latest as-of rule snapshot, resolution predicate, ambiguity
assessment, market-data quality report, integrity assessment, equivalence/divergence
assessments, and trust verdict.

`ScenarioSimulationSpec` records what a scenario request would ask. It is a record of
intent only; no scenario job runs in v1.

`ScenarioArtifact` stores an imported JSON report. Fixture and manual imports are local
file reads only. URLs, non-JSON files, oversized files, and executable inputs are rejected.

`ScenarioFeatureSnapshot` stores normalized scores such as confidence, uncertainty,
consensus, polarization, narrative risk, and shock risk. Missing scores remain null.

`ScenarioRun` and `ScenarioRunSummary` record synchronous seed build, fixture import,
manual import, or normalization batches.

## Fixture Format

Fixtures live under `sample_data/scenario_artifacts/mirofish_style/`. They use a small JSON
shape with fields like `engine`, `schema_version`, `market_id`, `scenario_goal`,
`horizon_hours`, `summary`, normalized scores, `key_scenarios`, `risk_factors`,
`agent_groups`, and short safe evidence fragments.

## Point-In-Time Safety

Seed bundles and feature snapshots are available at explicit timestamps. Scenario as-of
lookups use `available_at <= asof_timestamp`. Research features and replay metadata consume
only the latest scenario feature available by the replay or research timestamp.

## Research Integration

`build_research_features` includes scenario features when sources are omitted or when
`SCENARIO` / `SCENARIO_SIMULATION_PLACEHOLDER` is requested. The emitted research feature
uses:

- `feature_source = SCENARIO_SIMULATION_PLACEHOLDER`
- `feature_family = SCENARIO`
- source refs for the scenario feature and artifact
- normalized scenario scores and reason codes

The `scenario_context_research_v1` strategy produces `WATCH` or `REVIEW_ONLY` signals only.
It does not create hypothetical trade-intent proposals.

## Replay Metadata

Replay actions do not change in v1. Replay steps attach scenario metadata when available:

- `latest_scenario_feature_snapshot_id`
- `scenario_confidence_score`
- `scenario_uncertainty_score`
- `scenario_reason_codes`

## CLI

```bash
prediction-desk scenario-build-seed --market-id mkt_sfo_rain_2026_09_01
prediction-desk scenario-import-fixtures --market-id mkt_sfo_rain_2026_09_01
prediction-desk scenario-latest --market-id mkt_sfo_rain_2026_09_01
prediction-desk scenario-run --market-id mkt_sfo_rain_2026_09_01
```

## API

- `POST /api/v1/scenario/seeds/build`
- `GET /api/v1/markets/{market_id}/scenario/seed/latest`
- `POST /api/v1/scenario/specs`
- `POST /api/v1/scenario/import-fixtures`
- `POST /api/v1/scenario/import-manual`
- `POST /api/v1/scenario/artifacts/{scenario_artifact_id}/normalize`
- `GET /api/v1/scenario/artifacts`
- `GET /api/v1/scenario/features`
- `GET /api/v1/markets/{market_id}/scenario/latest`
- `POST /api/v1/scenario/runs`
- `GET /api/v1/scenario/runs`
- `GET /api/v1/scenario/runs/{scenario_run_id}`
- `GET /api/v1/scenario/runs/{scenario_run_id}/summary`

## Boundaries

Scenario features do not directly affect trust verdict actions, pre-trade gate decisions,
paper simulation behavior, or replay actions in v1. They are slow-lane research context and
may support future local adapters if those adapters preserve point-in-time semantics,
local-only execution, explicit simulated labeling, and credential-free operation.
